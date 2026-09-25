from __future__ import annotations
from queue import Queue
from threading import Event, RLock, Thread
from typing import Protocol
from .state_machine import CallStateMachine
from .store import CallSessionStore, InMemoryCallSessionStore
import asyncio
import logging

from .models import (
    CallEvent,
    CallSession,
    EnqueueResult,
    StateTransition,
    TERMINAL_STATES,
)


class CallExecutor(Protocol):
    async def execute(self, session: CallSession, transition: "TransitionCallback") -> None: ...

    def request_stop(self) -> None: ...


class CallResultNotifier(Protocol):
    def notify_result(self, session: CallSession) -> None: ...


class TransitionCallback(Protocol):
    def __call__(
        self,
        session: CallSession,
        event: CallEvent,
        *,
        remote_reason: str | None = None,
        error_code: str | None = None,
    ) -> StateTransition: ...


class CallCoordinator:
    """
    Owns the single call slot, FIFO queue, registry and all FSM mutations.
    """

    def __init__(
        self,
        executor: CallExecutor,
        notifier: CallResultNotifier,
        logger: logging.Logger,
        store: CallSessionStore | None = None,
    ) -> None:
        self._executor = executor
        self._notifier = notifier
        self._logger = logger
        self._store = store or InMemoryCallSessionStore()
        self._fsm = CallStateMachine()
        self._queue: Queue[CallSession | None] = Queue()
        self._lock = RLock()
        self._stop_event = Event()
        self._worker: Thread | None = None
        self._active_session: CallSession | None = None

    def enqueue(self, sender_id: str, chat_id: str, language: str) -> EnqueueResult:
        with self._lock:
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
            if self._worker and self._worker.is_alive():
                return

            self._stop_event.clear()
            self._worker = Thread(target=self._worker_loop, name="voip-call-worker", daemon=True)
            self._worker.start()

    def stop(self, timeout: float = 10.0) -> None:
        # The event prevents another queued call from starting. The sentinel wakes
        # an idle worker blocked in Queue.get(). Both are needed for prompt shutdown.

        self._stop_event.set()
        self._executor.request_stop()
        self._queue.put(None)
        worker = self._worker

        if worker and worker.is_alive():
            worker.join(timeout=timeout)

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            session = self._queue.get()

            if session is None:
                self._queue.task_done()
                return

            try:
                self._run_session(session)
            finally:
                self._finalize_session(session)
                self._queue.task_done()

    def _run_session(self, session: CallSession) -> None:
        with self._lock:
            self._active_session = session

        try:
            asyncio.run(self._executor.execute(session, self.transition))

            if session.state not in TERMINAL_STATES:
                self.transition(
                    session,
                    CallEvent.INTERNAL_ERROR,
                    error_code="executor_finished_without_terminal_state",
                )
        except Exception as error:
            self._logger.exception(
                "Unhandled VoIP call error for session=%s", session.session_id
            )
            self.transition(
                session,
                CallEvent.INTERNAL_ERROR,
                error_code=type(error).__name__,
            )

    def _finalize_session(self, session: CallSession) -> None:
        try:
            self._notifier.notify_result(session)
        except Exception:
            self._logger.exception(
                "Unable to send VoIP result for session=%s", session.session_id
            )

        with self._lock:
            self._store.remove(session.sender_id)

            if self._active_session is session:
                self._active_session = None

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
