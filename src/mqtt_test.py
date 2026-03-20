
import logging, time, sys
import json, os, ssl
from typing import Optional, List
import paho.mqtt.client as mqtt
from config import Config

def isfloat(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def myfloat(s):
    try:
        if s.isdigit():
            s = s + ".0"
        return float(s)
    except ValueError:
        return 0.0

class MQTT:
    def __init__(self, digitalframe):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("Creating an instance of MQTT for test")
        self.df = digitalframe
        #self.df.publish_state = self.publish_state

        self.device_id = Config.get('mqtt.device_id', None)
        self.device_url = None
        self.broker = Config.get('mqtt.server', None)
        self.port = Config.get('mqtt.port', None)
        self.login = Config.get('mqtt.login', None)
        self.password = Config.get('mqtt.password', None)
        self.tls = Config.get('mqtt.tls', None)
        self.client_id = "mqtt_test" #Config.get('mqtt.client_id', None)
        self.client = None
        self.connected = False
        self.wifi_error_count = 0

        self.topics = []
        self.states = {}

        self.initialize_client()
        self.connect()

    def initialize_client(self):
        self.logger.debug("Initializing MQTT client")
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self.client_id,
            clean_session=True,
        )
        self.client.username_pw_set(self.login, self.password)
        if self.tls:
            self.client.tls_set(self.tls)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    def connect(self):
        try:
            self.logger.info(f"Attempting to connect to MQTT broker at {self.broker}:{self.port}")
            if self.client is not None:
                result = self.client.connect(self.broker, self.port, keepalive=60)
                self.logger.debug(f"Connect result: {result}")
                self.client.loop_start()
                self.connected = True
            else:
                self.logger.error("MQTT client is not initialized.")
        except OSError as error:
            self.logger.warning(f"Network error while connecting to MQTT broker: {error}")
            self.connected = False
            self.wifi_error_count += 1
            if self.wifi_error_count > 30:
                self.df.reboot()
        except ssl.SSLError as error:
            self.logger.warning(f"SSL error while connecting to MQTT broker: {error}")
            self.connected = False
        except Exception as error:  # pylint: disable=broad-except
            self.logger.error(f"Unexpected error while connecting to MQTT broker:: {error}")
            self.connected = False

    def on_disconnect(self, client: mqtt.Client, userdata: object, disconnect_flags: mqtt.DisconnectFlags, reason_code, properties=None):
        if isinstance(reason_code, mqtt.ReasonCode):
            reason_code_str = f"{reason_code} (value: {reason_code.value})"
        else:
            reason_code_str = str(reason_code)
        self.logger.warning(f"Disconnected from MQTT broker. Return code: {reason_code_str}")
        self.connected = False

    def on_connect(self, client: mqtt.Client, userdata: object, flags: mqtt.ConnectFlags, reason_code, properties=None):
        if reason_code != 0:
            if isinstance(reason_code, mqtt.ReasonCode):
                reason_code_str = f"{reason_code} (value: {reason_code.value})"
            else:
                reason_code_str = str(reason_code)
            self.logger.warning(f"Can't connect with MQTT broker. Reason = {reason_code_str}")
            self.connected = False
            return
        self.logger.info("Connected with MQTT broker")
        self.connected = True

        client.subscribe(f"{self.device_id}/#")
        client.subscribe(f"homeassistant/+/+/config")
        client.subscribe(f"homeassistant/+/+/state")

    def on_message(self, client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage):
        msg = message.payload.decode("utf-8")
        if "digitalframe" in message.topic:
            if message.topic.endswith("/config"):
                self.topics.append(json.loads(msg))
            else:
                self.states[message.topic] = msg
                self.logger.debug(message.topic+"="+msg)

config_file = None if len(sys.argv) == 1 else sys.argv[1]
Config.init(config_file)
logging.basicConfig(filename='mqtt.log', filemode='a', format='%(asctime)s %(levelname)s %(module)s %(lineno)s: %(message)s', level=logging.DEBUG)

mymqtt = MQTT(None)

loop = True
while loop:
    time.sleep(5)
    mymqtt.logger.debug(">>>> start test topic")
    for topic in mymqtt.topics:
        value_template: str = topic.get("value_template", None)
        if value_template:
            value_template = value_template.replace("{{ value_json.", "").replace("}}", "")
        state_topic = topic.get("state_topic", None)
        command_topic = topic.get("command_topic", None)
        if command_topic:
            if "/text/" in command_topic:
                payload = "filter_text"
                mymqtt.logger.debug(f"{command_topic=} {payload=}")
                mymqtt.client.publish(command_topic, payload, retain=False)   
                time.sleep(0.1)
            elif "/switch/" in command_topic:
                payload = "ON"
                mymqtt.logger.debug(f"{command_topic=} {payload=}")
                mymqtt.client.publish(command_topic, payload, retain=False)   
                time.sleep(0.1)
                payload = "OFF"
                mymqtt.logger.debug(f"{command_topic=} {payload=}")
                mymqtt.client.publish(command_topic, payload, retain=False)   
                time.sleep(0.1)
            elif "/select/" in command_topic:
                payload = "bw"
                mymqtt.logger.debug(f"{command_topic=} {payload=}")
                mymqtt.client.publish(command_topic, payload, retain=False)   
                time.sleep(0.1)
            elif "/number/" in command_topic:
                payload = "0.0"
                mymqtt.logger.debug(f"{command_topic=} {payload=}")
                mymqtt.client.publish(command_topic, payload, retain=False)   
                time.sleep(0.1)
                payload = "1.0"
                mymqtt.logger.debug(f"{command_topic=} {payload=}")
                mymqtt.client.publish(command_topic, payload, retain=False)   
                time.sleep(0.1)
            elif "/button/" in command_topic:
                payload = "ON"
                mymqtt.logger.debug(f"{command_topic=} {payload=}")
                mymqtt.client.publish(command_topic, payload, retain=False)   
                time.sleep(0.1)
                payload = "OFF"
                mymqtt.logger.debug(f"{command_topic=} {payload=}")
                mymqtt.client.publish(command_topic, payload, retain=False)   
                time.sleep(0.1)
        else:
            if value_template:
                if state_topic in mymqtt.states:
                    state = mymqtt.states[state_topic]
                    js = json.loads(state)
                    payload = js.get(value_template, "undefined")
                    mymqtt.logger.debug(f"{command_topic=} {payload=}")
                else:
                    mymqtt.logger.debug(f"{state_topic=} not found <<<<<<<<<<<<<<")
            else:
                mymqtt.logger.debug(f"{topic}")

    #loop = False

