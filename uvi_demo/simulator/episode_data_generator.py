"""Episode data generator for synthetic raw signals."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QElapsedTimer, QTimer, Signal

from uvi_demo.services.mock_can_gateway import CANGWService


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "assets" / "episodeScripts"
REALTIME_CADENCE_SECONDS = (5.0, 15.0, 25.0, 30.0)
NOISE_BY_SIGNAL = {
    "VEH_SPEED": 2.5,
    "CABIN_TEMP_C": 0.25,
    "REAR_CABIN_TEMP_C": 0.3,
    "OUTSIDE_TEMP_C": 0.2,
    "BMS_TEMP_C": 0.35,
    "WEATHER_VISIBILITY_PERCENT": 1.4,
    "DMS_FATIGUE_SCORE": 0.012,
    "DMS_ATTENTION_SCORE": 0.012,
    "DMS_STRESS_SCORE": 0.012,
}


@dataclass(frozen=True)
class EpisodeEvent:
    """A timestamped burst of script signals."""

    time_sec: float
    signals: dict[str, Any]
    authored: bool = False


@dataclass(frozen=True)
class EpisodeScript:
    """Loaded episode script metadata and timeline."""

    episode_id: str
    episode_name: str
    duration_seconds: float
    target: str
    ambience: dict[str, Any]
    timeline: tuple[EpisodeEvent, ...]


class EpisodeDataGenerator(QObject):
    """Loads episode scripts and pushes timeline signals through CANGWService."""

    episode_started = Signal(object)
    event_pushed = Signal(object, object)
    playback_progress = Signal(float, float)
    playback_finished = Signal(object)

    def __init__(
        self,
        can_gateway: CANGWService,
        script_dir: Path = SCRIPT_DIR,
        playback_speed: float = 1.0,
    ) -> None:
        super().__init__()
        self.can_gateway = can_gateway
        self.script_dir = script_dir
        self.playback_speed = max(0.1, playback_speed)
        self._scripts: dict[str, EpisodeScript] = {}
        self._active_script: EpisodeScript | None = None
        self._next_event_index = 0
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._tick)

    def list_episodes(self) -> list[EpisodeScript]:
        """Return all available episode scripts sorted by episode id."""
        if not self._scripts:
            self.reload_scripts()
        return [self._scripts[key] for key in sorted(self._scripts)]

    def reload_scripts(self) -> None:
        """Load episode scripts from disk."""
        scripts: dict[str, EpisodeScript] = {}
        for path in sorted(self.script_dir.glob("EP*.json")):
            script = self._load_script(path)
            scripts[script.episode_id] = script
        self._scripts = scripts

    def play(self, episode_id: str) -> None:
        """Start playback for an episode id."""
        if not self._scripts:
            self.reload_scripts()
        script = self._scripts[episode_id]
        self.stop()
        self._active_script = script
        self._next_event_index = 0
        self._clock.start()
        self.episode_started.emit(script)
        self._timer.start()
        self._tick()

    def stop(self) -> None:
        """Stop active episode playback."""
        self._timer.stop()
        self._active_script = None
        self._next_event_index = 0

    def active_script(self) -> EpisodeScript | None:
        """Return the currently playing episode, if any."""
        return self._active_script

    def _tick(self) -> None:
        script = self._active_script
        if script is None:
            return

        elapsed_sec = self._clock.elapsed() / 1000.0 * self.playback_speed
        while self._next_event_index < len(script.timeline):
            event = script.timeline[self._next_event_index]
            if event.time_sec > elapsed_sec:
                break
            frame = self.can_gateway.push_signals(script.episode_id, event.time_sec, event.signals)
            self.event_pushed.emit(event, frame)
            self._next_event_index += 1

        self.playback_progress.emit(min(elapsed_sec, script.duration_seconds), script.duration_seconds)
        if elapsed_sec >= script.duration_seconds:
            self._timer.stop()
            self.playback_progress.emit(script.duration_seconds, script.duration_seconds)
            self.playback_finished.emit(script)
            self._active_script = None

    def _load_script(self, path: Path) -> EpisodeScript:
        with path.open("r", encoding="utf-8") as file:
            raw = json.load(file)

        authored_timeline = tuple(
            EpisodeEvent(time_sec=float(item["timeSec"]), signals=dict(item.get("signals", {})), authored=True)
            for item in raw.get("timeline", [])
        )
        duration_seconds = float(
            raw.get("durationSeconds", authored_timeline[-1].time_sec if authored_timeline else 480)
        )
        timeline = self._expand_timeline(str(raw["episodeId"]), authored_timeline, duration_seconds)
        return EpisodeScript(
            episode_id=str(raw["episodeId"]),
            episode_name=str(raw.get("episodeName", raw["episodeId"])),
            duration_seconds=duration_seconds,
            target=str(raw.get("target", "mock_can_gateway")),
            ambience=dict(raw.get("ambience", {})),
            timeline=timeline,
        )

    def _expand_timeline(
        self,
        episode_id: str,
        authored_timeline: tuple[EpisodeEvent, ...],
        duration_seconds: float,
    ) -> tuple[EpisodeEvent, ...]:
        authored = tuple(sorted(authored_timeline, key=lambda event: event.time_sec))
        if not authored:
            return ()

        rng = random.Random(sum(ord(char) for char in episode_id))
        expanded: list[EpisodeEvent] = []
        state: dict[str, Any] = {}

        for index, event in enumerate(authored):
            state.update(event.signals)
            expanded.append(EpisodeEvent(event.time_sec, dict(state), authored=True))

            next_event = authored[index + 1] if index + 1 < len(authored) else None
            next_time = next_event.time_sec if next_event else duration_seconds
            if next_time <= event.time_sec:
                continue

            next_state = dict(state)
            if next_event:
                next_state.update(next_event.signals)

            cursor = event.time_sec
            while True:
                remaining = next_time - cursor
                if remaining in REALTIME_CADENCE_SECONDS:
                    break
                valid_cadences = [
                    cadence
                    for cadence in REALTIME_CADENCE_SECONDS
                    if cadence < remaining
                    and (
                        remaining - cadence in REALTIME_CADENCE_SECONDS
                        or remaining - cadence > max(REALTIME_CADENCE_SECONDS)
                    )
                ]
                if not valid_cadences:
                    break
                cursor += rng.choice(valid_cadences)
                ratio = (cursor - event.time_sec) / (next_time - event.time_sec)
                signals = self._interpolated_signals(state, next_state, ratio, rng)
                expanded.append(EpisodeEvent(cursor, signals, authored=False))

        return tuple(sorted(expanded, key=lambda event: event.time_sec))

    def _interpolated_signals(
        self,
        current: dict[str, Any],
        upcoming: dict[str, Any],
        ratio: float,
        rng: random.Random,
    ) -> dict[str, Any]:
        signals: dict[str, Any] = {}
        for key in sorted(set(current) | set(upcoming)):
            current_value = current.get(key, upcoming.get(key))
            upcoming_value = upcoming.get(key, current_value)
            if self._is_number(current_value) and self._is_number(upcoming_value):
                value = float(current_value) + (float(upcoming_value) - float(current_value)) * ratio
                value = self._apply_noise(key, value, rng)
                signals[key] = self._clamp_signal(key, value)
            else:
                signals[key] = current_value
        return signals

    def _apply_noise(self, key: str, value: float, rng: random.Random) -> float:
        amplitude = NOISE_BY_SIGNAL.get(key, 0.0)
        if amplitude <= 0:
            return value
        return value + rng.uniform(-amplitude, amplitude)

    def _clamp_signal(self, key: str, value: float) -> float | int:
        if key in {"BMS_SOC", "WEATHER_VISIBILITY_PERCENT"}:
            value = max(0.0, min(100.0, value))
        elif key in {"DMS_FATIGUE_SCORE", "DMS_ATTENTION_SCORE", "DMS_STRESS_SCORE"}:
            value = max(0.0, min(1.0, value))
        elif key == "VEH_SPEED":
            value = max(0.0, value)

        if key.endswith("_MIN") or key.endswith("_KM") or key in {"VEH_SPEED", "BMS_SOC"}:
            return int(round(value))
        return round(value, 2)

    def _is_number(self, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
