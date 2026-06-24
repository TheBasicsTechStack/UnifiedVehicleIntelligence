"""Base domain service that bridges CANGW frames into the data broker."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from uvi_demo.broker.kuksa_placeholder import KuksaDataBroker
from uvi_demo.services.mock_can_gateway import CANFrame, CANGWService


class DomainSignalService(QObject):
    """Filters generic CANGW frames into one service's subscribed broker paths."""

    broker_write = Signal(str, int)

    def __init__(
        self,
        service_name: str,
        subscribed_signals: tuple[str, ...],
        can_gateway: CANGWService,
        broker: KuksaDataBroker,
    ) -> None:
        super().__init__()
        self.service_name = service_name
        self.subscribed_signals = set(subscribed_signals)
        self.broker = broker
        self.last_write_count = 0
        can_gateway.frame_received.connect(self.on_can_frame)

    def on_can_frame(self, frame: CANFrame) -> None:
        """Write this service's signals from a CANGW frame into the broker."""
        selected = {
            path: value
            for path, value in frame.signals.items()
            if path in self.subscribed_signals
        }
        if not selected:
            self.last_write_count = 0
            return
        self.broker.set_many(
            selected,
            source_service=self.service_name,
            episode_id=frame.episode_id,
            time_sec=frame.time_sec,
        )
        self.last_write_count = len(selected)
        self.broker_write.emit(self.service_name, len(selected))
