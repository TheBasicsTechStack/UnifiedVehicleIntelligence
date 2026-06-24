"""In-process KUKSA-like data broker for the demo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class BrokerUpdate:
    """One value update written by a domain service."""

    path: str
    value: Any
    source_service: str
    episode_id: str
    time_sec: float
    received_at: datetime


class KuksaDataBroker(QObject):
    """Small in-memory broker with KUKSA-style path/value semantics."""

    value_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._values: dict[str, Any] = {}
        self._subscribers: dict[str, list[Callable[[BrokerUpdate], None]]] = {}

    def set_value(
        self,
        path: str,
        value: Any,
        source_service: str,
        episode_id: str = "",
        time_sec: float = 0.0,
    ) -> BrokerUpdate:
        """Set one broker value and notify listeners."""
        self._values[path] = value
        update = BrokerUpdate(
            path=path,
            value=value,
            source_service=source_service,
            episode_id=episode_id,
            time_sec=time_sec,
            received_at=datetime.now(),
        )
        self.value_changed.emit(update)
        for callback in self._subscribers.get(path, []):
            callback(update)
        for callback in self._subscribers.get("*", []):
            callback(update)
        return update

    def set_many(
        self,
        values: dict[str, Any],
        source_service: str,
        episode_id: str = "",
        time_sec: float = 0.0,
    ) -> list[BrokerUpdate]:
        """Set multiple broker values from one service frame."""
        return [
            self.set_value(path, value, source_service, episode_id, time_sec)
            for path, value in values.items()
        ]

    def get_value(self, path: str, default: Any = None) -> Any:
        """Return the latest value for a path."""
        return self._values.get(path, default)

    def snapshot(self) -> dict[str, Any]:
        """Return a copy of all current broker values."""
        return dict(self._values)

    def subscribe(self, path: str, callback: Callable[[BrokerUpdate], None]) -> None:
        """Subscribe to a path, or '*' for all broker updates."""
        self._subscribers.setdefault(path, []).append(callback)
