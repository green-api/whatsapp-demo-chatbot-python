from __future__ import annotations
from typing import Protocol
from .models import CallSession


class CallSessionStore(Protocol):
    def add(self, session: CallSession) -> None: ...

    def get_by_sender(self, sender_id: str) -> CallSession | None: ...

    def remove(self, sender_id: str) -> None: ...


class InMemoryCallSessionStore:
    """
    The coordinator lock protects this intentionally small store.
    """

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
