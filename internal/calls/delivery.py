"""Post-call result text, recording upload, and temporary-file ownership."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Protocol
from .models import CallEndReason, CallExecutionResult, CallSession
import asyncio
import logging
import aiohttp
import requests

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

    def notify_result(self, session: CallSession) -> None:
        key = MESSAGE_KEY_BY_END_REASON.get(session.end_reason, "call_failed")
        translations = self._answers_data[key]
        message = translations.get(session.language, translations["en"])

        response = requests.post(
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


UPLOAD_TIMEOUT_SECONDS = 30
RECORDING_FILENAME = "call-recording.mp3"


class RecordingUploadError(Exception):
    pass


class RecordingUploader:
    def __init__(self, id_instance: str, api_token_instance: str) -> None:
        self._url = (
            f"https://media.green-api.com/waInstance{id_instance}/"
            f"sendFileByUpload/{api_token_instance}"
        )

    async def send(self, chat_id: str, path: Path) -> None:
        form = aiohttp.FormData()
        form.add_field("chatId", chat_id)
        form.add_field("fileName", RECORDING_FILENAME)

        with path.open("rb") as file:
            form.add_field("file", file, filename=RECORDING_FILENAME, content_type="audio/mpeg")

            timeout = aiohttp.ClientTimeout(total=UPLOAD_TIMEOUT_SECONDS)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self._url, data=form) as response:
                    if response.status != 200:
                        raise RecordingUploadError(f"upload HTTP {response.status}")

                    try:
                        body = await response.json()
                    except (aiohttp.ContentTypeError, ValueError) as error:
                        raise RecordingUploadError("invalid upload response") from error

                    if not isinstance(body, dict) or not body.get("idMessage"):
                        raise RecordingUploadError("upload response has no idMessage")


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
