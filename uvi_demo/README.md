# UVI Demo

PySide6 cockpit demo with a voice-first AI travel companion.

## Run

Use Python 3.11 or 3.12:

```powershell
python -m pip install -r uvi_demo/requirements.txt
$env:UVI_LLM_API_KEY="your-api-key"
python -m uvi_demo.main
```

The companion accepts both microphone and typed input. Microphone speech is
converted to text, sent through the companion, and then spoken by the separate
UVI voice output service. Without an API key it uses a small built-in
conversation fallback, so the demo remains usable offline. Microphone input
uses sounddevice, so PyAudio is not required for the main demo. To use any
OpenAI-compatible LLM endpoint, configure:

```powershell
$env:UVI_LLM_BASE_URL="https://api.openai.com/v1"
$env:UVI_LLM_MODEL="gpt-4o-mini"
$env:UVI_DRIVER_NAME="Chandana"
$env:UVI_SPEECH_LANGUAGE="en-IN"
```

The microphone path uses online Google speech recognition. Voice output uses
the local system TTS engine through pyttsx3.

For the most realistic and soothing cockpit motion, place a calm forward-driving
video loop at:

```text
uvi_demo/assets/drive_loop.mp4
```

The cockpit will use that video as the windshield exterior and paint the UVI
cockpit, HUD, weather, and companion overlays on top. If the file is missing,
the app falls back to the lightweight synthetic exterior.
