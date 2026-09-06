import asyncio
import os, threading, logging
import subprocess, re
from config import Config
from assistants.fauxmo.fauxmo import main as fauxmo_main
from assistants.alexa.speech2text import AlexaSpeechBackend
from assistants.esp32s3.myalexa import VoskSpeechBackend
import utils.ddcutil as ddcutil
from rapidfuzz import process, fuzz
from text_to_num import text2num
from num2words2 import num2words

logger = logging.getLogger(__name__)

class VoiceAssistant():
    def __init__(self, digitalframe, config_path):
        logger.setLevel(Config.get("window.log_level", logging.INFO))
        #logger.setLevel(logging.DEBUG)
        self.df = digitalframe
        self.config_path = config_path
        self.verbosity = Config.get("window.log_level", logging.INFO)
        self.lang = Config.get("voice.lang", "en")

        # menu class ref
        self.menu = digitalframe.devices.menu

        # Cache structure for rapid string matching
        self._cached_menu_texts = []
        self._cached_menu_options = []

        # Fauxmo threading handles
        self.fauxmo_loop = None
        self.fauxmo_thread = None

        # Alexa Speech to text Backend Server instance
        self.alexa_stt_backend = None

        # ESP32S3 MyAlexa Speech to text Backend Server instance
        self.vosk_server = None

        # Feature flags
        self.fauxmo_enabled = Config.get('voice.fauxmo.enabled', False)
        self.alexa_enabled = Config.get('voice.alexa.enabled', False)
        self.esp32s3_enabled = Config.get('voice.esp32s3.enabled', False)
        self.piper_enabled = Config.get('voice.piper.enabled', False)

    def eval_menu_text(self, option):
        item_text = ""
        if "t" in option:
            item_text = option["t"]
        elif "g" in option:
            try:
                item_text = eval(option["g"], {"self": self.menu, "Config": Config, "ddcutil": ddcutil})
            except Exception:
                item_text = option["g"]
        elif "e" in option:
            try:
                item_text = eval(option["e"], {"self": self.menu, "Config": Config, "ddcutil": ddcutil})
            except Exception:
                item_text = option["e"]

        return item_text

    def refresh_menu_cache(self):
        """
        Pre-calculates and flattens all selectable menu texts into single indexed lists
        so fuzzy search can match across the whole menu corpus in a single operation.
        """
        texts = []
        options_ref = []

        for menu_name, options in self.menu.menus.items():
            if not isinstance(options, list) or menu_name == "pre_action_selection_word" or menu_name == "action_selection_word":
                continue

            for option in options:
                item_text = self.eval_menu_text(option)

                clean_text = item_text.lower().strip()
                if clean_text:
                    clean_text = re.sub(r"\s*\(.*?\)", "", clean_text)
                    clean_text = re.sub(r"\s*<.*?>", "", clean_text)
                    clean_text = re.sub(r"\.[^.]+$", "", clean_text)
                    clean_text = re.sub(r"[\"']", "", clean_text)

                    texts.append(clean_text)
                    options_ref.append(option)

        self._cached_menu_texts = texts
        self._cached_menu_options = options_ref
        logger.info(f"Pre-calculated {len(self._cached_menu_texts)} voice menu command targets.")

    def extract_menu_vocabulary(self) -> list:
        """Extracts text tokens dynamically from cached digitalframe menu strings."""
        if not self._cached_menu_texts:
            self.refresh_menu_cache()

        words = []
        try:
            for text in self._cached_menu_texts:
                clean_text = text.strip()
                if clean_text:
                    # Add full phrase as well as individual token words
                    words.append(clean_text)
                    words.extend(clean_text.split())

            # Also include action words from 'pre_action_selection_word' and 'action_selection_word' mapping if present
            asw_list = self.menu.menus.get("pre_action_selection_word", [])
            for action in asw_list:
                if action and isinstance(action, list):
                    words.append(action[0].lower().strip())

            asw_list = self.menu.menus.get("action_selection_word", [])
            for action in asw_list:
                if action and isinstance(action, list):
                    words.append(action[0].lower().strip())

            # Also include numbers from 0 to 255
            for n in range(0, 255):
                words.append(num2words(n, lang=self.lang))

        except Exception as e:
            logger.warning(f"Could not extract menu words: {e}")

        return list(set(words))

    def on_speech_received(self, text: str, locale: str):
        """Callback triggered when a voice command is captured by AlexaSpeechBackend or VoskSpeechBackend."""
        logger.debug(f"Executing Speech command: '{text}'")

        command = text.lower().strip()

        # Build cache on first run if not already present
        if not self._cached_menu_texts:
            self.refresh_menu_cache()

        # Manage pre action selection word  (fs)
        pre_action = ""
        pre_word_action_list = self.menu.menus.get("pre_action_selection_word", [])
        for word, _pre_action_ in pre_word_action_list:
            if command.startswith(word):
                command = command.replace(word, "", 1).strip()
                pre_action = _pre_action_
                break
        logger.debug(f"{pre_action=} {command=}")

        # Manage action selection word  (f, fl, fr)
        action = "f"
        word_action_list = self.menu.menus.get("action_selection_word", [])
        for word, _action_ in word_action_list:
            if command.startswith(word):
                command = command.replace(word, "", 1).strip()
                action = _action_
                break
        logger.debug(f"{action=} {command=}")

        response = "ko"
        speech = ""

        if pre_action == "fn" or pre_action == "fm":  # set self.number. use "for" pre control word to use that with action 'fv'
            try:
                self.menu.number = text2num(command, lang=self.lang)
                if pre_action == "fm": self.menu.number = self.menu.number * -1
                logger.debug(f"{pre_action=} {self.menu.number=}")
                response = "ok"
            except Exception as e:
                logger.error(f"{e}")

        # Execute single RapidFuzz search across all pre-calculated commands at once
        match = process.extractOne(command, self._cached_menu_texts, scorer=fuzz.WRatio)
        if match and match[1] >= Config.get("voice.threshold", 90):
            matched_text, score, index = match
            option = self._cached_menu_options[index]
            logger.info(f"Matched voice command '{matched_text}' ({score}) with menu item: {option}")

            if 'k' in option:       # Execute key press
                self.menu.in_action = True
                self.df.devices.send_keys(option['k'])
                self.menu.in_action = False
                response = "ok"

            elif 'm' in option:     # Select current menu
                self.menu.set_menu(option['m'])
                response = "ok"

            elif action in option:    # Execute python function string
                try:
                    self.menu.in_action = True

                    if pre_action == "fs":  # simulate item manual selection
                        ret = self.menu.select(command)

                    ret = eval(option[action], {"self": self.menu, "Config": Config, "ddcutil": ddcutil})
                    logger.debug(f"eval ret: {ret}")
                    response = "done" if ret and ret == "stop" else "ok"

                    self.menu.in_action = False

                except Exception as e:
                    speech = f"Error executing menu function '{option[action]}': {e}"
                    logger.error(speech)
                    response = "err"

            if self.piper_enabled:
                if response == "ok":
                    speech = self.eval_menu_text(option)
                    logger.debug(f"{speech=}")
                    if speech:
                        self.speak(speech)

        return response

    def speak(self, text):
        # nice but too slow
        path = Config.get('voice.piper.path', 'piper')
        model_path = os.path.join(Config.RESOURCES_PIPER, Config.get('voice.piper.model_path', 'it_IT-paola-medium.onnx'))
        logger.debug(f"{path=} {model_path=}")
        # Pipe synthesized audio directly to aplay for zero-latency playback
        piper_cmd = [path, "--model", model_path, "--output-raw"]
        aplay_cmd = ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw"]

        piper_proc = subprocess.Popen(piper_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        aplay_proc = subprocess.Popen(aplay_cmd, stdin=piper_proc.stdout)

        piper_proc.stdin.write(text.encode('utf-8'))
        piper_proc.stdin.close()
        aplay_proc.wait()

    def run(self):
        # 1. Start Fauxmo if enabled
        if self.fauxmo_enabled:
            self.fauxmo_loop = asyncio.new_event_loop()
            self.fauxmo_thread = threading.Thread(
                target=fauxmo_main,
                args=(self.df, self.fauxmo_loop, self.config_path, self.verbosity),
                daemon=True
            )
            self.fauxmo_thread.start()
            logger.info("Fauxmo server thread started.")

        # 2. Start AlexaSpeechBackend in a background thread if enabled
        if self.alexa_enabled:
            host = Config.get('voice.alexa.host', '0.0.0.0')
            port = Config.get('voice.alexa.port', 5000)
            verify_sig = Config.get('voice.alexa.verify_signature', False)

            self.alexa_stt_backend = AlexaSpeechBackend(host=host, port=port, verify_signature=verify_sig, on_speech_callback=self.on_speech_received)

            # Connect callback handler to digitalframe
            self.alexa_stt_backend.on_speech_received = self.on_speech_received

            # Start Flask/Werkzeug server in background thread
            self.alexa_stt_backend.start(in_thread=True)
            logger.info(f"Alexa SpeechToText backend server running on port {port}")

        # 3. Start Vosk Local UDP Server thread for ESP32S3 MyAlexa if enabled
        if self.esp32s3_enabled:
            model_path = os.path.join(Config.RESOURCES_VOSK, Config.get('voice.esp32s3.model_path', 'vosk-model-small-en-us-0.15'))
            if not os.path.exists(model_path):
                logger.error(f"VOSK model path not found: {model_path}")
                return

            udp_ip = Config.get('voice.esp32s3.host', '0.0.0.0')
            udp_port = Config.get('voice.esp32s3.port', 5005)
            esp32_ip = Config.get('voice.esp32s3.esp32_ip', '192.168.1.2')
            esp32_port = Config.get('voice.esp32s3.esp32_port', 5005)
            vocabulary = Config.get('voice.esp32s3.vocabulary', True)

            if vocabulary:
                menu_vocab = self.extract_menu_vocabulary()
            else:
                menu_vocab = None

            self.vosk_server = VoskSpeechBackend(
                udp_ip=udp_ip,
                udp_port=udp_port,
                esp32_ip=esp32_ip,
                esp32_port=esp32_port,
                model_path=model_path,
                vocabulary=menu_vocab,
                on_speech_callback=self.on_speech_received
            )
            self.vosk_server.start(in_thread=True)
            logger.info("VOSK local STT engine running.")

    def stop(self):
        # 1. Stop Alexa Backend server
        if self.alexa_stt_backend:
            self.alexa_stt_backend.stop()

        # 2. Stop Fauxmo event loop safely
        if self.fauxmo_loop and self.fauxmo_loop.is_running():
            self.fauxmo_loop.call_soon_threadsafe(self.fauxmo_loop.stop)
            if self.fauxmo_thread:
                self.fauxmo_thread.join()
            self.fauxmo_loop.close()
            logger.info("Fauxmo event loop closed.")

        # 2. Stop MyAlexa server
        if self.vosk_server:
            self.vosk_server.stop()
