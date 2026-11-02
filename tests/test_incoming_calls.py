import logging
import unittest
from threading import Event
from time import monotonic, time
from types import SimpleNamespace

from whatsapp_chatbot_python import IncomingCall, IncomingCallNotification
from whatsapp_chatbot_python.filters import filters
from whatsapp_chatbot_python.manager.router import Router
from whatsapp_chatbot_python.manager.state import StateManager
from whatsapp_chatbot_python.calls import WhatsAppCallService

from internal.calls.coordinator import CallCoordinator
from internal.calls.integration import create_call_coordinator, handle_incoming_call
from internal.calls.models import (
    CallDirection, CallEndReason, CallEvent, CallSession, CallState, EnqueueResult,
)
from internal.calls.state_machine import CallStateMachine


class WaitingExecutor:
    def __init__(self):
        self.rejected = []
        self.ended = []
        self.rejected_event = Event()

    def request_stop(self):
        pass

    def notify_incoming_ended(self, call_id):
        self.ended.append(call_id)
        return False

    async def reject_incoming(self, call_id, sender_id):
        self.rejected.append((call_id, sender_id))
        self.rejected_event.set()
        return True


class IncomingQueueTest(unittest.TestCase):
    def setUp(self):
        self.executor = WaitingExecutor()
        self.coordinator = CallCoordinator(
            self.executor, None, logging.getLogger("incoming-test"),
            prompts={"en": "Greet the user: Hello!", "ru": "Поздоровайся: Здравствуйте!"},
            incoming_timeout_seconds=60,
        )
        self.states = StateManager()
        self.states.set_state("caller@c.us", "MENU")
        self.states.set_state_data("caller@c.us", {"language_code": "ru"})
        self.addCleanup(self.coordinator.stop)

    @staticmethod
    def event(status="offer", call_id="call-1", timestamp=None):
        return {
            "typeWebhook": "incomingCall", "status": status,
            "from": "caller@c.us", "idMessage": call_id,
            "timestamp": time() if timestamp is None else timestamp,
        }

    def offer(self, **changes):
        return handle_incoming_call(
            self.coordinator, IncomingCall.from_event(self.event(**changes)),
            self.states, 60,
        )

    def test_offer_is_queued_once_and_caller_leaving_removes_it(self):
        self.assertEqual(self.offer(), EnqueueResult.CREATED)
        self.assertEqual(self.offer(), EnqueueResult.ALREADY_EXISTS)
        session = self.coordinator.get_session("caller@c.us")
        self.assertEqual(
            (session.language, session.direction, session.call_id, session.prompt),
            ("ru", CallDirection.INCOMING, "call-1", "Здравствуйте!"),
        )
        self.offer(status="declined", call_id="older")
        self.assertIs(self.coordinator.get_session("caller@c.us"), session)
        self.offer(status="hungUp")
        self.assertIsNone(self.coordinator.get_session("caller@c.us"))
        self.assertEqual((session.state, session.end_reason),
                         (CallState.REJECTED, CallEndReason.CALLER_LEFT))
        self.assertEqual(self.offer(), EnqueueResult.ALREADY_EXISTS)
        self.assertEqual(self.offer(call_id="call-2"), EnqueueResult.CREATED)

    def test_terminal_webhook_before_offer_blocks_late_offer(self):
        self.offer(status="missed")
        self.assertEqual(self.offer(), EnqueueResult.ALREADY_EXISTS)
        self.assertIsNone(self.coordinator.get_session("caller@c.us"))

    def test_bot_router_delivers_typed_call_with_shared_message_state(self):
        router = Router(None, logging.getLogger("incoming-router-test"))
        received = []
        router.message.state_manager.set_state("caller@c.us", "MENU")
        router.message.state_manager.set_state_data(
            "caller@c.us", {"language_code": "ru"},
        )

        def on_call(notification: IncomingCallNotification):
            received.append(notification)
            handle_incoming_call(
                self.coordinator, notification.call, notification.state_manager, 60,
            )

        router.incoming_call()(on_call)
        event = self.event()
        router.route_event(event)
        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], IncomingCallNotification)
        self.assertIs(received[0].state_manager, router.message.state_manager)
        self.assertIs(received[0].raw_event, event)
        self.assertIs(received[0].call.raw_event, event)
        self.assertEqual(received[0].call.call_id, "call-1")
        self.assertEqual(self.coordinator.get_session("caller@c.us").language, "ru")
        router.route_event(self.event(status="hungUp"))
        self.assertIsNone(self.coordinator.get_session("caller@c.us"))

    def test_timestamp_is_normalized_and_old_offers_are_ignored(self):
        self.assertIsNone(self.offer(timestamp=time() - 61))
        self.assertTrue(self.executor.rejected_event.wait(1))
        self.assertEqual(self.executor.rejected, [("call-1", "caller@c.us")])
        self.assertEqual(self.offer(), EnqueueResult.ALREADY_EXISTS)
        self.assertEqual(len(self.executor.rejected), 1)
        self.executor.rejected_event.clear()
        self.assertIsNone(self.offer(call_id="call-2", timestamp=(time() - 61) * 1000))
        self.assertTrue(self.executor.rejected_event.wait(1))
        self.executor.rejected_event.clear()
        self.assertIsNone(self.offer(call_id="call-3", timestamp=float("nan")))
        self.assertTrue(self.executor.rejected_event.wait(1))
        self.executor.rejected_event.clear()
        self.assertIsNone(self.offer(call_id="call-4", timestamp=time() * 1_000_000_000))
        self.assertTrue(self.executor.rejected_event.wait(1))
        self.assertIsNone(self.coordinator.get_session("caller@c.us"))
        self.assertEqual(len(self.executor.rejected), 4)
        self.assertEqual(
            self.offer(call_id="call-5", timestamp=time() * 1_000_000),
            EnqueueResult.CREATED,
        )

    def test_unusable_duplicate_offer_does_not_reject_queued_call(self):
        self.assertEqual(self.offer(), EnqueueResult.CREATED)
        session = self.coordinator.get_session("caller@c.us")
        self.assertIsNone(self.offer(timestamp=float("nan")))
        self.assertIs(self.coordinator.get_session("caller@c.us"), session)
        self.assertFalse(self.executor.rejected_event.wait(0.05))

    def test_unqueued_offer_with_other_session_is_rejected(self):
        self.coordinator.enqueue("caller@c.us", "caller@c.us", "ru")
        self.assertEqual(self.offer(), EnqueueResult.ALREADY_EXISTS)
        self.assertTrue(self.executor.rejected_event.wait(1))
        self.assertEqual(self.executor.rejected, [("call-1", "caller@c.us")])
        self.assertEqual(
            self.coordinator.get_session("caller@c.us").direction,
            CallDirection.OUTGOING,
        )

    def test_missing_call_id_cannot_be_rejected(self):
        with self.assertLogs("internal.calls.integration", level="WARNING") as captured:
            self.assertIsNone(self.offer(call_id=""))
        self.assertIn("missing call ID", captured.output[0])
        self.assertFalse(self.executor.rejected_event.wait(0.05))
        self.assertIsNone(self.coordinator.get_session("caller@c.us"))

    def test_queued_expiry_rejects_and_releases_sender(self):
        self.offer()
        session = self.coordinator.get_session("caller@c.us")
        self.coordinator._expire_incoming(session)
        self.assertEqual((session.state, session.end_reason),
                         (CallState.REJECTED, CallEndReason.INCOMING_EXPIRED))
        self.assertIsNone(self.coordinator.get_session("caller@c.us"))
        self.assertEqual(self.executor.rejected, [("call-1", "caller@c.us")])

    def test_library_fsm_uses_common_dequeued_and_answer_events(self):
        session = CallSession.incoming(
            sender_id="caller@c.us", call_id="call-1", language="en",
            incoming_deadline=monotonic() + 60, prompt="Greet the user: Hello!",
        )
        fsm = CallStateMachine()
        fsm.apply(session, CallEvent.ENQUEUED)
        fsm.apply(session, CallEvent.DEQUEUED)
        self.assertEqual(session.state, CallState.RINGING)
        fsm.apply(session, CallEvent.INCOMING_ACCEPTED)
        self.assertTrue(session.incoming_accept_completed)
        self.assertIsNone(session.answered_at)
        fsm.apply(session, CallEvent.REMOTE_ACCEPTED)
        self.assertIsNotNone(session.answered_at)
        fsm.apply(session, CallEvent.BRIDGE_READY)
        self.assertEqual(session.state, CallState.IN_CALL)

    def test_caller_leaving_during_worker_handoff_transitions_even_without_notification(self):
        self.offer()
        session = self.coordinator.get_session("caller@c.us")
        with self.coordinator._lock:
            self.coordinator._active_session = session
            self.coordinator._transition_unlocked(session, CallEvent.DEQUEUED)
        self.coordinator.incoming_ended("caller@c.us", "call-1")
        self.assertEqual(session.state, CallState.REJECTED)
        self.assertIs(self.coordinator.get_session("caller@c.us"), session)
        self.assertEqual(self.executor.ended, ["call-1"])

    def test_caller_leaving_after_answer_is_normal_end(self):
        self.offer()
        session = self.coordinator.get_session("caller@c.us")
        with self.coordinator._lock:
            self.coordinator._active_session = session
            self.coordinator._transition_unlocked(session, CallEvent.DEQUEUED)
            self.coordinator._transition_unlocked(session, CallEvent.REMOTE_ACCEPTED)
        self.coordinator.incoming_ended("caller@c.us", "call-1")
        self.assertEqual((session.state, session.end_reason),
                         (CallState.REMOTE_ENDED, CallEndReason.REMOTE_HANGUP))

    def test_queue_timer_cannot_expire_a_handed_off_call(self):
        self.offer()
        session = self.coordinator.get_session("caller@c.us")
        with self.coordinator._lock:
            self.coordinator._active_session = session
            self.coordinator._transition_unlocked(session, CallEvent.DEQUEUED)
        self.coordinator._expire_incoming(session)
        self.assertEqual(session.state, CallState.RINGING)
        self.assertEqual(self.executor.rejected, [])

    def test_worker_rechecks_deadline_before_execution(self):
        self.offer()
        session = self.coordinator.get_session("caller@c.us")
        session.incoming_deadline = monotonic() - 1
        self.assertIsNone(self.coordinator._run_session(session))
        self.assertEqual(session.state, CallState.REJECTED)
        self.assertEqual(self.executor.rejected, [("call-1", "caller@c.us")])

    def test_shutdown_rejects_queued_incoming(self):
        self.offer()
        self.coordinator.stop()
        self.assertEqual(self.executor.rejected, [("call-1", "caller@c.us")])
        self.assertIsNone(self.coordinator.get_session("caller@c.us"))

    def test_outgoing_session_keeps_localized_greeting(self):
        self.coordinator.enqueue("caller@c.us", "caller@c.us", "ru")
        session = self.coordinator.get_session("caller@c.us")
        self.assertEqual((session.direction, session.prompt),
                         (CallDirection.OUTGOING, "Здравствуйте!"))

    def test_factory_uses_library_executor_with_explicit_config(self):
        config = SimpleNamespace(
            api_url="https://api.invalid", media_url="https://media.invalid",
            user_id="1", api_token_id="token", openai_api_key="key",
            call_realtime_model="model", call_realtime_voice="voice",
            call_ring_timeout_seconds=30, call_incoming_ring_timeout_seconds=60,
            call_talk_timeout_seconds=120, call_shutdown_timeout_seconds=10,
        )
        previous_filter = filters.get("active_call_session")
        coordinator = None
        try:
            coordinator = create_call_coordinator(
                config, {"call_prompts": {"en": "Greet the user: Hello!"}},
                logging.getLogger("incoming-factory-test"),
            )
            self.assertIsInstance(coordinator._executor, WhatsAppCallService)
            self.assertEqual(coordinator._incoming_timeout_seconds, 60)
            self.assertEqual(coordinator._prompts["en"], "Greet the user: Hello!")
        finally:
            if coordinator is not None:
                coordinator.stop()
            if previous_filter is None:
                filters.pop("active_call_session", None)
            else:
                filters["active_call_session"] = previous_filter

    def test_factory_reports_missing_openai_key_before_starting_voip(self):
        logger = logging.getLogger("incoming-missing-key-test")
        with self.assertLogs(logger, level="ERROR") as captured:
            with self.assertRaisesRegex(ValueError, "OpenAI API key is required"):
                create_call_coordinator(
                    SimpleNamespace(openai_api_key=""), {}, logger,
                )
        self.assertIn("OPENAI_API_KEY", captured.output[0])
