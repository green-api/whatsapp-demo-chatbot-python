"""Post-call result text, recording upload, and temporary-file ownership."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Protocol
from .models import CallEndReason, CallExecutionResult, CallSession
from whatsapp_api_client_python.API import GreenAPI
import asyncio
import logging

MESSAGE_KEY_BY_END_REASON = {
    CallEndReason.REMOTE_HANGUP: "call_completed",
    CallEndReason.REMOTE_REJECTED: "call_unreachable",
    CallEndReason.RING_TIMEOUT: "call_unreachable",
    CallEndReason.TALK_TIMEOUT: "call_talk_timeout",
    CallEndReason.ERROR: "call_failed",
}


class CallNotifier:
    def __init__(
        self,
        *,
        api_url: str,
        media_url: str,
        id_instance: str,
        api_token_instance: str,
        answers_data: dict[str, Any],
        logger: logging.Logger,
    ) -> None:
        self._api_options = dict(
            idInstance=id_instance,
            apiTokenInstance=api_token_instance,
            host=api_url,
            media=media_url,
            host_timeout=20,
        )

        self._answers_data = answers_data
        self._logger = logger

    def notify_result(self, session: CallSession) -> None:
        key = MESSAGE_KEY_BY_END_REASON.get(session.end_reason, "call_failed")
        translations = self._answers_data[key]
        message = translations.get(session.language, translations["en"])

        api = GreenAPI(**self._api_options)

        try:
            response = api.sending.sendMessage(session.chat_id, message)
        finally:
            api.session.close()

        if response.code != 200 or not isinstance(response.data, dict) or not response.data.get("idMessage"):
            self._logger.error(
                "Unable to send VoIP result: session=%s status=%s",
                session.session_id,
                response.code,
            )

            raise RuntimeError("VoIP result message was not accepted")


UPLOAD_TIMEOUT_SECONDS = 30
RECORDING_FILENAME = "call-recording.mp3"


class RecordingUploadError(Exception):
    pass


class RecordingUploader:
    def __init__(self, id_instance: str, api_token_instance: str, media_url: str) -> None:
        self._api = GreenAPI(
            id_instance,
            api_token_instance,
            media=media_url,
            media_timeout=UPLOAD_TIMEOUT_SECONDS,
        )

    async def send(self, chat_id: str, path: Path) -> None:
        response = await self._api.sending.sendFileByUploadAsync(
            chat_id,
            str(path),
            RECORDING_FILENAME,
        )

        if response.code != 200 or not isinstance(response.data, dict) or not response.data.get("idMessage"):
            raise RecordingUploadError("recording was not accepted")


class CallResultNotifier(Protocol):
    def notify_result(self, session: CallSession) -> None: ...


class CallRecordingUploader(Protocol):
    async def send(self, chat_id: str, path: Path) -> None: ...


class CallDeliveryService:
    """Send final text before audio and release the temporary recording."""

    def __init__(
        self, notifier: CallResultNotifier, uploader: CallRecordingUploader | None,
        logger: logging.Logger,
    ) -> None:
        self._notifier = notifier
        self._uploader = uploader
        self._logger = logger

    def deliver(self, session: CallSession, result: CallExecutionResult) -> None:
        try:
            # A shutdown is operational; there is no user-facing failure result.
            if session.end_reason == CallEndReason.SHUTDOWN:
                return

            # Upload only after the text succeeds, preserving visible order.
            self._notifier.notify_result(session)

            if result.recording_path is not None and self._uploader is not None:
                asyncio.run(self._uploader.send(session.chat_id, result.recording_path))
        except Exception as error:
            self._logger.warning(
                "Unable to deliver VoIP result or recording: session=%s error=%s",
                session.session_id, type(error).__name__,
            )
        finally:
            try:
                if result.recording_path is not None:
                    result.recording_path.unlink(missing_ok=True)
            except OSError:
                self._logger.exception(
                    "Unable to remove VoIP recording: session=%s", session.session_id
                )
