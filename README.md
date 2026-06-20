UVI Demo — Codex Project Setup
You are helping build Unified Vehicle Intelligence (UVI), a demo of a Software Defined Vehicle running on a Linux/HPC-inspired architecture.
The goal is to create an impressive in-vehicle cockpit demo where judges feel they are sitting inside a modern intelligent vehicle.
________________________________________
Core Demo Story
When the user clicks the KL15 key:
1.	Vehicle ignition turns ON
2.	Linux HPC boots
3.	Execution Manager starts
4.	Service manifest is read
5.	Mock CAN Gateway starts
6.	KUKSA Data Broker starts
7.	Producer services start
8.	Dashboard cockpit loads
9.	UVI Companion runs headless in background
________________________________________
Applications
There are only two real applications on the HPC:
1. Dashboard Application
Visible cockpit application.
This is not a simple data dashboard.
It should create an immersive driver-seat experience.
Responsibilities:
•	Render steering wheel / cockpit view
•	Render windshield-like outside ambience
•	Show real-time speed, battery, range, weather, navigation, vehicle health
•	Animate speed and gauges from broker data
•	Simulate outside world movement from vehicle speed
•	Show weather effects such as rain, night, fog, storm
•	Show windshield wiper animation when rain is active
•	Show UVI companion message cards
•	Make judges feel like they are inside a moving modern vehicle
The Dashboard must consume data only from the data broker layer.
________________________________________
2. UVI Companion Application
Headless background AI companion.
Responsibilities:
•	Read real-time context from data broker
•	Build vehicle + driver + journey context
•	Generate useful insights
•	Speak through TTS/audio
•	Act like a companion, not only a warning system
________________________________________
Infrastructure / Background Services
Mock CAN Gateway
A mocked vehicle network gateway.
Responsibilities:
•	Receive synthetic raw vehicle signals from a hidden episode data generator
•	Provide raw signal streams to producer services
•	Emulate the CAN/Ethernet gateway dependency used by domain services
KUKSA Data Broker
Acts as the vehicle data broker / single source of truth.
Responsibilities:
•	Store normalized VSS-style vehicle data
•	Maintain latest state
•	Publish updates
•	Serve Dashboard and UVI Companion
Producer Services
Background services. They are not user-facing apps.
Each producer service reads raw data from Mock CAN Gateway and writes normalized values to KUKSA.
Producer service groups:
1.	Powertrain Services
2.	Chassis Services
3.	Body Services
4.	ADAS Services
5.	Infotainment Services
6.	Connectivity Services
7.	Driver Monitoring Services
8.	Vehicle Health Services
________________________________________
Hidden Demo Tool
Episode Data Generator
This is not part of the vehicle stack.
Responsibilities:
•	Load demo episodes
•	Generate synthetic raw signals
•	Pump data into Mock CAN Gateway
It should be treated as a testing/simulation tool, not as a vehicle application.
________________________________________
Execution Manager
Build a lightweight Adaptive AUTOSAR-inspired Execution Manager in Python.
Responsibilities:
•	Read service_manifest.json
•	Launch services in dependency order
•	Show startup logs
•	Check health endpoints
•	Keep process handles
•	Gracefully stop services
Startup order:
1.	Mock CAN Gateway
2.	KUKSA Data Broker
3.	Producer Services in parallel
4.	Dashboard Application
5.	UVI Companion Application
Do not include Episode Data Generator in the manifest.
________________________________________
Phase 1 Implementation
Implement only the boot and cockpit shell first.
Do not implement real KUKSA integration yet.
Create a Python project with PySide6.
Phase 1 requirements:
1.	Fullscreen dark automotive UI
2.	Bottom-right KL15 key button
3.	When clicked, key rotates clockwise
4.	Show boot sequence:
o	KL15 ON
o	Booting Linux HPC…
o	Starting Execution Manager…
o	Reading Service Manifest…
o	Starting Mock CAN Gateway…
o	Starting KUKSA Data Broker…
o	Starting Producer Services…
o	Starting Dashboard Application…
o	Starting UVI Companion…
5.	After boot, show cockpit screen
6.	Cockpit screen must include:
o	Steering wheel visual
o	Digital speed indicator
o	Battery/range card
o	Navigation card
o	Weather card
o	Vehicle health card
o	UVI companion card
o	Windshield ambience area
7.	Use mock/default data for now
8.	Keep architecture ready for future broker-driven updates
________________________________________
Suggested Project Structure
uvi_demo/ ├── main.py ├── requirements.txt ├── README.md ├── service_manifest.json ├── execution_manager.py ├── ui/ │ ├── boot_screen.py │ ├── cockpit_screen.py │ ├── widgets/ │ │ ├── key_button.py │ │ ├── steering_wheel.py │ │ ├── speed_cluster.py │ │ ├── vehicle_cards.py │ │ ├── windshield_view.py │ │ └── companion_card.py ├── services/ │ ├── mock_can_gateway.py │ ├── powertrain_services.py │ ├── chassis_services.py │ ├── body_services.py │ ├── adas_services.py │ ├── infotainment_services.py │ ├── connectivity_services.py │ ├── driver_monitoring_services.py │ ├── vehicle_health_services.py │ └── uvi_companion_services.py ├── broker/ │ └── kuksa_placeholder.py ├── simulator/ │ ├── episode_data_generator.py │ └── episodes/ └── assets/
________________________________________
Important Design Direction
Make the first experience visually impressive.
The dashboard should feel like a premium EV cockpit, not a web admin dashboard.
Use:
•	Dark theme
•	Neon/cyan accents
•	Smooth animations
•	Large central speed
•	Steering wheel silhouette
•	Moving road/windshield ambience
•	Rain/wiper-ready design
Keep code modular and future-ready.
