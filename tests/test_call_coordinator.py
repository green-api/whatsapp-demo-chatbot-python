import asyncio
import logging
import unittest
from threading import Event, Lock

from internal.calls.coordinator import CallCoordinator
from internal.calls.models import CallEvent, EnqueueResult


class FakeExecutor:
    def __init__(self) -> None:
        self.order: list[str] = []
        self.lock = Lock()
        self.stop_requested = False

    def request_stop(self) -> None:
        self.stop_requested = True

    async def execute(self, session, transition) -> None:
        transition(session, CallEvent.DEQUEUED)
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
                transition(session, CallEvent.DEQUEUED)
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
                transition(session, CallEvent.DEQUEUED)

                with self.lock:
                    self.order.append(session.sender_id)

                self.started.set()

                while not self.stop_requested:
                    await asyncio.sleep(0)

                transition(session, CallEvent.INTERNAL_ERROR, error_code="shutdown")

        executor = BlockingExecutor()
        notifier = FakeNotifier()
        coordinator = CallCoordinator(executor, notifier, self.logger())

        coordinator.enqueue("one@c.us", "one@c.us", "ru")
        coordinator.enqueue("two@c.us", "two@c.us", "en")
        coordinator.start()
        self.assertTrue(executor.started.wait(1))
        coordinator.stop()

        self.assertEqual(executor.order, ["one@c.us"])


if __name__ == "__main__":
    unittest.main()
