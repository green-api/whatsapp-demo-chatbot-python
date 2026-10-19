"""Call types supplied by the local library; queue results belong to this demo."""

from enum import StrEnum

from whatsapp_chatbot_python.calls.models import (
    ACTIVE_STATES,
    TERMINAL_STATES,
    WAITING_STATES,
    CallDirection,
    CallEndReason,
    CallEvent,
    CallExecutionResult,
    CallSession,
    CallState,
    StateTransition,
    utc_now,
)


class EnqueueResult(StrEnum):
    CREATED = "created"
    ALREADY_EXISTS = "already_exists"


__all__ = [
    "ACTIVE_STATES", "TERMINAL_STATES", "WAITING_STATES", "CallDirection", "CallEndReason", "CallEvent",
    "CallExecutionResult", "CallSession", "CallState", "StateTransition", "utc_now", "EnqueueResult",
]
