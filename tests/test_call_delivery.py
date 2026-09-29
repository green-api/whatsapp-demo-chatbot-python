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
            api_url="https://example.invalid", id_instance="1",
            api_token_instance="token", answers_data=answers,
            logger=logging.getLogger("delivery-test"),
        )

        response = Mock(ok=True)

        with patch("internal.calls.delivery.requests.post", return_value=response) as post:
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
                    self.assertEqual(post.call_args.kwargs["json"]["message"], message)
