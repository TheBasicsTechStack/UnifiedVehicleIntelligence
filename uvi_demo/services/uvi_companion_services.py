"""Voice-first AI companion used by the UVI cockpit.

The companion owns conversation, context, and speech-to-text. Natural audio
playback is delegated to the UVI voice output service, matching the project
architecture where the companion decides what to say and voice output speaks it.
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from uvi_demo.services.uvi_voice_output_service import UVIVoiceOutputService, VoiceInstruction


SYSTEM_PROMPT = """You are UVI, a warm in-car audio companion for a person
travelling alone. Speak naturally like a thoughtful co-traveller. Keep replies
short (one to three sentences) because the user is driving. Never distract the
driver. If the user sounds tired, distressed, or reports a dangerous situation,
prioritize pulling over safely and contacting emergency help. Do not claim to
control the vehicle. Avoid markdown because every response is spoken aloud."""


@dataclass(slots=True)
class CompanionConfig:
    """Runtime configuration, supplied through environment variables."""

    driver_name: str = "Chandana"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    language: str = "en-IN"

    @classmethod
    def from_environment(cls) -> "CompanionConfig":
        return cls(
            driver_name=os.getenv("UVI_DRIVER_NAME", "Chandana"),
            api_key=os.getenv("UVI_LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")),
            base_url=os.getenv("UVI_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            model=os.getenv("UVI_LLM_MODEL", "gpt-4o-mini"),
            language=os.getenv("UVI_SPEECH_LANGUAGE", "en-IN"),
        )


class UVICompanionService(QObject):
    """Coordinates speech recognition, conversation, and voice instructions."""

    status_changed = Signal(str)
    transcript_ready = Signal(str)
    llm_input_ready = Signal(str)
    response_ready = Signal(str)
    listening_changed = Signal(bool)
    error_occurred = Signal(str)

    def __init__(
        self,
        config: CompanionConfig | None = None,
        voice_output: UVIVoiceOutputService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config or CompanionConfig.from_environment()
        self.voice_output = voice_output or UVIVoiceOutputService()
        self._busy = False
        self._history: list[dict[str, str]] = []
        self._lock = threading.Lock()
        self._stream_lock = threading.Lock()
        self._llm_stream_buffer = ""

    @property
    def busy(self) -> bool:
        return self._busy

    def greet(self) -> None:
        """Give the ignition greeting without calling the LLM."""
        message = f"Hi {self.config.driver_name}, how was your day? Are you going somewhere?"
        self.response_ready.emit(message)
        self.voice_output.speak_async(VoiceInstruction(message))

    def listen(self) -> None:
        """Capture one utterance from the default microphone and convert it to text."""
        if not self._claim():
            return
        self.listening_changed.emit(True)
        self.status_changed.emit("Listening...")
        threading.Thread(target=self._listen_worker, daemon=True, name="uvi-stt").start()

    def submit_text(self, text: str) -> None:
        """Text fallback useful for noisy demos and machines without a microphone."""
        print(f"[UVI SERVICE] submit_text received textbox input -> {text}", flush=True)
        self.set_llm_input_text(text)

    def set_llm_input_text(self, text: str) -> None:
        """Accept driver text and route it through the stream audio interface."""
        text = text.strip()
        if not text:
            return
        print(f"[UVI INTERFACE] set_llm_input_text -> publishing input: {text}", flush=True)
        self._publish_input_to_llm(text, emit_transcript=False)
        print("[UVI INTERFACE] routing textbox input through handle_llm_stream", flush=True)
        threading.Thread(
            target=self.handle_llm_stream,
            args=(self._demo_text_stream(text),),
            daemon=True,
            name="uvi-llm-stream-test",
        ).start()

    def handle_llm_stream(self, llm_stream: Iterable[str]) -> None:
        """Connect an LLM text stream to UVI audio output."""
        print("[UVI STREAM] handle_llm_stream started", flush=True)
        self.begin_llm_output_stream()
        for chunk in llm_stream:
            print(f"[UVI STREAM] chunk received -> {chunk!r}", flush=True)
            self.append_llm_output_stream(chunk)
        self.end_llm_output_stream()
        print("[UVI STREAM] handle_llm_stream finished", flush=True)

    def set_llm_output_stream(self, text: str) -> None:
        """Accept LLM output text and convert it into spoken audio."""
        text = text.strip()
        if not text:
            return
        self.status_changed.emit("Speaking audio output...")
        self.voice_output.speak_async(VoiceInstruction(text))
        self.status_changed.emit("Ready - type text for audio output")

    def begin_llm_output_stream(self) -> None:
        """Start a streamed LLM audio response."""
        with self._stream_lock:
            self._llm_stream_buffer = ""
        print("[UVI AUDIO] begin_llm_output_stream", flush=True)
        self.status_changed.emit("Receiving LLM audio stream...")

    def append_llm_output_stream(self, chunk: str) -> None:
        """Accept one streamed LLM text chunk and speak complete phrases."""
        if not chunk:
            return
        with self._stream_lock:
            self._llm_stream_buffer += str(chunk)
            ready_phrases = self._pop_stream_phrases()

        for phrase in ready_phrases:
            print(f"[UVI AUDIO] speaking streamed phrase -> {phrase}", flush=True)
            self.voice_output.speak_async(VoiceInstruction(phrase))
        if ready_phrases:
            self.status_changed.emit("Speaking LLM audio stream...")

    def end_llm_output_stream(self) -> None:
        """Flush the final streamed LLM text into audio."""
        with self._stream_lock:
            final_text = self._llm_stream_buffer.strip()
            self._llm_stream_buffer = ""

        if final_text:
            print(f"[UVI AUDIO] speaking final streamed text -> {final_text}", flush=True)
            self.voice_output.speak_async(VoiceInstruction(final_text))
        print("[UVI AUDIO] end_llm_output_stream", flush=True)
        self.status_changed.emit("Ready - type text for audio output")

    def _pop_stream_phrases(self) -> list[str]:
        phrases = []
        last_boundary = -1
        for index, char in enumerate(self._llm_stream_buffer):
            if char in ".!?\n":
                last_boundary = index

        if last_boundary == -1:
            return phrases

        ready_text = self._llm_stream_buffer[: last_boundary + 1]
        self._llm_stream_buffer = self._llm_stream_buffer[last_boundary + 1 :]
        start = 0
        for index, char in enumerate(ready_text):
            if char not in ".!?\n":
                continue
            phrase = ready_text[start : index + 1].strip()
            if phrase:
                phrases.append(phrase if char != "\n" else phrase.rstrip("\n"))
            start = index + 1
        return phrases

    @staticmethod
    def _demo_text_stream(text: str) -> Iterable[str]:
        """Split local textbox input into stream-like chunks for app testing."""
        for word in text.split():
            yield f"{word} "
            time.sleep(0.04)

    def _publish_input_to_llm(self, text: str, emit_transcript: bool) -> None:
        if emit_transcript:
            self.transcript_ready.emit(text)
        self.llm_input_ready.emit(text)
        print(f"[UVI INTERFACE] llm_input_ready emitted -> {text}", flush=True)
        self.status_changed.emit("Input sent to audio interface")

    def _claim(self) -> bool:
        with self._lock:
            if self._busy:
                self.status_changed.emit("Please wait for me to finish.")
                return False
            self._busy = True
            return True

    def _release(self) -> None:
        with self._lock:
            self._busy = False

    def _listen_worker(self) -> None:
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            audio = self._record_with_sounddevice(sr)
            self.status_changed.emit("Understanding...")
            text = recognizer.recognize_google(audio, language=self.config.language).strip()
            if not text:
                raise RuntimeError("I could not hear any words.")
            self._publish_input_to_llm(text, emit_transcript=True)
            self.status_changed.emit("Audio converted to text")
        except Exception as exc:
            message = self._friendly_audio_error(exc)
            self.error_occurred.emit(message)
            self.status_changed.emit(message)
        finally:
            self.listening_changed.emit(False)
            self._release()

    def _record_with_sounddevice(self, sr_module) -> object:
        """Record one short utterance without requiring PyAudio."""
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("Microphone packages missing. Run: python -m pip install -r uvi_demo\\requirements.txt") from exc

        sample_rate = 16000
        block_ms = 120
        max_seconds = 8
        silence_seconds = 1.2
        warmup_blocks = 4
        silence_blocks_needed = int(silence_seconds * 1000 / block_ms)
        max_blocks = int(max_seconds * 1000 / block_ms)
        blocksize = int(sample_rate * block_ms / 1000)
        frames = []
        noise_floor = 250.0
        silence_blocks = 0
        heard_voice = False

        self.status_changed.emit("Listening... speak now")
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16", blocksize=blocksize) as stream:
            for block_index in range(max_blocks):
                block, _overflowed = stream.read(blocksize)
                mono = block.reshape(-1).copy()
                frames.append(mono)
                level = float(np.sqrt(np.mean(mono.astype(np.float32) ** 2)))

                if block_index < warmup_blocks:
                    noise_floor = max(noise_floor * 0.7 + level * 0.3, 120.0)
                    continue

                speaking_threshold = max(noise_floor * 1.6, 320.0)
                if level > speaking_threshold:
                    heard_voice = True
                    silence_blocks = 0
                elif heard_voice:
                    silence_blocks += 1
                    if silence_blocks >= silence_blocks_needed:
                        break

                time.sleep(0.01)

        if not heard_voice:
            peak = max((int(np.max(np.abs(frame))) for frame in frames), default=0)
            if peak < 500:
                raise RuntimeError("I did not hear speech from the microphone.")

        pcm = np.concatenate(frames).astype(np.int16).tobytes()
        return sr_module.AudioData(pcm, sample_rate, 2)

    def _respond_worker(self, text: str) -> None:
        try:
            self._respond(text)
        except Exception as exc:
            self.error_occurred.emit(f"Companion error: {exc}")
            self.status_changed.emit("Ready")
        finally:
            self._release()

    def _respond(self, text: str) -> None:
        reply = self._llm_reply(text) if self.config.api_key else self._offline_reply(text)
        self._history.extend(({"role": "user", "content": text}, {"role": "assistant", "content": reply}))
        self._history = self._history[-10:]
        self.response_ready.emit(reply)
        self.status_changed.emit("Speaking...")
        self.voice_output.speak(VoiceInstruction(reply))
        self.status_changed.emit("Ready - tap the microphone to talk")

    def _llm_reply(self, text: str) -> str:
        payload = json.dumps(
            {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *self._history,
                    {"role": "user", "content": text},
                ],
                "temperature": 0.8,
                "max_tokens": 140,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=18) as response:
                data = json.load(response)
            return data["choices"][0]["message"]["content"].strip()
        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError):
            self.error_occurred.emit("LLM unavailable - using the built-in companion for this reply.")
            return self._offline_reply(text)

    def _offline_reply(self, text: str) -> str:
        lowered = text.lower()
        name = self.config.driver_name
        if any(word in lowered for word in ("tired", "sleepy", "drowsy", "exhausted")):
            return "You sound tired. Please take the next safe stop and rest for a while. I will stay with you until then."
        if any(word in lowered for word in ("sad", "lonely", "upset", "bad day")):
            return f"I am sorry it has been heavy, {name}. You do not have to fill the silence. Tell me what happened when you feel ready."
        if any(word in lowered for word in ("home", "office", "work", "college", "airport")):
            return "Got it. Settle in and keep your attention on the road; I will keep you company along the way."
        if any(word in lowered for word in ("music", "song")):
            return "Music sounds perfect. What mood are we choosing: calm, cheerful, or full road-trip energy?"
        if any(word in lowered for word in ("hello", "hi", "hey")):
            return f"Hey {name}! I am glad to be along for the drive. Where are we headed?"
        return random.choice(
            [
                "I am listening. Tell me a little more while we enjoy the drive.",
                "That makes sense. I am right here with you. How are you feeling about it?",
                "All right, I have got you. Keep your eyes on the road and tell me more.",
            ]
        )

    @staticmethod
    def _friendly_audio_error(exc: Exception) -> str:
        message = str(exc).lower()
        if "pyaudio" in message:
            return "PyAudio is unavailable, so UVI is using the alternate microphone path."
        if "no default input device" in message or "inputstream" in message:
            return "No microphone was found. Check Windows input settings, then tap the microphone again."
        if "did not hear speech" in message:
            return "I did not hear speech. Tap the microphone and speak clearly."
        if "timed out" in message:
            return "I did not hear anything. Tap the microphone when you are ready."
        if "could not understand" in message or "unknownvalue" in type(exc).__name__.lower():
            return "I could not understand that. Please try once more."
        return f"Microphone unavailable: {exc}"
