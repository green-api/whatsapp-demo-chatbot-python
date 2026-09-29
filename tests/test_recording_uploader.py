from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from internal.calls.delivery import RecordingUploader, RecordingUploadError
import asyncio


class FakeResponse:
    def __init__(self, status=200, body=None, error=None):
        self.status = status
        self.body = {"idMessage": "accepted"} if body is None else body
        self.error = error

    async def __aenter__(self):
        if self.error:
            raise self.error

        return self

    async def __aexit__(self, *args):
        return None

    async def json(self):
        return self.body


class FakeSession:
    def __init__(self, response, captured, **kwargs):
        self.response = response
        self.captured = captured
        self.captured["timeout"] = kwargs["timeout"].total

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def post(self, url, data):
        self.captured["url"] = url

        if isinstance(data, FakeFormData):
            self.captured["fields"] = data.fields

        return self.response


class FakeFormData:
    def __init__(self):
        self.fields = []

    def add_field(self, name, value, **options):
        self.fields.append((name, value, options))


class RecordingUploaderTest(IsolatedAsyncioTestCase):
    async def test_multipart_and_total_deadline(self):
        captured = {}

        with NamedTemporaryFile(suffix=".mp3") as file:
            file.write(b"audio")
            file.flush()

            with patch("internal.calls.delivery.aiohttp.FormData", FakeFormData), patch(
                "internal.calls.delivery.aiohttp.ClientSession",
                side_effect=lambda **kwargs: FakeSession(FakeResponse(), captured, **kwargs),
            ):
                await RecordingUploader("1", "token").send("123@c.us", Path(file.name))

        self.assertEqual(captured["timeout"], 30)

        self.assertEqual(
            captured["url"],
            "https://media.green-api.com/waInstance1/sendFileByUpload/token",
        )

        names = [name for name, _, _ in captured["fields"]]

        self.assertEqual(names, ["chatId", "fileName", "file"])
        self.assertEqual(captured["fields"][1][1], "call-recording.mp3")
        self.assertEqual(captured["fields"][2][2]["content_type"], "audio/mpeg")

    async def test_http_error_missing_id_and_timeout_are_failures(self):
        with NamedTemporaryFile(suffix=".mp3") as file:
            for response, expected in (
                (FakeResponse(status=500), RecordingUploadError),
                (FakeResponse(body={"other": "value"}), RecordingUploadError),
                (FakeResponse(error=asyncio.TimeoutError()), asyncio.TimeoutError),
            ):
                with self.subTest(expected=expected):
                    with patch(
                        "internal.calls.delivery.aiohttp.ClientSession",
                        side_effect=lambda **kwargs: FakeSession(response, {}, **kwargs),
                    ):
                        with self.assertRaises(expected):
                            await RecordingUploader("1", "token").send("123@c.us", Path(file.name))
