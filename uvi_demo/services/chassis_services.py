"""Chassis producer services."""

from uvi_demo.broker.kuksa_placeholder import KuksaDataBroker
from uvi_demo.services.can_signal_service_mappings import CAN_SIGNAL_SERVICE_MAPPINGS
from uvi_demo.services.domain_signal_service import DomainSignalService
from uvi_demo.services.mock_can_gateway import CANGWService


SUBSCRIBED_SIGNALS = CAN_SIGNAL_SERVICE_MAPPINGS["chassis_services"]


class ChassisService(DomainSignalService):
    """Publishes chassis, braking, steering, suspension, and tire updates."""

    def __init__(self, can_gateway: CANGWService, broker: KuksaDataBroker) -> None:
        super().__init__("chassis_services", SUBSCRIBED_SIGNALS, can_gateway, broker)

