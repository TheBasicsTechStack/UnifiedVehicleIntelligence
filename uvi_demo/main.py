"""Application entry point for the UVI demo."""

from PySide6.QtWidgets import QApplication

from uvi_demo.broker.kuksa_placeholder import KuksaDataBroker
from uvi_demo.services.adas_services import ADASService
from uvi_demo.services.body_services import BodyService
from uvi_demo.services.chassis_services import ChassisService
from uvi_demo.services.connectivity_services import ConnectivityService
from uvi_demo.services.driver_monitoring_services import DriverMonitoringService
from uvi_demo.services.dummy_broker_listener import DummyBrokerListener
from uvi_demo.services.infotainment_services import InfotainmentService
from uvi_demo.services.mock_can_gateway import CANGWService
from uvi_demo.services.powertrain_services import PowertrainService
from uvi_demo.services.uvi_companion_services import UVICompanionService
from uvi_demo.services.vehicle_health_services import VehicleHealthService
from uvi_demo.simulator.episode_data_generator import EpisodeDataGenerator
from uvi_demo.ui.boot_screen import BootScreen
from uvi_demo.ui.cockpit_screen import CockpitScreen
from uvi_demo.ui.data_generator_window import DataGeneratorWindow


def main() -> None:
    """Start the vehicle UI and data generator simulator."""
    app = QApplication([])
    can_gateway = CANGWService()
    broker = KuksaDataBroker()
    generator = EpisodeDataGenerator(can_gateway)
    domain_services = [
        PowertrainService(can_gateway, broker),
        ChassisService(can_gateway, broker),
        ADASService(can_gateway, broker),
        BodyService(can_gateway, broker),
        DriverMonitoringService(can_gateway, broker),
        InfotainmentService(can_gateway, broker),
        ConnectivityService(can_gateway, broker),
        VehicleHealthService(can_gateway, broker),
        UVICompanionService(can_gateway, broker),
    ]
    broker_listener = DummyBrokerListener(broker, print_updates=True)
    can_gateway.frame_dispatched.connect(lambda _frame: broker_listener.flush())
    cockpit = CockpitScreen(can_gateway=can_gateway, generator=generator, show_simulator_panel=False)
    vehicle_window = BootScreen(cockpit)
    generator_window = DataGeneratorWindow(generator)

    vehicle_window.showFullScreen()
    generator_window.show()
    app.runtime = (broker, domain_services, broker_listener)
    app.windows = (vehicle_window, generator_window)
    app.exec()


if __name__ == "__main__":
    main()
