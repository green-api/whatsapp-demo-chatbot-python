from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event, RLock, Semaphore, Thread
from time import time
from internal.utils import MAX_INACTIVITY_TIME_SECONDS
from whatsapp_chatbot_python.calls.contracts import CallExecutor
from .delivery import CallDeliveryService, CallRecordingUploader, CallResultNotifier
from .state_machine import CallStateMachine
import asyncio
import logging

from .models import (
    CallEvent,
    CallExecutionResult,
    CallSession,
    CallState,
    EnqueueResult,
    StateTransition,
    TERMINAL_STATES,
)


# Constants

MAX_CONCURRENT_DELIVERIES = 4


class InMemoryCallSessionStore:
    """The coordinator lock protects this registry."""

    def __init__(self) -> None:
        self._by_sender: dict[str, CallSession] = {}

    def add(self, session: CallSession) -> None:
        if session.sender_id in self._by_sender:
            raise KeyError(session.sender_id)

        self._by_sender[session.sender_id] = session

    def get_by_sender(self, sender_id: str) -> CallSession | None:
        return self._by_sender.get(sender_id)

    def remove(self, sender_id: str) -> None:
        self._by_sender.pop(sender_id, None)

    def values(self) -> tuple[CallSession, ...]:
        return tuple(self._by_sender.values())


class CallCoordinator:
    """
    Owns the single call slot, FIFO queue, registry and all FSM mutations.
    """

    def __init__(
        self,
        executor: CallExecutor,
        notifier: CallResultNotifier,
        logger: logging.Logger,
        store: InMemoryCallSessionStore | None = None,
        uploader: CallRecordingUploader | None = None,
    ) -> None:
        self._executor = executor
        self._delivery = CallDeliveryService(notifier, uploader, logger)
        self._logger = logger
        self._store = store or InMemoryCallSessionStore()
        self._fsm = CallStateMachine()
        self._queue: Queue[CallSession | None] = Queue()
        self._lock = RLock()
        self._stop_event = Event()
        self._worker: Thread | None = None
        self._closed = False
        self._active_session: CallSession | None = None
        self._finished_at: dict[str, int] = {}
        self._deliveries = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DELIVERIES, thread_name_prefix="voip-delivery")
        self._delivery_slots = Semaphore(MAX_CONCURRENT_DELIVERIES)

    def enqueue(self, sender_id: str, chat_id: str, language: str) -> EnqueueResult:
        with self._lock:
            if self._closed:
                raise RuntimeError("CallCoordinator is closed")

            if self._store.get_by_sender(sender_id) is not None:
                return EnqueueResult.ALREADY_EXISTS

            session = CallSession(sender_id=sender_id, chat_id=chat_id, language=language)
            self._store.add(session)
            self._transition_unlocked(session, CallEvent.ENQUEUED)
            self._queue.put(session)

        self._logger.info(
            "VoIP request queued: session=%s",
            session.session_id,
        )

        return EnqueueResult.CREATED

    def get_session(self, sender_id: str | None) -> CallSession | None:
        if sender_id is None:
            return None

        with self._lock:
            return self._store.get_by_sender(sender_id)

    def has_session(self, sender_id: str | None) -> bool:
        return self.get_session(sender_id) is not None

    def activity_timestamp(self, sender_id: str | None) -> int | None:
        if sender_id is None:
            return None

        with self._lock:
            if self._store.get_by_sender(sender_id) is not None:
                return int(time())

            return self._finished_at.pop(sender_id, None)

    def dialog_status(self, sender_id: str | None) -> tuple[CallState, str] | None:
        """Return a stable call state and language for chat routing."""

        if sender_id is None:
            return None

        with self._lock:
            session = self._store.get_by_sender(sender_id)
            return (session.state, session.language) if session is not None else None

    def cancel_queued(self, sender_id: str | None) -> bool:
        if sender_id is None:
            return False

        with self._lock:
            session = self._store.get_by_sender(sender_id)

            if session is None or session.state != CallState.QUEUED:
                return False

            self._transition_unlocked(session, CallEvent.CANCEL_REQUESTED)
            self._store.remove(sender_id)

            return True

    @property
    def active_session(self) -> CallSession | None:
        with self._lock:
            return self._active_session

    def transition(
        self,
        session: CallSession,
        event: CallEvent,
        *,
        remote_reason: str | None = None,
        error_code: str | None = None,
    ) -> StateTransition:
        with self._lock:
            return self._transition_unlocked(
                session,
                event,
                remote_reason=remote_reason,
                error_code=error_code,
            )

    def start(self) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("CallCoordinator is closed")

            if self._worker and self._worker.is_alive():
                return

            self._stop_event.clear()
            self._worker = Thread(target=self._worker_loop, name="voip-call-worker", daemon=True)
            self._worker.start()

    def stop(self, timeout: float | None = None) -> None:
        """Close once, then wait for the active call and accepted deliveries."""
        # The event prevents another queued call from starting. The sentinel wakes
        # an idle worker blocked in Queue.get(). Both are needed for prompt shutdown.

        with self._lock:
            if self._closed:
                return

            self._closed = True

            self._stop_event.set()

            for session in self._store.values():
                if session.state == CallState.QUEUED:
                    self._transition_unlocked(session, CallEvent.SHUTDOWN_REQUESTED)
                    self._store.remove(session.sender_id)
        self._executor.request_stop()
        self._queue.put(None)
        worker = self._worker

        if worker and worker.is_alive():
            worker.join(timeout=timeout)

        worker_stopped = worker is None or not worker.is_alive()

        if not worker_stopped:
            self._logger.warning("VoIP call worker did not stop within the shutdown timeout")

        self._deliveries.shutdown(wait=worker_stopped)

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            session = self._queue.get()

            if session is None:
                self._queue.task_done()
                return

            try:
                result = self._run_session(session)

                if result is not None:
                    self._finalize_session(session, result)
            finally:
                self._queue.task_done()

    def _run_session(self, session: CallSession) -> CallExecutionResult | None:
        with self._lock:
            if self._store.get_by_sender(session.sender_id) is not session or session.state != CallState.QUEUED or self._stop_event.is_set():
                return None

            self._active_session = session

            self._transition_unlocked(session, CallEvent.DEQUEUED)

        try:
            result = asyncio.run(self._executor.execute(session, self.transition))

            if session.state not in TERMINAL_STATES:
                self.transition(
                    session,
                    CallEvent.INTERNAL_ERROR,
                    error_code="executor_finished_without_terminal_state",
                )

            return result or CallExecutionResult()
        except Exception as error:
            self._logger.exception(
                "Unhandled VoIP call error for session=%s", session.session_id
            )
            self.transition(
                session,
                CallEvent.INTERNAL_ERROR,
                error_code=type(error).__name__,
            )

            return CallExecutionResult()

    def _finalize_session(self, session: CallSession, result: CallExecutionResult) -> None:
        with self._lock:
            if self._active_session is session:
                self._active_session = None

        if self._delivery_slots.acquire(blocking=False):
            try:
                self._deliveries.submit(self._deliver, session, result)
            except RuntimeError:
                self._delivery_slots.release()
                self._deliver(session, result, release_slot=False)
        else:
            # Intentional backpressure: a fifth delivery blocks the call worker
            # rather than growing an unbounded queue of recordings.
            self._deliver(session, result, release_slot=False)

    def _deliver(self, session: CallSession, result: CallExecutionResult, release_slot: bool = True) -> None:
        try:
            self._delivery.deliver(session, result)
        finally:
            # A terminal call still owns the dialog until result delivery ends.
            with self._lock:
                if self._store.get_by_sender(session.sender_id) is session:
                    finished_at = int(time())

                    self._finished_at = dict(filter(
                        lambda item: finished_at - item[1] <= MAX_INACTIVITY_TIME_SECONDS,
                        self._finished_at.items(),
                    ))

                    self._finished_at[session.sender_id] = finished_at

                    self._store.remove(session.sender_id)

            if release_slot:
                self._delivery_slots.release()

    def _transition_unlocked(
        self,
        session: CallSession,
        event: CallEvent,
        *,
        remote_reason: str | None = None,
        error_code: str | None = None,
    ) -> StateTransition:
        result = self._fsm.apply(
            session,
            event,
            remote_reason=remote_reason,
            error_code=error_code,
        )

        if result.changed:
            self._logger.info(
                "VoIP state: session=%s %s -> %s event=%s",
                session.session_id,
                result.previous,
                result.current,
                event,
            )

        return result
