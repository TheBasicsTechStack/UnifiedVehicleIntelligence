# UVI Demo - Codex Project Setup

Unified Vehicle Intelligence (UVI) is a Software Defined Vehicle demo built
around one source of truth, intelligent insights, and safer journeys.

## Core Demo Story

When the user clicks the KL15 key:

1. Vehicle ignition turns on
2. Linux HPC boots
3. Execution Manager starts
4. Service manifest is read
5. Mock CAN Gateway starts
6. KUKSA Data Broker starts
7. Producer services start
8. Dashboard cockpit loads
9. UVI Companion runs in the background
10. UVI Voice Output speaks useful companion messages

## Applications

### Dashboard / Cockpit

The dashboard is the visible in-vehicle cockpit experience. It shows speed,
battery, range, navigation, weather, vehicle health, windshield ambience, and
UVI companion messages.

### UVI Companion

The companion reads vehicle context, accepts typed or spoken driver input,
generates short helpful responses, and sends voice instructions to the audio
service.

### UVI Voice Output

Chandana's voice-output responsibility is represented by
`uvi_voice_output_service.py`. It receives companion text, converts it to local
speech with TTS, and keeps playback separate from the LLM/conversation logic.

## Startup Order

1. Mock CAN Gateway
2. KUKSA Data Broker
3. Producer Services in parallel
4. Dashboard Application
5. UVI Companion Application
6. UVI Voice Output Service

## Suggested Project Structure

```text
uvi_demo/
  main.py
  requirements.txt
  README.md
  service_manifest.json
  execution_manager.py
  ui/
    boot_screen.py
    cockpit_screen.py
    widgets/
      companion_card.py
  services/
    mock_can_gateway.py
    powertrain_services.py
    chassis_services.py
    body_services.py
    adas_services.py
    infotainment_services.py
    connectivity_services.py
    driver_monitoring_services.py
    vehicle_health_services.py
    uvi_companion_services.py
    uvi_voice_output_service.py
  broker/
    kuksa_placeholder.py
  simulator/
    episode_data_generator.py
    episodes/
  assets/
```

## Voice Task Flow

1. Driver taps `MIC`
2. UVI records a short microphone utterance
3. SpeechRecognition converts the voice message to text
4. UVI Companion generates a short safe response
5. UVI Voice Output converts that response to speech

The architecture keeps speech-to-text, companion intelligence, and text-to-speech
separated so each team area can evolve independently.
