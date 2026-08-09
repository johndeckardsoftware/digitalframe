
---

# Alexa Integration Overview

This document outlines the two available mechanisms for controlling the **DigitalFrame** application via Amazon Echo / Alexa devices: **Local Smart Home Device Emulation (Fauxmo)** and **Custom Voice Command Integration (SpeechToText Skill)**.

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

*Source: `fauxmo.json*`

---

## 2. Speech-to-Text Skill Integration (`SpeechToTextIntent`)

The **SpeechToText** skill integration utilizes a Flask web service and the Alexa Skills Kit (ASK) SDK to capture arbitrary spoken text and translate it into dynamic application commands.

### Key Characteristics

* **Network Protocol:** HTTP POST requests dispatched to the localized `/alexa` endpoint.


* **Execution Latency:** Requires round-trip processing through Amazon's Alexa Voice Service (AVS) cloud.


* **Interaction Style:** Natural voice commands (e.g., *"Alexa, tell Digital Frame to pause"* or *"Alexa, ask Digital Frame to toggle Weather"*).

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

*Source: `speech2text.py*`

### Command Dispatching Logic

When a voice phrase is received by `on_speech_received(text, locale)`:

1. **Dynamic On-Screen Menu Match:** The handler iterates through registered menu items (`option["t"]`, `option["g"]`, or `option["e"]`). If the phrase matches a menu entry, it executes the assigned Python function (`option["f"]`) or simulates the required keypress (`option["k"]`).


2. **Fallback Navigation Commands:** Common keywords are translated directly into key commands or system actions:


* `"pause"` / `"pausa"` → Sets slideshow state to paused.


* `"next"` / `"avanti"` → Triggers `KEY_F5`.


* `"previous"` / `"indietro"` → Triggers `KEY_F4`.


* `"sleep"` / `"sospendi"` → Triggers `KEY_F7`.


* `"wakeup"` / `"attiva"` → Triggers `KEY_F8`.





---

## Comparison Matrix

| Feature | Fauxmo Emulator | SpeechToText Skill |
| --- | --- | --- |
| **Primary Use Case** | Fast ON/OFF state toggles | Menu navigation and custom commands |
| **Setup Complexity** | Low (Local JSON file)| Medium (Alexa Developer Console + HTTP Endpoint) |
| **Cloud Dependency** | None (Local LAN) | High (Requires Amazon AVS cloud) |
| **Voice Command Syntax** | *"Alexa, turn [On/Off] [Device Name]"* | *"Alexa, open [Skill Name]"* or *"Alexa, ask [Skill] [Text]"* |
| **Command Flexibility** | Binary (On/Off actions only) | Dynamic (Transcribes speech to trigger menu actions) |

---

## Enablement in `config.json`

Both services can be selectively enabled or disabled inside your main `config.json`:

```json
"alexa": {
    "fauxmo": {
        "enabled": true
    },
    "speech2text": {
        "enabled": true,
        "host": "0.0.0.0",
        "port": 5000,
        "verify_signature": false
    }
}

```

*Source: `config.json*`