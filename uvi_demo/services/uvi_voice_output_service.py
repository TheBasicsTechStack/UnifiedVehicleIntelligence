"""Voice output service for the UVI audio companion."""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(slots=True)
class VoiceInstruction:
    """Message prepared by the companion for natural voice output."""

    text: str
    interrupt_current: bool = False


class UVIVoiceOutputService:
    """Converts companion text instructions into spoken audio."""

    def __init__(self, rate: int = 178, volume: float = 0.95) -> None:
        self.rate = rate
        self.volume = volume
        self._lock = threading.Lock()

    def speak_async(self, instruction: VoiceInstruction | str) -> None:
        """Speak without blocking the cockpit UI."""
        normalized = self._normalize(instruction)
        threading.Thread(target=self.speak, args=(normalized,), daemon=True, name="uvi-voice-output").start()

    def speak(self, instruction: VoiceInstruction | str) -> None:
        """Speak one instruction synchronously on the current thread."""
        normalized = self._normalize(instruction)
        if not normalized.text:
            return

        try:
            import pyttsx3

            with self._lock:
                engine = pyttsx3.init()
                engine.setProperty("rate", self.rate)
                engine.setProperty("volume", self.volume)
                if normalized.interrupt_current:
                    engine.stop()
                engine.say(normalized.text)
                engine.runAndWait()
                engine.stop()
        except Exception:
            # The cockpit still displays the companion text if local TTS fails.
            return

    @staticmethod
    def _normalize(instruction: VoiceInstruction | str) -> VoiceInstruction:
        if isinstance(instruction, VoiceInstruction):
            return instruction
        return VoiceInstruction(text=str(instruction).strip())
