from __future__ import annotations
from typing import Any, Protocol
from .coordinator import CallCoordinator
from .filters import register_call_filters
from .notifier import CallNotifier
from .service import WhatsAppCallService
import logging


class CallFeatureConfig(Protocol):
    api_url: str
    user_id: str
    api_token_id: str
    call_realtime_model: str
    call_realtime_voice: str
    openai_api_key: str
    call_ring_timeout_seconds: int
    call_talk_timeout_seconds: int


def create_call_coordinator(
    config: CallFeatureConfig,
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
        logger=logger,
    )

    notifier = CallNotifier(
        api_url=config.api_url,
        id_instance=config.user_id,
        api_token_instance=config.api_token_id,
        answers_data=answers_data,
        logger=logger,
    )

    coordinator = CallCoordinator(service, notifier, logger)

    register_call_filters(coordinator)

    return coordinator
