import asyncio
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from internal.calls.models import CallEndReason, CallEvent, CallSession, CallState
from internal.calls.service import WhatsAppCallService
from internal.calls.state_machine import CallStateMachine


class FakeVoice:
    instances = []
    fail_start = False
    fail_greeting = False

    def __init__(self, **options):
        self.options = options
        self.greetings = 0
        self.closed = False
        self.instances.append(self)

    async def start(self):
        if self.fail_start:
            raise RuntimeError("OpenAI unavailable")

    async def close(self):
        self.closed = True

    async def greet_once(self):
        if self.greetings:
            return

        self.greetings += 1

        if self.fail_greeting:
            self.options["on_error"](RuntimeError("OpenAI failed"))

    def new_output_track(self):
        return object()

    def new_input_sink(self):
        return object()


class FakeCalls:
    def __init__(self, client):
        self.client = client
        self.listeners = {}
        self.closed = False
        self.audio_factory = None
        self.devices = []

    def addEventListener(self, name, callback):
        self.listeners.setdefault(name, []).append(callback)

    def emit(self, name, detail=None):
        for callback in self.listeners.get(name, []):
            callback(SimpleNamespace(detail=detail))

    async def startAudioBridge(self):
        self.client.actions.append("bridge")
        self.devices.append(self.audio_factory())
        if self.client.bridge_error:
            raise RuntimeError("audio bridge failed")
        if self.client.answer and not self.client.answer_after_bridge:
            self.emit("state", SimpleNamespace(state="on-call", reason=None))
        if self.client.answer and self.client.answer_after_bridge:
            asyncio.get_running_loop().call_later(
                0.001, self.emit, "state",
                SimpleNamespace(state="on-call", reason=None),
            )
        if self.client.reconnect:
            self.emit("disconnect", {"permanent": False})
            self.devices.append(self.audio_factory())
        if self.client.remote_hangup:
            asyncio.get_running_loop().call_later(
                0.01, self.emit, "state",
                SimpleNamespace(state="idle", reason="hangup"),
            )

    async def close(self):
        self.closed = True


class FakeClient:
    initial_state = "idle"
    answer = True
    remote_hangup = True
    bridge_error = False
    reconnect = False
    answer_after_bridge = False
    instances = []

    def __init__(self, options):
        self.calls = FakeCalls(self)
        self.actions = []
        self.instances.append(self)

    def connectCalls(self, *, audio_device_factory):
        self.calls.audio_factory = audio_device_factory

        loop = asyncio.get_running_loop()

        loop.call_soon(self.calls.emit, "connect")

        loop.call_soon(
            self.calls.emit, "state",
            SimpleNamespace(state=self.initial_state, reason=None),
        )
        return self.calls

    async def dial(self, target):
        self.actions.append(("dial", target))

    async def hangUp(self):
        self.actions.append("hangup")


class CallServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for name, value in {
            "initial_state": "idle", "answer": True, "remote_hangup": True,
            "bridge_error": False, "reconnect": False,
            "answer_after_bridge": False,
        }.items():
            setattr(FakeClient, name, value)

        FakeClient.instances = []
        FakeVoice.instances = []
        FakeVoice.fail_start = False
        FakeVoice.fail_greeting = False

        for target, fake in (
            ("internal.calls.service.GreenApiVoipClient", FakeClient),
            ("internal.calls.service.VoiceBotSession", FakeVoice),
        ):
            patcher = patch(target, fake)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_session(self):
        fsm = CallStateMachine()
        session = CallSession("sender@c.us", "sender@c.us", "ru")
        fsm.apply(session, CallEvent.ENQUEUED)
        return session, fsm.apply

    def make_service(self, ring=1, talk=1):
        logger = logging.getLogger("call-service-test")
        logger.disabled = True
        return WhatsAppCallService(
            api_url="https://example.invalid", id_instance="1",
            api_token_instance="token", openai_api_key="test-key",
            realtime_model="gpt-realtime-2.1", realtime_voice="marin",
            ring_timeout_seconds=ring, talk_timeout_seconds=talk, logger=logger,
        )

    async def test_dial_voice_bridge_and_remote_hangup(self):
        session, transition = self.make_session()

        await self.make_service().execute(session, transition)

        client = FakeClient.instances[0]
        voice = FakeVoice.instances[0]

        self.assertEqual(client.actions, [("dial", "sender@c.us"), "bridge"])
        self.assertEqual(session.state, CallState.REMOTE_ENDED)
        self.assertEqual(session.end_reason, CallEndReason.REMOTE_HANGUP)
        self.assertEqual(voice.greetings, 1)
        self.assertTrue(voice.closed)
        self.assertTrue(client.calls.closed)

    async def test_reconnect_keeps_one_conversation_and_greeting(self):
        FakeClient.reconnect = True
        session, transition = self.make_session()

        await self.make_service().execute(session, transition)
        self.assertEqual(len(FakeVoice.instances), 1)
        self.assertEqual(FakeVoice.instances[0].greetings, 1)
        self.assertEqual(len(FakeClient.instances[0].calls.devices), 2)

    async def test_bridge_before_answer_greets_only_after_answer(self):
        FakeClient.answer_after_bridge = True
        session, transition = self.make_session()

        await self.make_service().execute(session, transition)
        self.assertEqual(session.state, CallState.REMOTE_ENDED)
        self.assertEqual(FakeVoice.instances[0].greetings, 1)

    async def test_voice_failure_hangs_up_once(self):
        FakeClient.remote_hangup = False
        FakeVoice.fail_greeting = True
        session, transition = self.make_session()

        await self.make_service().execute(session, transition)
        self.assertEqual(session.state, CallState.FAILED)
        self.assertEqual(session.end_reason, CallEndReason.ERROR)
        self.assertEqual(FakeClient.instances[0].actions.count("hangup"), 1)

    async def test_openai_start_failure_does_not_dial(self):
        FakeVoice.fail_start = True
        session, transition = self.make_session()

        with self.assertRaises(RuntimeError):
            await self.make_service().execute(session, transition)

        self.assertEqual(FakeClient.instances, [])
        self.assertTrue(FakeVoice.instances[0].closed)

    async def test_ring_and_talk_timeout_hang_up(self):
        for answer, expected in ((False, CallState.RING_TIMEOUT), (True, CallState.TALK_TIMEOUT)):
            with self.subTest(expected=expected):
                FakeClient.answer = answer
                FakeClient.remote_hangup = False
                session, transition = self.make_session()

                await self.make_service(ring=0.01, talk=0.01).execute(session, transition)
                self.assertEqual(session.state, expected)
                self.assertEqual(FakeClient.instances[-1].actions.count("hangup"), 1)

    async def test_busy_instance_is_not_dialed(self):
        FakeClient.initial_state = "on-call"
        session, transition = self.make_session()

        await self.make_service().execute(session, transition)
        self.assertEqual(session.state, CallState.FAILED)
        self.assertEqual(FakeClient.instances[0].actions, [])

    async def test_bridge_failure_hangs_up(self):
        FakeClient.bridge_error = True
        session, transition = self.make_session()

        await self.make_service().execute(session, transition)
        self.assertEqual(session.state, CallState.FAILED)
        self.assertEqual(FakeClient.instances[0].actions.count("hangup"), 1)

    async def test_shutdown_hangs_up(self):
        FakeClient.answer = False
        FakeClient.remote_hangup = False
        session, transition = self.make_session()

        service = self.make_service()
        task = asyncio.create_task(service.execute(session, transition))

        while session.state != CallState.RINGING:
            await asyncio.sleep(0)

        service.request_stop()

        await task

        self.assertEqual(session.end_reason, CallEndReason.SHUTDOWN)
        self.assertEqual(FakeClient.instances[0].actions.count("hangup"), 1)
