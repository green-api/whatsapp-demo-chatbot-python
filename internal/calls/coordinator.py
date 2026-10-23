from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event, RLock, Semaphore, Thread, Timer
from time import monotonic, time
from internal.utils import MAX_INACTIVITY_TIME_SECONDS
from whatsapp_chatbot_python.calls import IncomingCallExecutor
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
    CallDirection,
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
        executor: IncomingCallExecutor,
        notifier: CallResultNotifier,
        logger: logging.Logger,
        store: InMemoryCallSessionStore | None = None,
        uploader: CallRecordingUploader | None = None,
        prompts: dict[str, str] | None = None,
        incoming_timeout_seconds: int = 60,
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
        self._prompts = prompts or {}
        self._incoming_timeout_seconds = incoming_timeout_seconds
        self._ended_incoming: dict[tuple[str, str], float] = {}
        self._finished_at: dict[str, int] = {}
        self._incoming_timers: dict[str, Timer] = {}
        self._deliveries = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DELIVERIES, thread_name_prefix="voip-delivery")
        self._delivery_slots = Semaphore(MAX_CONCURRENT_DELIVERIES)

    def enqueue(self, sender_id: str, chat_id: str, language: str, *,
                direction: CallDirection = CallDirection.OUTGOING,
                call_id: str | None = None, incoming_deadline: float | None = None) -> EnqueueResult:
        with self._lock:
            if self._closed:
                raise RuntimeError("CallCoordinator is closed")

            if self._store.get_by_sender(sender_id) is not None:
                return EnqueueResult.ALREADY_EXISTS

            prompt = self._prompts.get(language, self._prompts.get("en"))

            if direction == CallDirection.INCOMING:
                if call_id is None or incoming_deadline is None:
                    raise ValueError("Incoming calls require call_id and incoming_deadline")

                self._prune_ended_incoming_unlocked()

                if (sender_id, call_id) in self._ended_incoming:
                    return EnqueueResult.ALREADY_EXISTS

                if monotonic() >= incoming_deadline:
                    return EnqueueResult.ALREADY_EXISTS

                session = CallSession.incoming(
                    sender_id=sender_id, chat_id=chat_id, call_id=call_id,
                    language=language, incoming_deadline=incoming_deadline,
                    prompt=prompt,
                )
            else:
                session = CallSession(
                    sender_id=sender_id, chat_id=chat_id, language=language,
                    prompt=prompt,
                )
            self._store.add(session)
            self._transition_unlocked(session, CallEvent.ENQUEUED)
            self._queue.put(session)

            if direction == CallDirection.INCOMING and incoming_deadline is not None:
                timer = Timer(max(0, incoming_deadline - monotonic()),
                              self._expire_incoming, args=(session,))

                timer.daemon = True
                self._incoming_timers[session.session_id] = timer

                timer.start()

        self._logger.info(
            "VoIP request queued: session=%s",
            session.session_id,
        )

        return EnqueueResult.CREATED

    def _expire_incoming(self, session: CallSession) -> None:
        with self._lock:
            if self._store.get_by_sender(session.sender_id) is not session:
                return

            if session.state != CallState.QUEUED:
                return

            self._transition_unlocked(session, CallEvent.INCOMING_EXPIRED)
            self._store.remove(session.sender_id)
            self._remember_incoming_unlocked(session.sender_id, session.call_id)
            self._incoming_timers.pop(session.session_id, None)

        self._reject_incoming(session)

    def _reject_incoming(self, session: CallSession) -> None:
        try:
            asyncio.run(self._executor.reject_incoming(session.call_id, session.sender_id))
        except Exception:
            self._logger.exception("Unable to reject incoming call: session=%s", session.session_id)

    def reject_unqueued_incoming(self, sender_id: str, call_id: str, reason: str) -> bool:
        """Reject an unusable offer without affecting a queued or active call."""
        with self._lock:
            if self._closed:
                return False

            session = self._store.get_by_sender(sender_id)

            if (session is not None and session.direction == CallDirection.INCOMING
                    and session.call_id == call_id):
                return False

            self._prune_ended_incoming_unlocked()

            if (sender_id, call_id) in self._ended_incoming:
                return False

            self._remember_incoming_unlocked(sender_id, call_id)

        self._logger.warning(
            "Incoming VoIP offer not queued; rejection requested: reason=%s call_id=%s",
            reason, call_id,
        )

        Thread(
            target=self._reject_incoming_call,
            args=(call_id, sender_id), daemon=True,
        ).start()

        return True

    def _reject_incoming_call(self, call_id: str, sender_id: str) -> None:
        try:
            rejected = asyncio.run(self._executor.reject_incoming(call_id, sender_id))
            if not rejected:
                self._logger.info(
                    "Incoming VoIP rejection skipped: no matching ringing call for call_id=%s",
                    call_id,
                )
        except Exception:
            self._logger.exception("Unable to reject incoming call: call_id=%s", call_id)

    def incoming_ended(self, sender_id: str, call_id: str) -> None:
        notify = False

        with self._lock:
            # A terminal webhook can arrive before its offer. Remember both IDs.
            self._remember_incoming_unlocked(sender_id, call_id)
            session = self._store.get_by_sender(sender_id)

            if session is None or session.direction != CallDirection.INCOMING or session.call_id != call_id:
                return

            was_queued = session.state == CallState.QUEUED

            event = (
                CallEvent.REMOTE_IDLE if session.state in (CallState.CONNECTING, CallState.IN_CALL)
                     else CallEvent.CALLER_LEFT
             )

            transition = self._transition_unlocked(session, event)

            if was_queued:
                self._store.remove(sender_id)
            elif transition.applied:
                notify = True

            timer = self._incoming_timers.pop(session.session_id, None)

            if timer is not None:
                timer.cancel()

        if notify:
            try:
                self._executor.notify_incoming_ended(call_id)
            except Exception:
                self._logger.exception(
                    "Unable to notify active incoming call end: call_id=%s", call_id,
                )

    def _prune_ended_incoming_unlocked(self) -> None:
        now = monotonic()

        self._ended_incoming = {
            key: deadline for key, deadline in self._ended_incoming.items()
            if deadline > now
        }

    def _remember_incoming_unlocked(self, sender_id: str, call_id: str | None) -> None:
        if call_id is None:
            return

        self._prune_ended_incoming_unlocked()
        self._ended_incoming[(sender_id, call_id)] = monotonic() + self._incoming_timeout_seconds

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

        incoming_to_reject = None

        with self._lock:
            session = self._store.get_by_sender(sender_id)

            if session is None or session.state != CallState.QUEUED:
                return False

            self._transition_unlocked(session, CallEvent.CANCEL_REQUESTED)
            self._store.remove(sender_id)
            timer = self._incoming_timers.pop(session.session_id, None)

            if timer is not None:
                timer.cancel()

            if session.direction == CallDirection.INCOMING:
                self._remember_incoming_unlocked(session.sender_id, session.call_id)
                incoming_to_reject = session

        if incoming_to_reject is not None:
            Thread(target=self._reject_incoming, args=(incoming_to_reject,), daemon=True).start()

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
            result = self._transition_unlocked(
                session,
                event,
                remote_reason=remote_reason,
                error_code=error_code,
            )

            return result

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

            incoming_to_reject = []

            for session in self._store.values():
                if session.state == CallState.QUEUED:
                    self._transition_unlocked(session, CallEvent.SHUTDOWN_REQUESTED)
                    self._store.remove(session.sender_id)

                    if session.direction == CallDirection.INCOMING:
                        self._remember_incoming_unlocked(session.sender_id, session.call_id)
                        incoming_to_reject.append(session)

            for timer in self._incoming_timers.values():
                timer.cancel()

            self._incoming_timers.clear()

        self._executor.request_stop()

        for session in incoming_to_reject:
            self._reject_incoming(session)

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
        expired = False

        with self._lock:
            if self._store.get_by_sender(session.sender_id) is not session or session.state != CallState.QUEUED or self._stop_event.is_set():
                return None

            if session.direction == CallDirection.INCOMING and session.incoming_deadline is not None and monotonic() >= session.incoming_deadline:
                self._transition_unlocked(session, CallEvent.INCOMING_EXPIRED)
                self._store.remove(session.sender_id)
                self._remember_incoming_unlocked(session.sender_id, session.call_id)

                expired = True
            else:
                self._active_session = session

                self._transition_unlocked(session, CallEvent.DEQUEUED)

                timer = self._incoming_timers.pop(session.session_id, None)

                if timer is not None:
                    timer.cancel()

        if expired:
            self._reject_incoming(session)
            return None

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

            if session.direction == CallDirection.INCOMING:
                self._remember_incoming_unlocked(session.sender_id, session.call_id)

            timer = self._incoming_timers.pop(session.session_id, None)

            if timer is not None:
                timer.cancel()

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
