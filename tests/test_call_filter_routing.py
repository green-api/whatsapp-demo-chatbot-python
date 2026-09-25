from unittest.mock import Mock
from whatsapp_chatbot_python.filters import TEXT_TYPES, filters
from whatsapp_chatbot_python.manager.router import Router
from internal.calls.coordinator import CallCoordinator
from internal.calls.filters import register_call_filters
import logging
import unittest


class CallFilterRoutingTest(unittest.TestCase):
    def test_message_routing_with_and_without_call_session(self) -> None:
        logger = logging.getLogger("call-filter-routing-test")
        logger.disabled = True
        coordinator = CallCoordinator(Mock(), Mock(), logger)

        previous_filter = filters.get("active_call_session")
        register_call_filters(coordinator)
        self.addCleanup(self._restore_filter, previous_filter)

        router = Router(None, logger)
        handled = []
        router.message(type_message=TEXT_TYPES, active_call_session=True)(
            lambda notification: handled.append("call")
        )
        router.message(type_message=TEXT_TYPES)(
            lambda notification: handled.append("normal")
        )
        event = {
            "typeWebhook": "incomingMessageReceived",
            "senderData": {"sender": "one@c.us", "chatId": "one@c.us"},
            "messageData": {
                "typeMessage": "textMessage",
                "textMessageData": {"textMessage": "hello"},
            },
        }

        router.route_event(event)
        coordinator.enqueue("one@c.us", "one@c.us", "en")
        router.route_event(event)

        self.assertEqual(handled, ["normal", "call"])

    @staticmethod
    def _restore_filter(previous_filter) -> None:
        if previous_filter is None:
            filters.pop("active_call_session", None)
        else:
            filters["active_call_session"] = previous_filter


if __name__ == "__main__":
    unittest.main()
