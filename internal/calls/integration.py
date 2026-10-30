from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from whatsapp_chatbot_python import IncomingCall
from whatsapp_chatbot_python.filters import AbstractFilter, filters
from whatsapp_chatbot_python.calls import CallOptions, VadOptions, WhatsAppCallService
from .coordinator import CallCoordinator
from .delivery import CallNotifier, RecordingUploader
from .models import ACTIVE_STATES, CallDirection, CallState, EnqueueResult, TERMINAL_STATES
from internal.utils import LANGUAGE_CODE_KEY, LAST_INTERACTION_KEY
import logging
from time import monotonic, time

if TYPE_CHECKING:
    from internal.config import ServerConfig
    from whatsapp_chatbot_python import Notification
    from whatsapp_chatbot_python.manager.state import AbstractStateManager


def create_call_coordinator(
    config: ServerConfig,
    answers_data: dict[str, Any],
    logger: logging.Logger,
) -> CallCoordinator:
    if not config.openai_api_key or not config.openai_api_key.strip():
        logger.error("VoIP is unavailable: configure OPENAI_API_KEY or openai_api_key")
        raise ValueError("OpenAI API key is required for VoIP calls")

    service = WhatsAppCallService(
        api_url=config.api_url,
        id_instance=config.user_id,
        api_token_instance=config.api_token_id,
        openai_api_key=config.openai_api_key,
        realtime_model=config.call_realtime_model,
        realtime_voice=config.call_realtime_voice,
        options=CallOptions(
            ring_seconds=config.call_ring_timeout_seconds,
            talk_seconds=config.call_talk_timeout_seconds,
            shutdown_seconds=config.call_shutdown_timeout_seconds,
            vad=VadOptions(
                threshold=0.70,
                prefix_padding_ms=400,
                silence_duration_ms=800,
                noise_reduction="near_field",
            ),
        ),
    )

    notifier = CallNotifier(
        api_url=config.api_url,
        media_url=config.media_url,
        id_instance=config.user_id,
        api_token_instance=config.api_token_id,
        answers_data=answers_data,
        logger=logger,
    )

    uploader = RecordingUploader(config.user_id, config.api_token_id, config.media_url)

    coordinator = CallCoordinator(
        service, notifier, logger, uploader=uploader,
        prompts=answers_data["call_prompts"],
        incoming_timeout_seconds=config.call_incoming_ring_timeout_seconds,
    )

    register_call_filters(coordinator)

    return coordinator


def handle_incoming_call(
    coordinator: CallCoordinator, call: IncomingCall,
    state_manager: AbstractStateManager, timeout_seconds: int,
) -> EnqueueResult | None:
    """Queue a live incoming offer or remove it when the caller leaves."""
    sender_id = call.sender
    call_id = call.call_id

    if not isinstance(sender_id, str) or not sender_id.endswith(("@c.us", "@lid")):
        logging.getLogger(__name__).warning(
            "Incoming VoIP event ignored: invalid caller address",
        )

        return None

    if not isinstance(call_id, str) or not call_id:
        logging.getLogger(__name__).warning(
            "Incoming VoIP event ignored: missing call ID",
        )

        return None

    status = call.status

    if status in ("declined", "missed", "hungUp"):
        coordinator.incoming_ended(sender_id, call_id)
        return None

    if status != "offer":
        return None

    if call.timestamp is None:
        coordinator.reject_unqueued_incoming(sender_id, call_id, "missing_timestamp")
        return None

    remaining = timeout_seconds - max(0, time() - call.timestamp)

    if remaining <= 0:
        coordinator.reject_unqueued_incoming(sender_id, call_id, "expired_offer")
        return None

    sender_data = state_manager.get_state_data(sender_id) or {}
    language = sender_data.get(LANGUAGE_CODE_KEY) or "en"

    result = coordinator.enqueue(
        sender_id, call.chat_id or sender_id, language,
        direction=CallDirection.INCOMING,
        call_id=call_id, incoming_deadline=monotonic() + remaining,
    )

    if result == EnqueueResult.ALREADY_EXISTS:
        coordinator.reject_unqueued_incoming(sender_id, call_id, "not_queued")

    return result


@dataclass(frozen=True, slots=True)
class CallChatAction:
    message_key: str | None
    language: str | None
    show_menu: bool = False


def handle_call_message(coordinator: CallCoordinator, sender_id: str | None, text: str | None) -> CallChatAction:
    status = coordinator.dialog_status(sender_id)

    if status is None:
        return CallChatAction(None, None)

    state, language = status
    is_zero = (text or "").strip() == "0"

    if state == CallState.QUEUED and is_zero:
        if coordinator.cancel_queued(sender_id):
            return CallChatAction("call_cancelled", language, show_menu=True)

        status = coordinator.dialog_status(sender_id)

        if status is None:
            return CallChatAction(None, None)

        state, language = status

    if state in TERMINAL_STATES:
        return CallChatAction("call_processing", language)

    if state in ACTIVE_STATES:
        return CallChatAction(None if is_zero else "call_in_progress", language)

    if state == CallState.QUEUED:
        return CallChatAction("call_queued", language)

    return CallChatAction("call_in_progress", language)


def update_call_activity(coordinator: CallCoordinator, notification: Notification) -> bool:
    data = notification.state_manager.get_state_data(notification.sender)

    if data is None:
        return False

    timestamp = coordinator.activity_timestamp(notification.sender)

    if timestamp is None:
        return False

    notification.state_manager.update_state_data(
        notification.sender,
        {LAST_INTERACTION_KEY: max(data.get(LAST_INTERACTION_KEY, 0), timestamp)},
    )

    return True


def register_call_filters(coordinator: CallCoordinator | None) -> None:
    class ActiveCallSessionFilter(AbstractFilter):
        def __init__(self, enabled: bool) -> None:
            self._enabled = enabled

        def check_event(self, notification: Notification) -> bool:
            return self._enabled and coordinator is not None and coordinator.has_session(notification.sender)

    filters["active_call_session"] = ActiveCallSessionFilter
