"""Vehicle health producer services."""

from uvi_demo.broker.kuksa_placeholder import KuksaDataBroker
from uvi_demo.services.can_signal_service_mappings import CAN_SIGNAL_SERVICE_MAPPINGS
from uvi_demo.services.domain_signal_service import DomainSignalService
from uvi_demo.services.mock_can_gateway import CANGWService


SUBSCRIBED_SIGNALS = CAN_SIGNAL_SERVICE_MAPPINGS["vehicle_health_services"]


class VehicleHealthService(DomainSignalService):
    """Publishes diagnostics, maintenance, and security updates to the data broker."""

    def __init__(self, can_gateway: CANGWService, broker: KuksaDataBroker) -> None:
        super().__init__("vehicle_health_services", SUBSCRIBED_SIGNALS, can_gateway, broker)

