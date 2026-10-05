from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from whatsapp_chatbot_python.manager.state import StateManager
from internal.calls.coordinator import CallCoordinator
from internal.calls.integration import handle_call_message, update_call_activity
from internal.calls.models import CallExecutionResult
from internal.utils import LAST_INTERACTION_KEY, LANGUAGE_CODE_KEY, States, sender_state_data_updater


class CallActivityTest(TestCase):
    def test_cancel_after_long_queue_wait_preserves_menu_and_language(self):
        coordinator = CallCoordinator(Mock(), Mock(), Mock())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")

        manager = StateManager()

        manager.set_state("one@c.us", States.MENU.value)

        manager.set_state_data("one@c.us", {
            LAST_INTERACTION_KEY: 1, LANGUAGE_CODE_KEY: "ru",
        })

        notification = SimpleNamespace(sender="one@c.us", state_manager=manager)

        with patch("internal.calls.coordinator.time", return_value=1000):
            self.assertTrue(update_call_activity(coordinator, notification))
            action = handle_call_message(coordinator, notification.sender, "0")

        self.assertEqual((action.message_key, action.show_menu), ("call_cancelled", True))
        self.assertIsNone(coordinator.get_session(notification.sender))

        with patch("internal.utils.time", return_value=1001):
            self.assertFalse(sender_state_data_updater(notification))

        self.assertEqual(manager.get_state(notification.sender).name, States.MENU.value)
        self.assertEqual(manager.get_state_data(notification.sender)[LANGUAGE_CODE_KEY], "ru")

    def test_call_end_refreshes_activity_without_changing_language(self):
        coordinator = CallCoordinator(Mock(), Mock(), Mock())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")

        manager = StateManager()

        manager.set_state("one@c.us", States.MENU.value)

        manager.set_state_data("one@c.us", {
            LAST_INTERACTION_KEY: 1,
            LANGUAGE_CODE_KEY: "ru",
        })

        notification = SimpleNamespace(sender="one@c.us", state_manager=manager)

        with patch("internal.calls.coordinator.time", return_value=1000):
            self.assertTrue(update_call_activity(coordinator, notification))
            call_session = coordinator.get_session("one@c.us")
            coordinator._deliver(call_session, CallExecutionResult())

        manager.update_state_data("one@c.us", {LAST_INTERACTION_KEY: 1})
        self.assertTrue(update_call_activity(coordinator, notification))

        with patch("internal.utils.time", return_value=1001):
            self.assertFalse(sender_state_data_updater(notification))

        self.assertEqual(manager.get_state("one@c.us").name, States.MENU.value)
        self.assertEqual(manager.get_state_data("one@c.us")[LANGUAGE_CODE_KEY], "ru")
        self.assertFalse(update_call_activity(coordinator, notification))

    def test_old_completion_does_not_extend_activity_indefinitely(self):
        coordinator = CallCoordinator(Mock(), Mock(), Mock())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")

        manager = StateManager()

        manager.set_state("one@c.us", States.MENU.value)

        manager.set_state_data("one@c.us", {
            LAST_INTERACTION_KEY: 1, LANGUAGE_CODE_KEY: "ru",
        })

        notification = SimpleNamespace(sender="one@c.us", state_manager=manager)

        with patch("internal.calls.coordinator.time", return_value=1000):
            coordinator._deliver(coordinator.get_session("one@c.us"), CallExecutionResult())

        self.assertTrue(update_call_activity(coordinator, notification))

        with patch("internal.utils.time", return_value=1401):
            self.assertTrue(sender_state_data_updater(notification))

        self.assertEqual(manager.get_state("one@c.us").name, States.INITIAL.value)
