from __future__ import annotations
from typing import TYPE_CHECKING
from whatsapp_chatbot_python.filters import AbstractFilter, filters

if TYPE_CHECKING:
    from whatsapp_chatbot_python import Notification
    from .coordinator import CallCoordinator


def register_call_filters(coordinator: "CallCoordinator") -> None:
    class ActiveCallSessionFilter(AbstractFilter):
        def __init__(self, enabled: bool) -> None:
            self._enabled = enabled

        def check_event(self, notification: "Notification") -> bool:
            return self._enabled and coordinator.has_session(notification.sender)

    filters["active_call_session"] = ActiveCallSessionFilter
