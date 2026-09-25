"""Menu 14's installed chat package must keep working with the upgraded SDK."""

from types import SimpleNamespace
from openai import OpenAI
from whatsapp_chatgpt_python import WhatsappGptBot
import json
import unittest
import httpx2


class ChatGptCompatibilityTest(unittest.TestCase):
    def test_process_chat_sync_sends_chat_completion_and_answers(self):
        requests = []

        def respond(request):
            requests.append(json.loads(request.content))

            return httpx2.Response(200, json={
                "id": "chatcmpl-test", "object": "chat.completion", "created": 1,
                "model": "gpt-4o", "choices": [{
                    "index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "Hello!"},
                }],
            })

        transport = httpx2.MockTransport(respond)

        client = OpenAI(
            api_key="test-key", base_url="https://example.invalid/v1",
            http_client=httpx2.Client(transport=transport),
        )

        # The Green-API parent constructor performs network I/O, exercise the installed package's actual chat method
        # with an isolated SDK client.
        bot = WhatsappGptBot.__new__(WhatsappGptBot)
        bot.openai_client = client
        bot.model = "gpt-4o"
        bot.temperature = 0.7
        bot.system_message = "Be concise."
        bot.max_history_length = 10
        bot.error_message = "failed"
        bot.sessions = {}

        bot.message_handlers = SimpleNamespace(
            process_message_sync=lambda notification: "Hi"
        )

        bot.middleware = SimpleNamespace(
            message_middlewares=[], response_middlewares=[]
        )

        answers = []
        notification = SimpleNamespace(chat="caller@c.us", answer=answers.append)

        bot.process_chat_sync(notification)

        self.assertEqual(answers, ["Hello!"])
        self.assertEqual(requests[0]["model"], "gpt-4o")
        self.assertEqual(requests[0]["messages"][-1], {"role": "user", "content": "Hi"})
        client.close()
