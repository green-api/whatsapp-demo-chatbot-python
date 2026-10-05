from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch
from internal.calls.delivery import RecordingUploader, RecordingUploadError


class RecordingUploaderTest(IsolatedAsyncioTestCase):
    async def test_sdk_upload_uses_media_host_and_deadline(self):
        with patch("internal.calls.delivery.GreenAPI") as client:
            client.return_value.sending.sendFileByUploadAsync = AsyncMock(
                return_value=Mock(code=200, data={"idMessage": "accepted"}),
            )

            uploader = RecordingUploader("1", "token", "https://pool.media.invalid")

            with NamedTemporaryFile(suffix=".mp3") as file:
                await uploader.send("123@c.us", Path(file.name))

                client.return_value.sending.sendFileByUploadAsync.assert_awaited_once_with(
                    "123@c.us",
                    file.name,
                    "call-recording.mp3",
                )

            self.assertEqual(client.call_args.kwargs["media"], "https://pool.media.invalid")
            self.assertEqual(client.call_args.kwargs["media_timeout"], 30)

    async def test_failed_or_incomplete_response_is_rejected(self):
        with patch("internal.calls.delivery.GreenAPI") as client:
            uploader = RecordingUploader("1", "token", "https://pool.media.invalid")

            client.return_value.sending.sendFileByUploadAsync = AsyncMock()

            with NamedTemporaryFile(suffix=".mp3") as file:
                for response in (Mock(code=500, data=None), Mock(code=200, data={})):
                    client.return_value.sending.sendFileByUploadAsync.return_value = response

                    with self.assertRaises(RecordingUploadError):
                        await uploader.send("123@c.us", Path(file.name))
