import asyncio
import os, threading, logging
from config import Config
from assistants.fauxmo.fauxmo import main as fauxmo_main
from assistants.alexa.speech2text import AlexaSpeechBackend
from assistants.esp32s3.myalexa import VoskSpeechBackend
import utils.ddcutil as ddcutil
from rapidfuzz import process, fuzz

logger = logging.getLogger(__name__)

class VoiceAssistant():
    def __init__(self, digitalframe, config_path):
        logger.setLevel(Config.get("window.log_level", logging.INFO))
        self.df = digitalframe
        self.config_path = config_path
        self.verbosity = Config.get("window.log_level", logging.INFO)

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

    def refresh_menu_cache(self):
        """
        Pre-calculates and flattens all selectable menu texts into single indexed lists
        so fuzzy search can match across the whole menu corpus in a single operation.
        """
        menu_obj = self.df.devices.menu
        texts = []
        options_ref = []

        for menu_name, options in menu_obj.menus.items():
            if not isinstance(options, list) or menu_name == "wta":
                continue

            for option in options:
                item_text = ""
                if "t" in option:
                    item_text = option["t"]
                elif "g" in option:
                    try:
                        item_text = eval(option["g"], {"self": menu_obj, "Config": Config})
                    except Exception:
                        item_text = option["g"]
                elif "e" in option:
                    try:
                        item_text = eval(option["e"], {"self": menu_obj, "Config": Config})
                    except Exception:
                        item_text = option["e"]

                clean_text = item_text.lower().strip()
                if clean_text:
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
                # Remove non-word formatting artifacts
                clean_text = text
                for char in ["<", ">", "(", ")", "\"", "'"]:
                    clean_text = clean_text.replace(char, "")

                clean_text = clean_text.strip()
                if clean_text:
                    # Add full phrase as well as individual token words
                    words.append(clean_text)
                    words.extend(clean_text.split())

            # Also include action words from wta mapping if present
            wta_list = self.df.devices.menu.menus.get("wta", [])
            for action in wta_list:
                if action and isinstance(action, list):
                    words.append(action[0].lower().strip())

        except Exception as e:
            logger.warning(f"Could not extract dynamic menu words: {e}")

        return list(set(words))

    def on_speech_received(self, text: str, locale: str):
        """Callback triggered when a voice command is captured by AlexaSpeechBackend or VoskSpeechBackend."""
        logger.info(f"Executing Speech command: '{text}'")

        command = text.lower().strip()
        response_text = "done"

        menu_obj = self.df.devices.menu

        # Build cache on first run if not already present
        if not self._cached_menu_texts:
            self.refresh_menu_cache()

        # Manage word-to-menu action (f, fl, fr)
        action = "f"
        word_action_list = menu_obj.menus.get("wta", [])
        for word_action in word_action_list:
            if command.startswith(word_action[0]):
                command = command.replace(word_action[0], "", 1).strip()
                action = word_action[1]
        logger.debug(f"{action=}")

        # Execute single RapidFuzz search across all pre-calculated commands at once
        match = process.extractOne(command, self._cached_menu_texts, scorer=fuzz.WRatio)

        if match and match[1] >= Config.get("voice.threshold", 90):
            matched_text, score, index = match
            option = self._cached_menu_options[index]

            logger.info(f"Matched voice command '{matched_text}' ({score}) with menu item: {option}")

            # Execute key press if defined in option
            if "k" in option:
                self.df.devices.send_keys(option["k"])
                return response_text

            # Execute python function string if provided in option
            if action in option:
                try:
                    exec(option[action], {"self": menu_obj, "Config": Config, "ddcutil": ddcutil})
                    return response_text
                except Exception as e:
                    response_text = f"Error executing menu function '{option[action]}': {e}"
                    logger.error(response_text)
                    return response_text

        return "unknown"

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
            esp32_ip = Config.get('voice.esp32s3.esp32_ip', '192.168.10.45')
            esp32_port = Config.get('voice.esp32s3.esp32_port', 5005)
            vocabulary = Config.get('voice.esp32s3.vocabulary', False)

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
