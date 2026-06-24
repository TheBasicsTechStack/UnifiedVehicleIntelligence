"""Mock vehicle network gateway service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class CANFrame:
    """Synthetic CAN gateway frame emitted by the simulator."""

    episode_id: str
    time_sec: float
    signals: dict[str, Any]
    sequence: int
    received_at: datetime


class CANGWService(QObject):
    """Receives scripted vehicle signals and publishes gateway frames."""

    frame_received = Signal(object)
    frame_dispatched = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._sequence = 0
        self.last_signals: dict[str, Any] = {}

    def push_signals(self, episode_id: str, time_sec: float, signals: dict[str, Any]) -> CANFrame:
        """Publish one synthetic signal burst through the mock gateway."""
        self._sequence += 1
        self.last_signals.update(signals)
        frame = CANFrame(
            episode_id=episode_id,
            time_sec=time_sec,
            signals=dict(signals),
            sequence=self._sequence,
            received_at=datetime.now(),
        )
        self.frame_received.emit(frame)
        self.frame_dispatched.emit(frame)
        return frame
