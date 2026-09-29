from threading import Event, Lock
from pathlib import Path
from tempfile import NamedTemporaryFile
from internal.calls.coordinator import CallCoordinator
from internal.calls.models import CallEndReason, CallEvent, CallState, EnqueueResult
from internal.calls.models import CallExecutionResult
from internal.calls.integration import handle_call_message
import asyncio
import logging
import unittest


class FakeExecutor:
    def __init__(self) -> None:
        self.order: list[str] = []
        self.lock = Lock()
        self.stop_requested = False

    def request_stop(self) -> None:
        self.stop_requested = True

    async def execute(self, session, transition) -> None:
        with self.lock:
            self.order.append(session.sender_id)

        await asyncio.sleep(0.02)
        transition(session, CallEvent.DIAL_ACCEPTED)
        transition(session, CallEvent.REMOTE_ACCEPTED)
        transition(session, CallEvent.BRIDGE_READY)
        transition(session, CallEvent.REMOTE_IDLE)


class FakeNotifier:
    def __init__(self) -> None:
        self.sessions = []
        self.done = Event()

    def notify_result(self, session) -> None:
        self.sessions.append(session)

        if len(self.sessions) == 2:
            self.done.set()


class CallCoordinatorTest(unittest.TestCase):
    @staticmethod
    def logger() -> logging.Logger:
        logger = logging.getLogger("call-coordinator-test")
        logger.disabled = True

        return logger

    def test_fifo_and_duplicate_protection(self) -> None:
        executor = FakeExecutor()
        notifier = FakeNotifier()
        coordinator = CallCoordinator(executor, notifier, self.logger())

        self.assertEqual(
            coordinator.enqueue("one@c.us", "one@c.us", "ru"),
            EnqueueResult.CREATED,
        )

        self.assertEqual(
            coordinator.enqueue("one@c.us", "one@c.us", "ru"),
            EnqueueResult.ALREADY_EXISTS,
        )

        self.assertEqual(
            coordinator.enqueue("two@c.us", "two@c.us", "en"),
            EnqueueResult.CREATED,
        )

        coordinator.start()
        self.assertTrue(notifier.done.wait(2))
        coordinator.stop()
        self.assertEqual(executor.order, ["one@c.us", "two@c.us"])
        self.assertTrue(executor.stop_requested)
        self.assertIsNone(coordinator.get_session("one@c.us"))
        self.assertIsNone(coordinator.get_session("two@c.us"))

    def test_error_does_not_block_next_session(self) -> None:
        class FailingOnceExecutor(FakeExecutor):
            async def execute(self, session, transition) -> None:
                with self.lock:
                    self.order.append(session.sender_id)
                    position = len(self.order)

                if position == 1:
                    raise RuntimeError("expected test failure")

                transition(session, CallEvent.INTERNAL_ERROR, error_code="test")

        executor = FailingOnceExecutor()
        notifier = FakeNotifier()
        coordinator = CallCoordinator(executor, notifier, self.logger())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")
        coordinator.enqueue("two@c.us", "two@c.us", "en")
        coordinator.start()
        self.assertTrue(notifier.done.wait(2))
        coordinator.stop()
        self.assertEqual(executor.order, ["one@c.us", "two@c.us"])

    def test_stop_cancels_active_call_without_starting_next(self) -> None:
        class BlockingExecutor(FakeExecutor):
            def __init__(self) -> None:
                super().__init__()
                self.started = Event()

            async def execute(self, session, transition) -> None:
                with self.lock:
                    self.order.append(session.sender_id)

                self.started.set()

                while not self.stop_requested:
                    await asyncio.sleep(0)

                transition(session, CallEvent.SHUTDOWN_REQUESTED, error_code="shutdown")

        executor = BlockingExecutor()
        notifier = FakeNotifier()
        coordinator = CallCoordinator(executor, notifier, self.logger())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")
        coordinator.enqueue("two@c.us", "two@c.us", "en")
        coordinator.start()
        self.assertTrue(executor.started.wait(1))
        coordinator.stop()

        self.assertEqual(executor.order, ["one@c.us"])
        self.assertEqual(notifier.sessions, [])
        self.assertIsNone(coordinator.get_session("one@c.us"))
        self.assertIsNone(coordinator.get_session("two@c.us"))

    def test_stop_closes_queue_without_start_and_prevents_reuse(self) -> None:
        executor = FakeExecutor()
        notifier = FakeNotifier()
        coordinator = CallCoordinator(executor, notifier, self.logger())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")
        coordinator.enqueue("two@c.us", "two@c.us", "en")

        queued = coordinator.get_session("two@c.us")

        coordinator.stop()
        self.assertEqual(queued.state, CallState.FAILED)
        self.assertEqual(queued.end_reason, CallEndReason.SHUTDOWN)
        self.assertIsNone(coordinator.get_session("one@c.us"))
        self.assertIsNone(coordinator.get_session("two@c.us"))
        self.assertEqual(executor.order, [])
        self.assertEqual(notifier.sessions, [])

        with self.assertRaises(RuntimeError):
            coordinator.start()

        with self.assertRaises(RuntimeError):
            coordinator.enqueue("three@c.us", "three@c.us", "ru")

    def test_cancelled_queue_item_is_skipped_and_sender_can_requeue(self) -> None:
        executor = FakeExecutor()
        notifier = FakeNotifier()
        coordinator = CallCoordinator(executor, notifier, self.logger())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")

        cancelled = coordinator.get_session("one@c.us")

        self.assertTrue(coordinator.cancel_queued("one@c.us"))
        self.assertEqual(cancelled.state, CallState.CANCELLED)
        self.assertEqual(cancelled.end_reason.value, "user_cancelled")
        self.assertEqual(coordinator.enqueue("one@c.us", "one@c.us", "ru"), EnqueueResult.CREATED)
        coordinator.enqueue("two@c.us", "two@c.us", "en")
        coordinator.start()
        self.assertTrue(notifier.done.wait(2))
        coordinator.stop()
        self.assertEqual(executor.order, ["one@c.us", "two@c.us"])
        self.assertEqual(len(notifier.sessions), 2)

    def test_cancel_loses_once_worker_claims_call(self) -> None:
        claimed = Event()
        release = Event()

        class ClaimedExecutor(FakeExecutor):
            async def execute(self, session, transition):
                claimed.set()

                while not release.is_set():
                    await asyncio.sleep(0.001)

                transition(session, CallEvent.INTERNAL_ERROR)

        executor = ClaimedExecutor()
        coordinator = CallCoordinator(executor, FakeNotifier(), self.logger())
        coordinator.enqueue("one@c.us", "one@c.us", "ru")
        coordinator.start()

        try:
            self.assertTrue(claimed.wait(2))
            self.assertFalse(coordinator.cancel_queued("one@c.us"))
            self.assertEqual(coordinator.get_session("one@c.us").state, CallState.DIALING)
        finally:
            release.set()
            coordinator.stop()

    def test_zero_only_cancels_queued_call(self) -> None:
        coordinator = CallCoordinator(FakeExecutor(), FakeNotifier(), self.logger())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")

        action = handle_call_message(coordinator, "one@c.us", " 0 ")

        self.assertEqual(
            (action.message_key, action.language, action.show_menu),
            ("call_cancelled", "ru", True),
        )

        self.assertIsNone(coordinator.get_session("one@c.us"))

        coordinator.enqueue("one@c.us", "one@c.us", "ru")

        session = coordinator.get_session("one@c.us")

        coordinator.transition(session, CallEvent.DEQUEUED)
        coordinator.transition(session, CallEvent.DIAL_ACCEPTED)
        coordinator.transition(session, CallEvent.REMOTE_ACCEPTED)
        coordinator.transition(session, CallEvent.BRIDGE_READY)
        self.assertIsNone(handle_call_message(coordinator, "one@c.us", "0").message_key)
        self.assertFalse(coordinator.cancel_queued("one@c.us"))
        self.assertEqual(session.state, CallState.IN_CALL)

    def test_upload_failure_is_silent_and_releases_dialog(self) -> None:
        finished = Event()
        sent_text = []
        paths = []

        class Executor(FakeExecutor):
            async def execute(self, session, transition):
                await super().execute(session, transition)

                with NamedTemporaryFile(suffix=".mp3", delete=False) as file:
                    paths.append(Path(file.name))

                return CallExecutionResult(paths[-1])

        class Notifier:
            def notify_result(self, session):
                sent_text.append(session.state)

        class Uploader:
            async def send(self, chat_id, path):
                raise TimeoutError("upload deadline")

        class SignallingLogger:
            def info(self, *args):
                pass

            def warning(self, *args):
                finished.set()

        coordinator = CallCoordinator(Executor(), Notifier(), SignallingLogger(), uploader=Uploader())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")
        coordinator.start()
        self.assertTrue(finished.wait(2))
        coordinator.stop()
        self.assertEqual(sent_text, [CallState.REMOTE_ENDED])
        self.assertIsNone(coordinator.get_session("one@c.us"))
        self.assertFalse(paths[0].exists())

    def test_result_text_failure_skips_upload(self) -> None:
        done = Event()
        uploaded = []
        paths = []

        class Executor(FakeExecutor):
            async def execute(self, session, transition):
                await super().execute(session, transition)

                with NamedTemporaryFile(suffix=".mp3", delete=False) as file:
                    paths.append(Path(file.name))

                return CallExecutionResult(paths[-1])

        class Notifier:
            def notify_result(self, session):
                raise OSError("send failed")

        class Uploader:
            async def send(self, chat_id, path):
                uploaded.append(chat_id)

        class Logger:
            def info(self, *args):
                pass

            def warning(self, *args):
                done.set()

        coordinator = CallCoordinator(Executor(), Notifier(), Logger(), uploader=Uploader())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")
        coordinator.start()
        self.assertTrue(done.wait(2))
        coordinator.stop()
        self.assertEqual(uploaded, [])
        self.assertIsNone(coordinator.get_session("one@c.us"))
        self.assertFalse(paths[0].exists())

    def test_result_precedes_upload_and_sender_stays_locked_until_upload_finishes(self) -> None:
        actions = []
        upload_started = Event()
        upload_release = Event()
        paths = []

        class RecordingExecutor(FakeExecutor):
            async def execute(self, session, transition):
                await super().execute(session, transition)

                if session.sender_id == "one@c.us":
                    with NamedTemporaryFile(suffix=".mp3", delete=False) as file:
                        file.write(b"audio")
                        paths.append(Path(file.name))

                        return CallExecutionResult(paths[-1])

                return CallExecutionResult()

        class Notifier(FakeNotifier):
            def notify_result(self, session):
                actions.append(("text", session.sender_id))
                super().notify_result(session)

        class Uploader:
            async def send(self, chat_id, path):
                actions.append(("upload", chat_id))
                upload_started.set()

                while not upload_release.is_set():
                    await asyncio.sleep(0.001)

        executor = RecordingExecutor()
        notifier = Notifier()
        coordinator = CallCoordinator(executor, notifier, self.logger(), uploader=Uploader())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")
        coordinator.enqueue("two@c.us", "two@c.us", "en")
        coordinator.start()
        self.assertTrue(upload_started.wait(2))
        self.assertEqual(actions[:2], [("text", "one@c.us"), ("upload", "one@c.us")])

        self.assertEqual(
            handle_call_message(coordinator, "one@c.us", "hello").message_key,
            "call_processing",
        )

        self.assertEqual(coordinator.enqueue("one@c.us", "one@c.us", "ru"), EnqueueResult.ALREADY_EXISTS)
        self.assertTrue(notifier.done.wait(2))
        self.assertEqual(executor.order, ["one@c.us", "two@c.us"])
        upload_release.set()
        coordinator.stop()
        self.assertIsNone(coordinator.get_session("one@c.us"))
        self.assertFalse(paths[0].exists())


if __name__ == "__main__":
    unittest.main()
