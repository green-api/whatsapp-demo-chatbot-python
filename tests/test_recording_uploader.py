from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase
from unittest.mock import Mock, patch
from internal.calls.delivery import RecordingUploader, RecordingUploadError


class RecordingUploaderTest(TestCase):
    def test_sdk_upload_uses_media_host_and_deadline(self):
        with patch("internal.calls.delivery.GreenAPI") as client:
            client.return_value.sending.uploadFile.return_value = Mock(
                code=200, data={"urlFile": "https://media.invalid/recording.mp3"},
            )

            uploader = RecordingUploader("1", "token", "https://pool.media.invalid")

            with NamedTemporaryFile(suffix=".mp3") as file:
                url = uploader.upload(Path(file.name))

                client.return_value.sending.uploadFile.assert_called_once_with(file.name)

            self.assertEqual(url, "https://media.invalid/recording.mp3")
            self.assertEqual(client.call_args.kwargs["media"], "https://pool.media.invalid")
            self.assertEqual(client.call_args.kwargs["media_timeout"], 30)
            client.return_value.session.close.assert_called_once()

    def test_failed_or_incomplete_response_is_rejected(self):
        with patch("internal.calls.delivery.GreenAPI") as client:
            uploader = RecordingUploader("1", "token", "https://pool.media.invalid")

            with NamedTemporaryFile(suffix=".mp3") as file:
                for response in (Mock(code=500, data=None), Mock(code=200, data={}),
                                 Mock(code=200, data={"urlFile": "invalid"})):
                    client.return_value.sending.uploadFile.return_value = response

                    with self.assertRaises(RecordingUploadError):
                        uploader.upload(Path(file.name))
