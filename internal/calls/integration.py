from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from whatsapp_chatbot_python.filters import AbstractFilter, filters
from whatsapp_chatbot_python.calls.service import WhatsAppCallService
from .coordinator import CallCoordinator
from .delivery import CallNotifier, RecordingUploader
from .models import ACTIVE_STATES, CallState, TERMINAL_STATES
from internal.utils import LAST_INTERACTION_KEY
import logging

if TYPE_CHECKING:
    from internal.config import ServerConfig
    from whatsapp_chatbot_python import Notification


def create_call_coordinator(
    config: ServerConfig,
    answers_data: dict[str, Any],
    logger: logging.Logger,
) -> CallCoordinator:
    service = WhatsAppCallService(
        api_url=config.api_url,
        id_instance=config.user_id,
        api_token_instance=config.api_token_id,
        openai_api_key=config.openai_api_key,
        realtime_model=config.call_realtime_model,
        realtime_voice=config.call_realtime_voice,
        ring_timeout_seconds=config.call_ring_timeout_seconds,
        talk_timeout_seconds=config.call_talk_timeout_seconds,
        shutdown_timeout_seconds=config.call_shutdown_timeout_seconds,
        logger=logger,
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
    coordinator = CallCoordinator(service, notifier, logger, uploader=uploader)

    register_call_filters(coordinator)

    return coordinator


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


def register_call_filters(coordinator: CallCoordinator) -> None:
    class ActiveCallSessionFilter(AbstractFilter):
        def __init__(self, enabled: bool) -> None:
            self._enabled = enabled

        def check_event(self, notification: Notification) -> bool:
            return self._enabled and coordinator.has_session(notification.sender)

    filters["active_call_session"] = ActiveCallSessionFilter
