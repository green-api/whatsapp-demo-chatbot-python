from __future__ import annotations
from typing import Any
from .models import CallSession, CallState
import logging
import requests


MESSAGE_KEY_BY_STATE = {
    CallState.REMOTE_ENDED: "call_completed",
    CallState.REJECTED: "call_unreachable",
    CallState.RING_TIMEOUT: "call_unreachable",
    CallState.TALK_TIMEOUT: "call_talk_timeout",
    CallState.FAILED: "call_failed",
}


class CallNotifier:
    def __init__(
        self,
        *,
        api_url: str,
        id_instance: str,
        api_token_instance: str,
        answers_data: dict[str, Any],
        logger: logging.Logger,
    ) -> None:
        self._url = (
            f"{api_url.rstrip('/')}/waInstance{id_instance}/sendMessage/"
            f"{api_token_instance}"
        )

        self._answers_data = answers_data
        self._logger = logger
        self._session = requests.Session()

    def notify_result(self, session: CallSession) -> None:
        key = MESSAGE_KEY_BY_STATE.get(session.state, "call_failed")
        translations = self._answers_data[key]
        message = translations.get(session.language, translations["en"])

        response = self._session.post(
            self._url,
            json={"chatId": session.chat_id, "message": message},
            timeout=20,
        )

        if not response.ok:
            self._logger.error(
                "Unable to send VoIP result: session=%s status=%s",
                session.session_id,
                response.status_code,
            )

            response.raise_for_status()
