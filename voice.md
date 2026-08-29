

---

# Voice Assistants Integration Overview

This document outlines the three available mechanisms for controlling the **DigitalFrame** application via voice: **Local Smart Home Device Emulation (Fauxmo)**, **Custom Voice Command Integration (SpeechToText Skill)**, and **Local Offline Speech Recognition (Vosk + UDP Nodes)**.

---

## 1. Local Smart Home Device Emulation via Fauxmo

The **Fauxmo** integration emulates standard Belkin WeMo smart plugs over UPnP/SSDP on your local network. This enables basic **ON / OFF** voice controls (e.g., *"Alexa, turn on Frame"*) without requiring an external cloud service or custom Alexa skill.

### Key Characteristics

* **Network Protocol:** UPnP/SSDP multicast discovery and local HTTP SOAP requests.


* **Execution Latency:** Near-instantaneous execution over the local area network (LAN).


* **Interaction Style:** Native smart home controls (`turn on`, `turn off`).



### Configuration (`fauxmo.json`)

Devices are mapped to specific virtual HTTP endpoints via the `ThreadPlugin`. Keys assigned to `on_cmd` and `off_cmd` are dispatched directly to the application's key event handler.

```json
{
  "FAUXMO": {
    "ip_address": "auto"
  },
  "PLUGINS": {
    "ThreadPlugin": {
      "DEVICES": [
        {
          "name": "Frame",
          "port": 49152,
          "on_cmd": "KEY_F8",
          "off_cmd": "KEY_F7",
          "use_fake_state": true,
          "initial_state": "on"
        }
      ]
    }
  }
}

```

---

## 2. Speech-to-Text Skill Integration (`SpeechToTextIntent`)

The **SpeechToText** skill integration utilizes a Flask web service and the Alexa Skills Kit (ASK) SDK to capture arbitrary spoken text and translate it into dynamic application commands.

### Key Characteristics

* **Network Protocol:** HTTP POST requests dispatched to the localized `/alexa` endpoint.


* **Execution Latency:** Requires round-trip processing through Amazon's Alexa Voice Service (AVS) cloud.


* **Interaction Style:** Natural voice commands (e.g., *"Alexa, tell Digital Frame to pause"*).



### Python Backend Service (`AlexaSpeechBackend`)

The Python server exposes an endpoint to parse incoming Alexa intents and route captured slot values back into the application runtime:

```python
class SpeechToTextIntentHandler(AbstractRequestHandler):
    def handle(self, handler_input: HandlerInput):
        locale = handler_input.request_envelope.request.locale
        slots = handler_input.request_envelope.request.intent.slots
        s2t = slots["SpeechToTextSlot"].value if slots and "SpeechToTextSlot" in slots else ""

        # Send captured speech string to callback logic
        if self.speech2text_callback:
            speech_text = self.speech2text_callback(s2t, locale)

        return handler_input.response_builder.speak(speech_text).response

```

---

## 3. Local Offline Speech Recognition (Vosk + ESP32-S3 / UDP Node)

The **Vosk UDP** integration turns an ESP32-S3 board (such as the Waveshare ESP32-S3-AUDIO Board) or any microcontroller equipped with an I2S microphone into a zero-cloud voice satellite node. The ESP32 streams raw PCM audio over UDP directly to a local Python socket server running the Kaldi-based [**Vosk STT**](https://alphacephei.com/vosk/) engine.

### Key Characteristics

* **Network Protocol:** Direct UDP audio datagram stream (PCM 16kHz, 16-bit Mono) from hardware to host; UDP status feedback loop sent back to the microcontroller.


* **Execution Latency:** Very low (runs locally on Pi/PC CPU without cloud roundtrips).
* **Interaction Style:** Direct spoken commands into local hardware (e.g., *"Diagnostica"*, *"Prossima foto"*, *"Regolazione luce"*).
* **Privacy & Offline Operation:** Works 100% offline without any internet connection or cloud dependency.

### Python Backend Service (`VoskSpeechBackend`)



The Python server runs a background thread that listens on a UDP port, passes incoming PCM chunks into Vosk's `KaldiRecognizer`, and fires the application callback upon utterance completion:

```python
# Create UDP listener with optional vocabulary constraint
self.vosk_server = VoskSpeechBackend(
    udp_ip="0.0.0.0",
    udp_port=5005,
    esp32_ip="192.168.10.45",
    esp32_port=5005,
    model_path="models/vosk-model-small-it-0.22",
    vocabulary=self.extract_menu_vocabulary(),
    on_speech_callback=self.on_speech_received
)
self.vosk_server.start(in_thread=True)

```

### Dynamic Grammar / Vocabulary Constraining

To maximize speech recognition accuracy on low-power devices, the system can extract current menu strings and pass them as a JSON vocabulary array into Vosk:

```python
# Passing menu vocabulary locks Vosk to expect only valid system commands
clean_vocab = ["diagnostica", "pausa", "prossima", "luce ambiente", "[unk]"]
self.recognizer = KaldiRecognizer(self.model, self.sample_rate, json.dumps(clean_vocab))

```

---

## Command Dispatching Logic

When a voice phrase is received by `on_speech_received(text, locale)` from either Alexa STT or Vosk UDP:

1. **Pre-calculated Fuzzy Menu Matching:** The handler checks incoming text against pre-calculated menu targets using `rapidfuzz.process.extractOne()` with `fuzz.WRatio`. If the similarity score exceeds `voice.threshold`, it executes the assigned function (`option["f"]`) or triggers a keypress (`option["k"]`).


2. **Action Modifier Prefixes (`wta`):** Handles prefix actions (e.g., `"incrementa"`, `"decrementa"`) to adjust spinbox parameters (`option["fr"]`, `option["fl"]`).
3. **Fallback Actions:** Custom keyword fallbacks (e.g., `"pausa"`, `"avanti"`, `"indietro"`) map directly to core display functions.

---

## Comparison Matrix

| Feature | Fauxmo Emulator | SpeechToText Skill | Vosk + ESP32-S3 Node |
| --- | --- | --- | --- |
| **Primary Use Case** | Fast ON/OFF state toggles | Cloud voice navigation via Alexa | 100% Local / Offline hardware voice control |
| **Setup Complexity** | Low (Local JSON file) | Medium (Alexa Developer Console) | Medium (Vosk model + ESP32 UDP firmware) |
| **Cloud Dependency** | None (Local LAN) | High (Requires Amazon AVS cloud) | **None** (100% Local processing) |
| **Voice Command Syntax** | *"Alexa, turn [On/Off] [Device]"*<br> | *"Alexa, ask Frame to [Command]"*<br> | Direct speech: *"Diagnostica"*, *"Pausa"* |
| **Hardware Required** | Existing Echo device | Existing Echo device | Waveshare ESP32-S3-AUDIO or any UDP audio node |
| **Latency** | Near-instant (~50ms) | High (~1000–2000ms) | Low (~200–400ms) |

---

## Enablement in `config.json`

All three services can be selectively enabled or configured inside your main `config.json`:

```json
"voice": {
    "threshold": 80,
    "fauxmo": {
        "enabled": true
    },
    "alexa": {
        "enabled": false,
        "host": "0.0.0.0",
        "port": 5000,
        "verify_signature": false
    },
    "esp32s3": {
        "enabled": true,
        "host": "0.0.0.0",
        "port": 5005,
        "esp32_ip": "192.168.1.2",
        "esp32_port": 5005,
        "model_path": "vosk-model-small-it-0.22",
        "vocabulary": true
    }
}

```