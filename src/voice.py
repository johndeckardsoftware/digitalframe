import os
import re
import asyncio
import logging
import threading

from rapidfuzz import fuzz, process
from num2words2 import num2words
from text_to_num import text2num 
from assistants.fauxmo.fauxmo import main as fauxmo_main
from assistants.alexa.speech2text import AlexaSpeechBackend
from assistants.esp32s3.myalexa import VoskSpeechBackend, PiperSpeechEngine
from config import Config
import utils.ddcutil as ddcutil

logger = logging.getLogger(__name__)

class VoiceAssistant:
    def __init__(self, digitalframe, config_path):
        logger.setLevel(Config.get("window.log_level", logging.INFO))
        logger.setLevel(logging.DEBUG)
        self.df = digitalframe
        self.config_path = config_path
        self.verbosity = Config.get("window.log_level", logging.INFO)
        self.lang = Config.get("voice.lang", "en")

        # menu class ref
        self.menu = digitalframe.devices.menu
        self.menu.va = digitalframe.voice_assistant

        # Cache structure for rapid string matching
        self._cached_menu_texts = []
        self._cached_menu_options = []

        # Fauxmo Thread handles
        self.fauxmo_enabled = Config.get("voice.fauxmo.enabled", False)
        self.fauxmo_loop = None
        self.fauxmo_thread = None

        # Alexa Speech to text Backend Thread
        self.alexa_enabled = Config.get("voice.alexa.enabled", False)
        self.alexa_stt_backend = None

        # MyAlexa ESP32S3 Speech to Text Backend Thread
        self.esp32s3_enabled = Config.get("voice.esp32s3.enabled", False)
        self.vosk_server = None
        self.vosk_vocabulary = None

        # MyAlexa Piper TTS Engine Thread
        self.piper_enabled = Config.get("voice.piper.enabled", False)
        self.tts_engine = None

    def speak(self, text: str):
        """Forwards speech requests to the Piper worker thread queue."""
        if self.tts_engine and self.piper_enabled:
            self.tts_engine.speak(text)

    def eval_menu_text(self, option):
        item_text = ""
        if "t" in option:
            item_text = option["t"]
        elif "g" in option:
            try:
                item_text = eval(option["g"], {"self": self.menu, "Config": Config, "ddcutil": ddcutil})
            except Exception as e:
                logger.error(e)
                item_text = option["g"]
        elif "e" in option:
            try:
                item_text = eval(option["e"], {"self": self.menu, "Config": Config, "ddcutil": ddcutil})
            except Exception as e:
                logger.error(e)
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
            if (
                not isinstance(options, list)
                or menu_name == "action_modifier_word"
            ):
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

            # Also include action words from 'action_modifier_word' mapping if present
            amw_list = self.menu.menus.get("action_modifier_word", [])
            for action in amw_list:
                if action and isinstance(action, list):
                    words.append(action[0].lower().strip())

            # Also include numbers from 0 to 255
            for n in range(0, 255):
                words.append(num2words(n, lang=self.lang))

            # Dynamically pull letter pronunciations/phonetics from the active OSK layout
            if hasattr(self.menu, "osk") and hasattr(self.menu.osk, "phonetic_map"):
                phonetic_keys = self.menu.osk.phonetic_map.keys()
                for name in phonetic_keys:
                    words.append(name)
                    words.extend(name.split())  # Handles multi-word names like "doppia vu" or "question mark"
        except Exception as e:
            logger.warning(f"Could not extract menu words: {e}")

        return list(set(words))

    def reload_vosk_vocabulary(self, vocabulary):
        if self.vosk_server and self.esp32s3_enabled:
            self.vosk_server.update_vocabulary(vocabulary)

    def on_speech_received(self, text: str, locale: str):
        """Callback triggered when a voice command is captured by AlexaSpeechBackend or VoskSpeechBackend."""
        logger.debug(f"Executing Speech command: '{text}'")

        # Build cache on first run if not already present
        if not self._cached_menu_texts:
            self.refresh_menu_cache()

        command = text.lower().strip()

        # Check voice action modifier words
        voice_action_list = self.menu.menus.get("voice_action", [])
        for voice_action in voice_action_list:
            words = voice_action['t']
            if command.startswith(words):
                if voice_action['s']:
                    command = command.replace(words, "", 1).strip()
                ret = eval(voice_action['f'], {"voice": self, "self": self.menu, "Config": Config, "ddcutil": ddcutil, "command": command})
                logger.debug(f"{voice_action=} {command=}")
                if voice_action['r']:
                    return "ok"
                break

        # Check action modifier word  (f, fl, fr, fv)
        action = "f"
        word_action_list = self.menu.menus.get("action_modifier_word", [])
        for word, _action_ in word_action_list:
            if command.startswith(word):
                command = command.replace(word, "", 1).strip()
                action = _action_
                break
        logger.debug(f"{command=} {action=} {self.menu.in_osk=}")

        response = "ko"
        speech = ""

        if self.menu.in_osk: # Check if the OnScreenKeyboard is actively receiving input
            cleaned_text = text.strip()
            # Pass the captured speech string directly to OSK buffer
            self.menu.osk.set_typed_char_from_voice(cleaned_text)
            return "ok"

        # Execute single RapidFuzz search across all pre-calculated commands at once
        match = process.extractOne(command, self._cached_menu_texts, scorer=fuzz.WRatio)
        if match and match[1] >= Config.get("voice.threshold", 90):
            matched_text, score, index = match
            option = self._cached_menu_options[index]
            logger.info(f"Matched voice command '{matched_text}' ({score}) with menu item: {option}")

            if 'vk' in option:
                self.menu.osk_show(option)
                response = "ok"

            elif 'k' in option:       # Execute key press
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

                    ret = eval(option[action], {"self": self.menu, "Config": Config, "ddcutil": ddcutil, "command": command})
                    logger.debug(f"eval ret: {ret}")
                    response = "done" if ret and ret == "stop" else "ok"

                    self.menu.in_action = False

                except Exception as e:
                    speech = f"Error executing menu function '{option[action]}': {e}"
                    logger.error(speech)
                    response = "err"

            if self.piper_enabled and response == "ok":
                speech = self.eval_menu_text(option)
                logger.debug(f"{speech=}")
                if speech:
                    self.speak(speech)

        return response

    def run(self):
        # 1. Start Fauxmo if enabled
        if self.fauxmo_enabled:
            self.fauxmo_loop = asyncio.new_event_loop()
            self.fauxmo_thread = threading.Thread(
                target=fauxmo_main,
                args=(
                    self.df,
                    self.fauxmo_loop,
                    self.config_path,
                    self.verbosity,
                ),
                daemon=True,
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
                self.vosk_vocabulary = self.extract_menu_vocabulary()
            else:
                self.vosk_vocabulary = None

            self.vosk_server = VoskSpeechBackend(
                udp_ip=udp_ip,
                udp_port=udp_port,
                esp32_ip=esp32_ip,
                esp32_port=esp32_port,
                model_path=model_path,
                vocabulary=self.vosk_vocabulary,
                on_speech_callback=self.on_speech_received
            )
            self.vosk_server.start(in_thread=True)
            logger.info("Vosk local STT engine running.")

        # 4. Start Piper TTS engine thread
        if self.piper_enabled:
            self.tts_engine = PiperSpeechEngine()
            self.tts_engine.start()

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

        # 3. Stop MyAlexa server
        if self.vosk_server:
            self.vosk_server.stop()

        # 4. Stop Piper speech engine
        if self.tts_engine:
            self.tts_engine.stop()
            self.tts_engine.join(timeout=10.0)
            logger.info("Piper local TTS engine stopped.")


