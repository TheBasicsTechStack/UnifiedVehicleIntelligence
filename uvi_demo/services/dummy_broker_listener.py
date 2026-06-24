"""Dummy broker listener for backend integration testing."""

from __future__ import annotations

from collections import defaultdict

from uvi_demo.broker.kuksa_placeholder import BrokerUpdate, KuksaDataBroker


class DummyBrokerListener:
    """Records broker updates and optionally prints a compact trace."""

    def __init__(self, broker: KuksaDataBroker, print_updates: bool = False) -> None:
        self.updates: list[BrokerUpdate] = []
        self.print_updates = print_updates
        self._pending: dict[tuple[str, float, str], list[BrokerUpdate]] = defaultdict(list)
        broker.subscribe("*", self.on_update)

    def on_update(self, update: BrokerUpdate) -> None:
        """Handle one broker update."""
        self.updates.append(update)
        if not self.print_updates:
            return
        key = (update.episode_id, update.time_sec, update.source_service)
        self._pending[key].append(update)

    def flush(self) -> None:
        """Print grouped listener updates and clear the pending buffer."""
        if not self.print_updates or not self._pending:
            return
        for (episode_id, time_sec, source_service), updates in sorted(self._pending.items()):
            print(
                "BROKER LISTENER RECEIVED | "
                f"episode={episode_id} | "
                f"time={time_sec:.0f}s | "
                f"source_service={source_service} | "
                f"signals={len(updates)}"
            )
            for update in sorted(updates, key=lambda item: item.path):
                print(f"  - {update.path} = {update.value!r}")
        self._pending.clear()
