"""Post-call result text, recording upload, and temporary-file ownership."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from .models import CallDirection, CallEndReason, CallExecutionResult, CallSession
from whatsapp_api_client_python.API import GreenAPI
import logging

MESSAGE_KEY_BY_END_REASON = {
    CallEndReason.REMOTE_HANGUP: "call_completed",
    CallEndReason.REMOTE_REJECTED: "call_unreachable",
    CallEndReason.RING_TIMEOUT: "call_unreachable",
    CallEndReason.INCOMING_EXPIRED: "call_unreachable",
    CallEndReason.CALLER_LEFT: "call_unreachable",
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
        if session.direction == CallDirection.INCOMING and session.answered_at is None:
            return

        key = MESSAGE_KEY_BY_END_REASON.get(session.end_reason, "call_failed")
        translations = self._answers_data[key]
        message = translations.get(session.language, translations["en"])

        self._send_message(session, message)

    def notify_recording_link(self, session: CallSession, url: str) -> None:
        translations = self._answers_data["call_recording_link"]
        label = translations.get(session.language, translations["en"])
        self._send_message(session, f"{label} {url}")

    def _send_message(self, session: CallSession, message: str) -> None:
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


class RecordingUploadError(Exception):
    pass


class RecordingUploader:
    def __init__(self, id_instance: str, api_token_instance: str, media_url: str) -> None:
        self._api_options = dict(idInstance=id_instance, apiTokenInstance=api_token_instance,
                                 media=media_url, media_timeout=UPLOAD_TIMEOUT_SECONDS)

    def upload(self, path: Path) -> str:
        api = GreenAPI(**self._api_options)

        try:
            response = api.sending.uploadFile(str(path))
        finally:
            api.session.close()

        url = response.data.get("urlFile") if isinstance(response.data, dict) else None

        if response.code != 200 or not isinstance(url, str) or not url.startswith("https://"):
            raise RecordingUploadError("recording upload did not return a file URL")

        filename = datetime.now().strftime("%Y-%m-%d-%H-%M-%S.mp3")
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))

        query["response-content-disposition"] = f'attachment; filename="{filename}"'

        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query, quote_via=quote),
            parts.fragment,
        ))


class CallResultNotifier(Protocol):
    def notify_result(self, session: CallSession) -> None: ...
    def notify_recording_link(self, session: CallSession, url: str) -> None: ...


class CallRecordingUploader(Protocol):
    def upload(self, path: Path) -> str: ...


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

            # Upload only after the result text succeeds, preserving visible order.
            self._notifier.notify_result(session)

            if result.recording_path is not None and self._uploader is not None:
                url = self._uploader.upload(result.recording_path)
                self._notifier.notify_recording_link(session, url)
        except Exception as error:
            self._logger.warning(
                "Unable to deliver VoIP result or recording: session=%s error=%s",
                session.session_id, type(error).__name__,
            )
        finally:
            try:
                result.close()
            except OSError:
                self._logger.exception(
                    "Unable to remove VoIP recording: session=%s", session.session_id
                )
