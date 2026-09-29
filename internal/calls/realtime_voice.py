"""One OpenAI Realtime conversation per Green-API call."""

from __future__ import annotations
from collections import deque
from fractions import Fraction
from typing import Callable
from aiortc import AudioStreamTrack, MediaStreamTrack
from aiortc.mediastreams import MediaStreamError
from openai import AsyncOpenAI
from .recording import CallRecorder
import asyncio
import base64
import av


# Constants

RATE = 24 * 1000

FRAME_SAMPLES = 480  # 20 ms of mono PCM16

FRAME_BYTES = 2 * FRAME_SAMPLES

MAX_BUFFER_FRAMES = 500  # 10 seconds, excess audio is a call error

LANGUAGE_NAMES = {
    "ru": "Russian",
    "en": "English",
    "he": "Hebrew",
    "es": "Spanish",
    "kz": "Kazakh",
}


class BotOutputTrack(AudioStreamTrack):
    def __init__(self, voice: VoiceBotSession, generation: int):
        super().__init__()
        self._voice = voice
        self._generation = generation
        self._pts = 0
        self._next_frame_at: float | None = None

    async def recv(self) -> av.AudioFrame:
        loop = asyncio.get_running_loop()

        if self._next_frame_at is None:
            self._next_frame_at = loop.time()

        await asyncio.sleep(max(0, self._next_frame_at - loop.time()))

        self._next_frame_at = max(self._next_frame_at + 0.02, loop.time())

        pcm = self._voice.take_frame(self._generation)

        if self._voice.recorder is not None:
            self._voice.recorder.add_bot(pcm, self._generation)

        frame = av.AudioFrame(format="s16", layout="mono", samples=FRAME_SAMPLES)

        frame.planes[0].update(pcm)

        frame.sample_rate = RATE
        frame.time_base = Fraction(1, RATE)
        frame.pts = self._pts
        self._pts += FRAME_SAMPLES

        return frame


class CallerAudioSink:
    def __init__(self, voice: VoiceBotSession, generation: int):
        self._voice = voice
        self._generation = generation
        self._task: asyncio.Task | None = None

    async def attach(self, track: MediaStreamTrack) -> None:
        if track.kind != "audio":
            raise ValueError("Expected an audio track")

        self._task = asyncio.create_task(self._consume(track))

    async def _consume(self, track: MediaStreamTrack) -> None:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=RATE)

        try:
            while self._generation == self._voice.generation:
                frame = await track.recv()

                for converted in resampler.resample(frame):
                    if self._generation != self._voice.generation:
                        return

                    pcm = bytes(converted.planes[0])[:converted.samples * 2]

                    if self._voice.recorder is not None:
                        self._voice.recorder.add_caller(pcm, self._generation)

                    await self._voice.append_input(pcm)
        except MediaStreamError:
            pass
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._voice.fail(error)

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

            self._task = None


class VoiceBotSession:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        voice: str,
        language: str,
        on_error: Callable[[Exception], None],
        recorder: CallRecorder | None = None,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._voice = voice
        self._language = language
        self._on_error = on_error
        self.recorder = recorder
        self._manager = None
        self._connection = None
        self._reader: asyncio.Task | None = None
        self._closed = False
        self._greeted = False
        self.generation = 0
        self._frames: deque[tuple[str | None, bytes]] = deque()
        self._partial = bytearray()
        self._last_item: str | None = None
        self._played: dict[str, int] = {}
        self._truncated: set[str] = set()
        self._finished: set[str] = set()

    async def start(self) -> None:
        if not self._client.api_key:
            raise ValueError("OpenAI API key is required for voice calls")

        self._manager = self._client.realtime.connect(model=self._model, max_retries=0)
        self._connection = await self._manager.__aenter__()

        try:
            await self._connection.session.update(session={
                "type": "realtime",
                "model": self._model,
                "output_modalities": ["audio"],
                "instructions": (
                    "You are a helpful voice assistant in a WhatsApp phone call. "
                    f"Speak in {LANGUAGE_NAMES.get(self._language, 'English')}. "
                    "Speak naturally and briefly. Do not use markdown."
                ),
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": RATE},
                        "turn_detection": {"type": "semantic_vad"},
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": RATE},
                        "voice": self._voice,
                    },
                },
            })

            while True:
                event = await asyncio.wait_for(self._connection.recv(), timeout=15)

                if event.type == "session.updated":
                    break

                if event.type == "error":
                    raise RuntimeError("OpenAI Realtime rejected session configuration")

            self._reader = asyncio.create_task(self._read_events())
        except BaseException:
            await self.close()
            raise

    async def greet_once(self) -> None:
        if self._greeted or self._closed:
            return

        self._greeted = True

        await self._connection.response.create(response={
            "instructions": (
                f"Greet the caller briefly in {LANGUAGE_NAMES.get(self._language, 'English')}."
            ),
        })

    def new_output_track(self) -> BotOutputTrack:
        self.generation += 1

        if self.recorder is not None:
            self.recorder.set_generation(self.generation)

        self._frames.clear()
        self._partial.clear()

        self._last_item = None

        return BotOutputTrack(self, self.generation)

    def new_input_sink(self) -> CallerAudioSink:
        return CallerAudioSink(self, self.generation)

    async def append_input(self, pcm: bytes) -> None:
        if pcm and not self._closed:
            await self._connection.input_audio_buffer.append(
                audio=base64.b64encode(pcm).decode("ascii")
            )

    def take_frame(self, generation: int) -> bytes:
        if generation != self.generation or not self._frames:
            return bytes(FRAME_BYTES)

        item, pcm = self._frames.popleft()

        if item is not None:
            self._played[item] = self._played.get(item, 0) + FRAME_SAMPLES

        return pcm

    def _queue_audio(self, item_id: str, pcm: bytes) -> None:
        if item_id in self._truncated:
            return

        if self._last_item != item_id:
            self._partial.clear()

        self._last_item = item_id

        self._partial.extend(pcm)

        while len(self._partial) >= FRAME_BYTES:
            if len(self._frames) >= MAX_BUFFER_FRAMES:
                raise BufferError("OpenAI audio exceeds ten seconds of queued playback")

            self._frames.append((item_id, bytes(self._partial[:FRAME_BYTES])))

            del self._partial[:FRAME_BYTES]

    def _finish_audio(self, item_id: str) -> None:
        if item_id in self._truncated:
            return

        self._finished.add(item_id)

        if self._partial and self._last_item == item_id:
            if len(self._frames) >= MAX_BUFFER_FRAMES:
                raise BufferError("OpenAI audio exceeds ten seconds of queued playback")

            pcm = bytes(self._partial).ljust(FRAME_BYTES, b"\x00")

            self._frames.append((item_id, pcm))
            self._partial.clear()

    async def _interrupt(self) -> None:
        item = self._last_item
        pending = bool(self._frames or self._partial)

        self._frames.clear()
        self._partial.clear()

        if item is not None and item not in self._truncated and (
            item not in self._finished or pending
        ):
            self._truncated.add(item)

            await self._connection.conversation.item.truncate(
                item_id=item,
                content_index=0,
                audio_end_ms=self._played.get(item, 0) * 1000 // RATE,
            )

    async def _read_events(self) -> None:
        try:
            async for event in self._connection:
                if event.type == "response.output_audio.delta":
                    self._queue_audio(event.item_id, base64.b64decode(event.delta))
                elif event.type == "response.output_audio.done":
                    self._finish_audio(event.item_id)
                elif event.type == "input_audio_buffer.speech_started":
                    await self._interrupt()
                elif event.type == "response.done" and event.response.status == "failed":
                    raise RuntimeError("OpenAI Realtime response failed")
                elif event.type == "error":
                    raise RuntimeError("OpenAI Realtime reported an error")

            if not self._closed:
                raise ConnectionError("OpenAI Realtime connection closed")
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.fail(error)

    def fail(self, error: Exception) -> None:
        if not self._closed:
            self._on_error(error)

    async def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        if self._reader is not None:
            self._reader.cancel()
            await asyncio.gather(self._reader, return_exceptions=True)

        if self._manager is not None:
            await self._manager.__aexit__(None, None, None)

        await self._client.close()
