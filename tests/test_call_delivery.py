from unittest.mock import Mock, patch
from internal.calls.delivery import CallNotifier
from internal.calls.models import CallEndReason, CallSession, CallState
import logging
import unittest


class CallDeliveryTest(unittest.TestCase):
    def test_result_text_uses_end_reason(self) -> None:
        answers = {
            "call_completed": {"en": "Completed"},
            "call_unreachable": {"en": "Unreachable"},
            "call_talk_timeout": {"en": "Time limit"},
            "call_failed": {"en": "Failed"},
        }

        notifier = CallNotifier(
            api_url="https://example.invalid",
            media_url="https://media.green-api.com",
            id_instance="1",
            api_token_instance="token",
            answers_data=answers,
            logger=logging.getLogger("delivery-test"),
        )

        response = Mock(code=200, data={"idMessage": "sent"})

        with patch("internal.calls.delivery.GreenAPI") as client:
            client.return_value.sending.sendMessage.return_value = response

            for reason, message in (
                (CallEndReason.REMOTE_HANGUP, "Completed"),
                (CallEndReason.REMOTE_REJECTED, "Unreachable"),
                (CallEndReason.RING_TIMEOUT, "Unreachable"),
                (CallEndReason.TALK_TIMEOUT, "Time limit"),
                (CallEndReason.ERROR, "Failed"),
            ):
                with self.subTest(reason=reason):
                    session = CallSession("one@c.us", "one@c.us", "en", state=CallState.FAILED)
                    session.end_reason = reason

                    notifier.notify_result(session)
                    client.return_value.sending.sendMessage.assert_called_with(session.chat_id, message)

            self.assertEqual(client.call_args.kwargs["media"], "https://media.green-api.com")

    def test_failed_sdk_response_raises(self) -> None:
        answers = {"call_failed": {"en": "Failed"}}

        notifier = CallNotifier(
            api_url="https://example.invalid", media_url="https://media.example.invalid",
            id_instance="1", api_token_instance="token", answers_data=answers,
            logger=logging.getLogger("delivery-test"),
        )

        with patch("internal.calls.delivery.GreenAPI") as client:
            client.return_value.sending.sendMessage.return_value = Mock(code=500, data=None)

            with self.assertRaises(RuntimeError):
                notifier.notify_result(CallSession("one@c.us", "one@c.us", "en"))
