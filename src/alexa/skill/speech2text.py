import logging
import threading
from typing import Optional

from flask import Flask, request, Response
from werkzeug.serving import make_server

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_webservice_support.webservice_handler import WebserviceSkillHandler

logger = logging.getLogger(__name__)

# --- Alexa Intent Handlers ---
class LaunchRequestHandler(AbstractRequestHandler):
    """Handles skill launch (e.g., 'Alexa, open digital frame')."""
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput):
        speech_text = "Skill started. Tell me the text."
        return (
            handler_input.response_builder
            .speak("Ok. tell the command like in menu")
            .ask(speech_text)
            .response
        )

class SpeechToTextIntentHandler(AbstractRequestHandler):
    def __init__(self, on_speech_callback=None):
        self.speech2text_callback = on_speech_callback

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("SpeechToTextIntent")(handler_input)

    def handle(self, handler_input: HandlerInput):
        locale = handler_input.request_envelope.request.locale
        slots = handler_input.request_envelope.request.intent.slots
        s2t = slots["SpeechToTextSlot"].value if slots and "SpeechToTextSlot" in slots else ""

        logger.debug(f"SpeechToTextIntentHandler received: '{s2t}' {locale=}")

        # Forward speech text to custom application logic if registered
        speech_text = f"No callback for: {s2t}"
        if self.speech2text_callback:
            speech_text = self.speech2text_callback(s2t, locale)

        return handler_input.response_builder.speak(speech_text).response

class HelpIntentHandler(AbstractRequestHandler):
    """Handles 'help', 'what can I do', etc."""
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput):
        speech_text = "You can excute almost any menu entry, just tell: 'menu' followed by the menu text as you see it on the screen."
        reprompt_text = "Please say the menu entry you want to execute."

        return (
            handler_input.response_builder
            .speak(speech_text)
            .ask(reprompt_text)
            .response
        )

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handles automatic or manual session termination."""
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput):
        logger.info(f"Session closed: {handler_input.request_envelope.request.reason}")
        return handler_input.response_builder.response

class GlobalExceptionHandler(AbstractExceptionHandler):
    """Prevents server crashes by catching unhandled exceptions."""
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception):
        speech_text = f"Error processing request: {exception}"
        logger.error(speech_text)
        return (
            handler_input.response_builder
            .speak(speech_text)
            .response
        )

class AlexaSpeechBackend:
    def __init__(self, host: str = "0.0.0.0", port: int = 5000, verify_signature: bool = False, on_speech_callback=None):
        self.host = host
        self.port = port
        self.verify_signature = verify_signature
        self.on_speech_callback = on_speech_callback if on_speech_callback else self.on_speech_received
        self.app = Flask(__name__)
        self.server = None
        self.server_thread: Optional[threading.Thread] = None

        # Build Skill
        self.sb = SkillBuilder()
        self._register_handlers()

        self.skill_response_handler = WebserviceSkillHandler(
            skill=self.sb.create(),
            verify_signature=self.verify_signature
        )

        # Setup Routes
        self._setup_routes()

    def _register_handlers(self):
        self.sb.add_request_handler(LaunchRequestHandler())
        self.sb.add_request_handler(SpeechToTextIntentHandler(on_speech_callback=self.on_speech_callback))
        self.sb.add_request_handler(HelpIntentHandler())
        self.sb.add_request_handler(SessionEndedRequestHandler())
        self.sb.add_exception_handler(GlobalExceptionHandler())

    def _setup_routes(self):
        @self.app.route('/alexa', methods=['POST'])
        def alexa_endpoint():
            headers = dict(request.headers)
            body = request.get_data(as_text=True)
            response_data = self.skill_response_handler.verify_request_and_dispatch(
                http_request_headers=headers,
                http_request_body=body
            )
            #return Response(response_data, mimetype='application/json')
            return response_data

        @self.app.route('/shutdown', methods=['POST'])
        def shutdown_endpoint():
            """Optional REST endpoint to trigger server shutdown remotely."""
            self.stop()
            return "Server shutting down..."

    def on_speech_received(self, text: str, locale: str):
        """Default SpeechToTextIntentHandler callback (just echo the received text)
           Override this passing a custom callback in the constructor of AlexaSpeechBackend"""
        speech_text = f"Default callback: {text}"
        logger.info(speech_text)
        return speech_text

    def start(self, in_thread: bool = False):
        """Starts the Flask app using Werkzeug's server instance for controlled lifecycle management."""
        self.server = make_server(self.host, self.port, self.app)
        logger.info(f"Starting Alexa SpeechToText backend server on http://{self.host}:{self.port}")

        if in_thread:
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
        else:
            self.server.serve_forever()

    def stop(self):
        """Gracefully shuts down the running Flask/Werkzeug server instance."""
        if self.server:
            logger.info("Stopping Alexa SpeechToText backend server...")
            self.server.shutdown()
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join()
            logger.info("Alexa SpeechToText backend server stopped.")
        else:
            logger.warning("Server is not running.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Instance creation
    alexa_server = AlexaSpeechBackend(host="0.0.0.0", port=5000, verify_signature=False)

    try:
        # Start server in main thread
        alexa_server.start()
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        alexa_server.stop()
