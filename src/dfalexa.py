import asyncio
import threading, logging
from config import Config
from alexa.fauxmo.fauxmo import main as fauxmo_main
from alexa.skill.speech2text import AlexaSpeechBackend
import utils.ddcutil as ddcutil

logger = logging.getLogger(__name__)

class Alexa():
    def __init__(self, digitalframe, config_path):
        logger.setLevel(Config.get("window.log_level", logging.INFO))
        self.df = digitalframe
        self.config_path = config_path
        self.verbosity = Config.get("window.log_level", logging.INFO)

        # Fauxmo threading handles
        self.loop = None
        self.fauxmo_thread = None

        # Alexa Speech Server instance
        self.speech_server = None

        # Check enabled flags in config
        self.fauxmo_enabled = Config.get('alexa.fauxmo.enabled', False)
        self.speech2text_enabled = Config.get('alexa.speech2text.enabled', False)

    def on_speech_received(self, text: str, locale: str):
        """Callback triggered when a voice command is captured by AlexaSpeechBackend."""
        logger.info(f"Executing Alexa Speech command: '{text}' {locale=}")
        speech_text = "done"
        command = text.lower().strip()
        menu_obj = self.df.devices.menu  # Access the OnScreenMenu instance attached to digitalframe

        # 1. First, search through all loaded menu items for matching actions
        for menu_name, options in menu_obj.menus.items():
            # Skip selection tracker attributes like 'menu_sel'
            if not isinstance(options, list):
                continue

            for option in options:
                # Extract text target from either 't' (plain text) or evaluate dynamic text ('g' / 'e')
                item_text = ""
                if "t" in option:
                    item_text = option["t"]
                elif "g" in option:
                    try:
                        # Evaluates dynamically like: f'Toogle Ambient Light ({self.on_off(...)})'
                        item_text = eval(option["g"], {"self": menu_obj, "Config": Config})
                    except Exception:
                        item_text = option["g"]
                elif "e" in option:
                    try:
                        item_text = eval(option["e"], {"self": menu_obj, "Config": Config})
                    except Exception:
                        item_text = option["e"]

                #Toogle pronunciation is impossible for me to get Alexa to understand.
                item_text_clean = item_text.lower().strip().replace("toogle", "")

                # Check if voice command matches menu label or key words inside it
                if item_text_clean and (item_text_clean in command or command in item_text_clean):
                    logger.info(f"Matched voice command '{text}' with menu item: {option}")

                    # Execute python function if provided in option
                    if "f" in option:
                        try:
                            exec(option["f"], {"self": menu_obj, "Config": Config, "ddcutil": ddcutil})
                            return speech_text
                        except Exception as e:
                            speech_text = f"Error executing menu function '{option['f']}': {e}"
                            logger.error(speech_text)
                            return speech_text

                    # Trigger key press if defined in option
                    elif "k" in option and option["k"]:
                        self.df.devices.send_keys(option["k"])
                        return speech_text

        # 2. Fallback direct control handling for common commands
        if command in ["pause", "pausa"]:
            self.df.set_paused(True)
        elif command in ["resume", "continua"]:
            self.df.set_paused(False)
        elif command in ["next", "avanti", "prossima"]:
            self.df.devices.send_keys("KEY_F5")  # Trigger Next using menu key map
        elif command in ["previous", "indietro", "precedente"]:
            self.df.devices.send_keys("KEY_F4")  # Trigger Previous using menu key map
        elif command in ["sleep", "sospendi"]:
            self.df.devices.send_keys("KEY_F7")  # Trigger Sleep using menu key map
        elif command in ["wakeup", "attiva"]:
            self.df.devices.send_keys("KEY_F8")  # Trigger Wakeup using menu key map
        else:
            return "unknown command"

        return speech_text

    def run(self):
        # 1. Start Fauxmo if enabled
        if self.fauxmo_enabled:
            self.loop = asyncio.new_event_loop()
            self.fauxmo_thread = threading.Thread(
                target=fauxmo_main,
                args=(self.df, self.loop, self.config_path, self.verbosity),
                daemon=True
            )
            self.fauxmo_thread.start()
            logger.info("Fauxmo server thread started.")

        # 2. Start AlexaSpeechServer in a background thread if enabled
        if self.speech2text_enabled:
            host = Config.get('alexa.speech2text.host', '0.0.0.0')
            port = Config.get('alexa.speech2text.port', 5000)
            verify_sig = Config.get('alexa.speech2text.verify_signature', False)

            self.speech_server = AlexaSpeechBackend(host=host, port=port, verify_signature=verify_sig, on_speech_callback=self.on_speech_received)

            # Connect callback handler to digitalframe
            self.speech_server.on_speech_received = self.on_speech_received

            # Start Flask/Werkzeug server in background thread
            self.speech_server.start(in_thread=True)
            logger.info(f"Alexa SpeechToText backend server running on port {port}")

    def stop(self):
        # 1. Stop Speech Server gracefully
        if self.speech_server:
            self.speech_server.stop()

        # 2. Stop Fauxmo event loop safely
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            if self.fauxmo_thread:
                self.fauxmo_thread.join()
            self.loop.close()
            logger.info("Fauxmo event loop closed.")
