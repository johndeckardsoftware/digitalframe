import json
import socket
import logging
import threading
from typing import Optional
from vosk import Model, KaldiRecognizer

from config import Config
import utils.ddcutil as ddcutil

logger = logging.getLogger(__name__)

class VoskSpeechBackend:
    """UDP Audio Stream receiver that processes speech with Vosk local STT."""
    def __init__(
        self,
        udp_ip: str = "0.0.0.0",
        udp_port: int = 5005,
        esp32_ip: str = "192.168.1.2",
        esp32_port: int = 5005,
        model_path: str = "",
        sample_rate: int = 16000,
        vocabulary: Optional[list] = None,
        on_speech_callback = None
    ):
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        self.esp32_ip = esp32_ip
        self.esp32_port = esp32_port
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.on_speech_callback = on_speech_callback

        self.sock: Optional[socket.socket] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # 1. Initialize Vosk Model (https://alphacephei.com/vosk/models to download your language model)
        try:
            self.model = Model(self.model_path)
        except Exception as e:
            logger.error(f"Could not load Vosk model from '{self.model_path}': {e}")
            return

        # 2. Configure vocabulary grammar constraint if vocabulary list is supplied
        if vocabulary and len(vocabulary) > 0:
            # Format list to lower case and include [unk] to handle unknown utterances
            clean_vocab = list(set([str(w).lower().strip() for w in vocabulary if w]))
            if "[unk]" not in clean_vocab:
                clean_vocab.append("[unk]")

            vocab_json = json.dumps(clean_vocab)
            logger.info(f"Vosk constrained with {len(clean_vocab)} vocabulary tokens.")
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate, vocab_json)
        else:
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)

    def send_status_udp(self, status_msg: str):
        """Sends a response status string over UDP back to the ESP32."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(status_msg.encode('utf-8'), (self.esp32_ip, self.esp32_port))
            logger.debug(f"Sent UDP status '{status_msg}' -> {self.esp32_ip}:{self.esp32_port}")
        except Exception as e:
            logger.error(f"Failed sending UDP status to ESP32: {e}")
        finally:
            sock.close()

    def _listen_loop(self):
        """Background thread worker that reads incoming audio buffers from UDP socket."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.udp_ip, self.udp_port))
        # Non-blocking socket timeout allows checking self.running flag on shutdown
        self.sock.settimeout(1.0)

        logger.info(f"Vosk UDP STT Backend listening on {self.udp_ip}:{self.udp_port}")

        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                if data and self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()
                    if text and text != "[unk]":
                        logger.info(f"Vosk Final Recognition: '{text}'")

                        # Execute speech callback function
                        response = "stop"
                        if self.on_speech_callback:
                            response = self.on_speech_callback(text, "en-US")

                        # Notify ESP32 with the following codes:
                        #   "ok": command processed, wait for the next command or 'stop' command to close mic.
                        #   "ko": command not recognized, wait for the next command or 'stop' command to close mic.
                        #   "err": error during command execution. close mic.
                        #   "done": 'stop' command processed. close mic.
                        self.send_status_udp(response)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error in Vosk listener loop: {e}")

        if self.sock:
            self.sock.close()
            logger.info("Vosk UDP socket closed.")

    def start(self, in_thread: bool = True):
        """Starts the local UDP STT engine."""
        self.running = True
        if in_thread:
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
        else:
            self._listen_loop()

    def stop(self):
        """Stops the engine and closes background thread resources."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join()
        logger.info("Vosk Speech Backend stopped.")
