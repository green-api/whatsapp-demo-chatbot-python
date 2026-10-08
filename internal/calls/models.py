"""Call types supplied by the external library; queue results belong to this demo."""

from enum import StrEnum

from whatsapp_chatbot_python.calls.models import (
    ACTIVE_STATES,
    TERMINAL_STATES,
    WAITING_STATES,
    CallEndReason,
    CallEvent,
    CallExecutionResult,
    CallSession,
    CallState,
    StateTransition,
    TransitionOutcome,
    utc_now,
)


class EnqueueResult(StrEnum):
    CREATED = "created"
    ALREADY_EXISTS = "already_exists"


__all__ = [
    "ACTIVE_STATES", "TERMINAL_STATES", "WAITING_STATES", "CallEndReason",
    "CallEvent", "CallExecutionResult", "CallSession", "CallState",
    "StateTransition", "TransitionOutcome", "utc_now", "EnqueueResult",
]
