The optimal text-to-speech engine for Raspberry Pi depends on your performance requirements:

| TTS Engine | Voice Quality | Latency / CPU Usage | Resource Footprint | Best Use Case |
| --- | --- | --- | --- | --- |
| **Piper TTS** *(Top Pick)* | High (Neural VITS) | Real-time on Pi 4/5 (~5-10% CPU) | Low (~50-100 MB RAM per voice) | Smart assistants, UI feedback, local projects |
| **Kokoro-82M** | Superior / Natural | Moderate (~1.5–2x speed on Pi 5) | Medium (~300 MB RAM) | Reading long texts, natural speech synthesis |
| **eSpeak NG** | Low / Robotic | Instant (<1% CPU) | Minimal (~5 MB RAM) | Headless debugging, status alerts, legacy systems |

---

### Why **Piper TTS** is the Preferred Choice

**Piper** is explicitly optimized for ARM single-board computers. It runs VITS neural models converted to ONNX, delivering clear, natural speech without relying on a GPU or active internet connection.

* **Extremely fast:** Synthesizes audio faster than real-time speed on Raspberry Pi 4 and 5.
* **Low memory usage:** Lightweight executable with voice models ranging between 30MB (medium quality) and 150MB (high quality).
* **Multi-language support:** Offers hundreds of pre-trained voices across 30+ languages (including Italian, English, French, German).

---

### Quick Implementation Guide (Piper + Python)

**1. System Installation**
Install `piper-tts` via `pip` or download the standalone ARM64 binary:

```bash
pip install piper-tts

```

**2. Download a Voice Model**
Fetch an ONNX model file and its corresponding `.json` config file (e.g., Italian medium voice):

```bash
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx.json

```

**3. Python Integration**
Stream audio output directly using a `subprocess` pipe:

```python
import subprocess

def speak(text, model_path="it_IT-paola-medium.onnx"):
    # Pipe synthesized audio directly to aplay for zero-latency playback
    piper_cmd = ["piper", "--model", model_path, "--output-raw"]
    aplay_cmd = ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw"]

    piper_proc = subprocess.Popen(piper_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    aplay_proc = subprocess.Popen(aplay_cmd, stdin=piper_proc.stdout)
    
    piper_proc.stdin.write(text.encode('utf-8'))
    piper_proc.stdin.close()
    aplay_proc.wait()

speak("Sistema pronto. Funzionamento corretto.")

```