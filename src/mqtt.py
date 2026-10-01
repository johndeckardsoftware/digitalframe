
import logging
import json, os, ssl
from typing import Optional, List, Dict, Any
import paho.mqtt.client as mqtt
from config import Config
from utils.metrics import get_cpu_temp

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
        #self.logger.setLevel(logging.DEBUG)
        self.logger.debug("Creating an instance of MQTT")
        self.df = digitalframe
        self.df._publish_state = self.publish_state

        self.device_id = Config.get('mqtt.device_id', "digitalframe")
        self.device_url = None
        self.broker = Config.get('mqtt.server', "server")
        self.port = Config.get('mqtt.port', 1883)
        self.login = Config.get('mqtt.login', "user")
        self.password = Config.get('mqtt.password', "password")
        self.tls = Config.get('mqtt.tls', "")
        self.client_id = Config.get('mqtt.client_id', "digitalframe")
        self.devices = Config.get('mqtt.devices', [])
        self.client = None
        self.connected = False
        self.wifi_error_count = 0

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

    def on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        reason_code: mqtt.ReasonCodes | int | None,
        properties: Optional[mqtt.Properties] = None,
    ):
        if isinstance(reason_code, mqtt.ReasonCodes):
            reason_code_str = f"{reason_code} (value: {reason_code.value})"
        else:
            reason_code_str = str(reason_code)
        self.logger.warning(f"Disconnected from MQTT broker. Return code: {reason_code_str}")
        self.connected = False

    def on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: Dict[str, Any],
        reason_code: mqtt.ReasonCodes | int,
        properties: Optional[mqtt.Properties] = None,
    ):
        if reason_code != 0:
            if isinstance(reason_code, mqtt.ReasonCodes):
                reason_code_str = f"{reason_code} (value: {reason_code.value})"
            else:
                reason_code_str = str(reason_code)
            self.logger.warning(f"Can't connect with MQTT broker. Reason = {reason_code_str}")
            self.connected = False
            return
        self.logger.info("Connected with MQTT broker")
        self.connected = True

        df = self.df

        #client.subscribe(f"{self.device_id}/#")
        client.subscribe(f"homeassistant/switch/{self.device_id}/#")

        # send last will and testament
        available_topic = f"homeassistant/switch/{self.device_id}/available"
        client.publish(available_topic, "online", qos=0, retain=True)

        # sensors
        self.setup_text(client, "location_filter", "mdi:map-search", available_topic, entity_category=None)
        self.setup_text(client, "tags_filter", "mdi:image-search", available_topic, entity_category=None)
        self.setup_sensor(client, "image_counter", "mdi:camera-burst", available_topic, entity_category="diagnostic")
        self.setup_sensor(client, "image", "mdi:image", available_topic, has_attributes=True, entity_category="diagnostic")
        self.setup_sensor(client, "temperature", "mdi:temperature-celsius", available_topic, entity_category="diagnostic")

        # numbers
        self.setup_number(client, "brightness", -128, 128, 1, "mdi:brightness-6", available_topic, entity_category="diagnostic")
        self.setup_number(client, "time_delay", 1, 3600, 1, "mdi:timer-play", available_topic)
        self.setup_number(client, "motion", 0.0, 100.0, 1, "mdi:motion-sensor", available_topic)
        self.setup_number(client, "autosleep", 0.0, 3600.0, 1, "mdi:monitor-off", available_topic)

        # selects
        _, dir_list = df.items.get_folders()
        #dir_list.sort()
        self.setup_select(client, "directory", dir_list, "mdi:folder-multiple-image", available_topic, init=True, entity_category=None)
        command_topic = self.device_id + "/directory"
        client.subscribe(command_topic, qos=0)

        # switches
        self.setup_switch(client, "meta_name", "mdi:subtitles-outline", available_topic, df.items.text_is_on("name"))
        self.setup_switch(client, "meta_title", "mdi:subtitles-outline", available_topic, df.items.text_is_on("title"))
        self.setup_switch(client, "meta_caption", "mdi:subtitles-outline", available_topic, df.items.text_is_on("caption"))
        self.setup_switch(client, "meta_date", "mdi:calendar-today", available_topic,  df.items.text_is_on("date"))
        self.setup_switch(client, "meta_location", "mdi:crosshairs-gps", available_topic, df.items.text_is_on("location"))
        self.setup_switch(client, "meta_directory", "mdi:folder", available_topic, df.items.text_is_on("directory"))
        self.setup_switch(client, "meta_off", "mdi:information-off-outline", available_topic)
        self.setup_switch(client, "clock", "mdi:clock-outline", available_topic, df.timer, entity_category=None)
        self.setup_switch(client, "shuffle", "mdi:shuffle-variant", available_topic, df.items.shuffle, entity_category=None)
        self.setup_switch(client, "paused", "mdi:pause", available_topic, df.paused, entity_category=None)
        self.setup_switch(client, "monitor", "mdi:monitor-off", available_topic, df.display_on(), entity_category=None)
        self.setup_switch(client, "standby", "mdi:power-standby", available_topic, df.is_standby(), entity_category=None)

        # buttons
        self.setup_button(client, "back", "mdi:skip-previous", available_topic)
        self.setup_button(client, "next", "mdi:skip-next", available_topic)

        client.subscribe(self.device_id + "/extra", qos=0)  # show extra images
        client.subscribe(self.device_id + "/stop", qos=0)  # close app
        client.subscribe(self.device_id + "/reboot", qos=0)  # close app ad reboot
        client.subscribe(self.device_id + "/power_down", qos=0)  # close app and shutdown
        client.subscribe(self.device_id + "/keyboard", qos=0)  # virtual keyboard. key_name to send to keyboard function

        """ subscribe illumination and motion devices in 'mqtt' key. for example:
        "devices": [
            {"state_topic": "rvml/sensors/pir/status", "device_class": "motion"},
            {"state_topic": "home/e04b4101a7fc0000000000009cac0000_AllArea/status", "device_class": "motion"},
            {"state_topic": "rvml/sensors/bh1750/status", "device_class": "illumination"}
        ]
        """
        for device in self.devices:
            client.subscribe(device['state_topic'], qos=0)

    def get_dev_element(self) -> dict:
        dev = {
            "ids": [self.device_id],
            "name": self.device_id,
            "mdl": "Digitalframe",
            "sw": "3.00.00",
            "mf": "Digitalframe Project"
        }
        if self.device_url:
            dev["cu"] = self.device_url
        return dev

    def setup_sensor(
        self,
        client: mqtt.Client,
        topic: str,
        icon: str,
        available_topic: str,
        has_attributes: bool = False,
        entity_category: Optional[str] = None
    ):
        """
        Set up a sensor in Home Assistant.

        Args:
            client: The MQTT client used to publish and subscribe to topics.
            topic: The topic of the sensor.
            icon: The icon to be displayed for the sensor.
            available_topic: The availability topic of the sensor.
            has_attributes: A boolean indicating whether the sensor has attributes.
            entity_category: The category of the sensor entity.

        Returns:
            None
        """
        sensor_topic_head = f"homeassistant/sensor/{self.device_id}/"
        config_topic = f"{sensor_topic_head}{topic}/config"
        name = f"{self.device_id}_{topic}"
        config_dict = {
            "name": topic,
            "icon": icon,
            "value_template": "{{ value_json." + topic + "}}",
            "avty_t": available_topic,
            "uniq_id": name,
            "dev": self.get_dev_element()
        }
        if has_attributes is True:
            config_dict["state_topic"] = f"{sensor_topic_head}{topic}/state"
            config_dict["json_attributes_topic"] = f"{sensor_topic_head}{topic}/attributes"
        else:
            config_dict["state_topic"] = f"{sensor_topic_head}state"
        if entity_category:
            config_dict["entity_category"] = entity_category

        config_payload = json.dumps(config_dict)
        client.publish(config_topic, config_payload, qos=0, retain=True)
        client.subscribe(self.device_id + "/" + topic, qos=0)

    def setup_text(
        self,
        client: mqtt.Client,
        topic: str,
        icon: str,
        available_topic: str,
        entity_category: Optional[str] = None
    ) -> None:
        """
        Sets up the text sensor configuration and publishes it to the MQTT broker.

        Args:
            client (mqtt.Client): The MQTT client instance.
            topic (str): The topic of the text sensor.
            icon (str): The icon to be displayed for the text sensor.
            available_topic (str): The availability topic for the text sensor.
            entity_category (str, optional): The entity category of the text sensor.

        Returns:
            None
        """
        text_topic_head = f"homeassistant/text/{self.device_id}/"
        config_topic = f"{text_topic_head}{topic}/config"
        name = f"{self.device_id}_{topic}"
        config_dict = {
            "name": topic,
            "icon": icon,
            "value_template": "{{ value_json." + topic + "}}",
            "state_topic": f"homeassistant/sensor/{self.device_id}/state",
            "command_topic": f"{self.device_id}/{topic}",
            "avty_t": available_topic,
            "uniq_id": name,
            "dev": self.get_dev_element()
        }
        if entity_category:
            config_dict["entity_category"] = entity_category

        config_payload = json.dumps(config_dict)
        client.publish(config_topic, config_payload, qos=0, retain=True)
        client.subscribe(self.device_id + "/" + topic, qos=0)

    def setup_number(
        self,
        client: mqtt.Client,
        topic: str,
        min_value: float,
        max_value: float,
        step: float,
        icon: str,
        available_topic: str,
        entity_category: str="config"
    ) -> None:
        """
        Set up a number entity in Home Assistant.

        Args:
            client (mqtt.Client): The MQTT client used for communication.
            topic (str): The topic of the number entity.
            min (float): The minimum value of the number entity.
            max (float): The maximum value of the number entity.
            step (float): The step value for incrementing or decrementing the number entity.
            icon (str): The icon to be displayed for the number entity.
            available_topic (str): The topic used to indicate the availability of the number entity.

        Returns:
            None
        """
        number_topic_head = f"homeassistant/number/{self.device_id}/"
        config_topic = f"{number_topic_head}{topic}/config"
        command_topic = f"{self.device_id}/{topic}"
        state_topic = f"homeassistant/sensor/{self.device_id}/state"
        name = f"{self.device_id}_{topic}"
        config_payload = json.dumps({"name": topic,
                                     "min": min_value,
                                     "max": max_value,
                                     "step": step,
                                     "icon": icon,
                                     "entity_category": entity_category,
                                     "state_topic": state_topic,
                                     "command_topic": command_topic,
                                     "value_template": "{{ value_json." + topic + "}}",
                                     "avty_t": available_topic,
                                     "uniq_id": name,
                                    "dev": self.get_dev_element()})
        client.publish(config_topic, config_payload, qos=0, retain=True)
        client.subscribe(command_topic, qos=0)

    def setup_select(
        self,
        client: mqtt.Client,
        topic: str,
        options: List[str],
        icon: str,
        available_topic: str,
        entity_category: str="config",
        init: bool = False
    ) -> None:
        """
        Set up a select component in Home Assistant.

        Args:
            client (mqtt.Client): The MQTT client used to publish and subscribe to topics.
            topic (str): The topic of the select component.
            options (list): The list of options for the select component.
            icon (str): The icon to be displayed for the select component.
            available_topic (str): The availability topic for the select component.
            init (bool, optional): Whether to subscribe to the command topic during i
                nitialization. Defaults to False.
        """
        select_topic_head = f"homeassistant/select/{self.device_id}/"
        config_topic = f"{select_topic_head}{topic}/config"
        command_topic = f"{self.device_id}/{topic}"
        state_topic = f"homeassistant/sensor/{self.device_id}/state"
        name = f"{self.device_id}_{topic}"
        config_dict = {
            "name": topic,
            "icon": icon,
            "options": options,
            "state_topic": state_topic,
            "command_topic": command_topic,
            "value_template": "{{ value_json." + topic + "}}",
            "avty_t": available_topic,
            "uniq_id": name,
            "dev": self.get_dev_element()
        }
        if entity_category:
            config_dict["entity_category"] = entity_category
        config_payload = json.dumps(config_dict)
        client.publish(config_topic, config_payload, qos=0, retain=True)
        if init:
            client.subscribe(command_topic, qos=0)

    def setup_switch(
        self,
        client: mqtt.Client,
        topic: str,
        icon: str,
        available_topic: str,
        is_on: bool = False,
        entity_category: str="config"
    ) -> None:
        """
        Sets up a switch in Home Assistant.

        Args:
            client (mqtt.Client): The MQTT client object.
            topic (str): The topic of the switch.
            icon (str): The icon to be displayed for the switch.
            available_topic (str): The availability topic for the switch.
            is_on (bool, optional): The initial state of the switch. Defaults to False.
            entity_category (str, optional): The category of the entity. Defaults to None.
        """
        switch_topic_head = f"homeassistant/switch/{self.device_id}/"
        config_topic = f"{switch_topic_head}{topic}/config"
        command_topic = f"{switch_topic_head}{topic}/set"
        state_topic = f"{switch_topic_head}{topic}/state"
        config_dict = {
            "name": topic,
            "icon": icon,
            "command_topic": command_topic,
            "state_topic": state_topic,
            "avty_t": available_topic,
            "uniq_id": self.device_id + "_" + topic,
            "dev": self.get_dev_element()
        }
        if entity_category:
            config_dict["entity_category"] = entity_category
        config_payload = json.dumps(config_dict)

        client.subscribe(command_topic, qos=0)
        client.publish(config_topic, config_payload, qos=0, retain=True)
        client.publish(state_topic, "ON" if is_on else "OFF", qos=0, retain=True)

    def setup_button(self, client: mqtt.Client, topic: str, icon: str,
                       available_topic: str, entity_category: Optional[str] = None) -> None:
        """
        Set up a button configuration for the Home Assistant integration.

        Args:
            client (mqtt.Client): The MQTT client used for communication.
            topic (str): The topic of the button.
            icon (str): The icon to be displayed for the button.
            available_topic (str): The availability topic for the button.
            entity_category (str, optional): The category of the entity. Defaults to None.

        Returns:
            None
        """
        button_topic_head = f"homeassistant/button/{self.device_id}/"
        config_topic = f"{button_topic_head}{topic}/config"
        command_topic = f"{button_topic_head}{topic}/set"
        config_dict = {
            "name": topic,
            "icon": icon,
            "command_topic": command_topic,
            "payload_press": "ON",
            "avty_t": available_topic,
            "uniq_id": self.device_id + "_" + topic,
            "dev": self.get_dev_element()
        }
        if entity_category:
            config_dict["entity_category"] = entity_category
        config_payload = json.dumps(config_dict)

        client.subscribe(command_topic, qos=0)
        client.publish(config_topic, config_payload, qos=0, retain=True)

    def on_message(
        self,
        client: mqtt.Client,
        _userdata: object,
        message: mqtt.MQTTMessage
    ) -> None:
        """
        Callback function that is called when a message is received.

        Args:
            client: The MQTT client instance.
            userdata: The user data passed to the MQTT client.
            message: An instance of the MQTTMessage class representing the received message.

        Returns:
            None

        Raises:
            None
        """
        df = self.df
        msg = message.payload.decode("utf-8")
        switch_topic_head = f"homeassistant/switch/{self.device_id}/"
        button_topic_head = f"homeassistant/button/{self.device_id}/"

        self.logger.debug(message.topic+"="+msg)

        # motion
        #if message.topic == self.device_id + "/motion":
        #    self.logger.debug(f"Received motion: {msg}")
        #    df.set_motion(myfloat(msg))
        # lux
        #elif message.topic == self.device_id + "/brightness":
        #    self.logger.debug(f"Received brightness: {msg}")
        #    df.set_lux(myfloat(msg))

        for device in self.devices:
            if message.topic == device['state_topic']:
                if device['device_class'] == "motion":
                    self.logger.debug(f"{device}, {msg=}")
                    df.set_motion(myfloat(msg))
                elif  device['device_class'] == "illumination":
                    self.logger.debug(f"{device}, {msg=}")
                    df.set_lux(myfloat(msg))

        # back buttons
        if message.topic == button_topic_head + "back/set":
            if msg == "ON":
                df.items.set_prev()
                if df.item: df.item.skip()
        # next buttons
        elif message.topic == button_topic_head + "next/set":
            if msg == "ON":
                df.items.set_next()
                if df.item: df.item.skip()
        # paused
        elif message.topic == switch_topic_head + "paused/set":
            state_topic = switch_topic_head + "paused/state"
            if msg == "ON":
                df.set_paused(True)
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                df.set_paused(False)
                client.publish(state_topic, "OFF", retain=True)
        # monitor
        elif message.topic == switch_topic_head + "monitor/set":
            state_topic = switch_topic_head + "monitor/state"
            if msg == "ON":
                df.display_set_on()
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                df.display_set_off()
                client.publish(state_topic, "OFF", retain=True)
        # standby
        elif message.topic == switch_topic_head + "standby/set":
            state_topic = switch_topic_head + "standby/state"
            df.set_standby(msg)
            client.publish(state_topic, msg, retain=True)
        # clock
        elif message.topic == switch_topic_head + "clock/set":
            state_topic = switch_topic_head + "clock/state"
            if msg == "ON":
                df.timer = True
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                df.timer = False
                client.publish(state_topic, "OFF", retain=True)
        # shuffle
        elif message.topic == switch_topic_head + "shuffle/set":
            state_topic = switch_topic_head + "shuffle/state"
            if msg == "ON":
                df.items.set_shuffle(True)
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                df.items.set_shuffle(False)
                client.publish(state_topic, "OFF", retain=True)
        # change subdirectory
        elif message.topic == self.device_id + "/directory":
            self.logger.debug(f"Received subdirectory: {msg}")
            df.items.set_subfolder(msg)
          # time_delay
        elif message.topic == self.device_id + "/time_delay":
            self.logger.debug(f"Received time_delay: {msg}")
            df.image_ttl = myfloat(msg)
        # title on-off
        elif message.topic == switch_topic_head + "meta_title/set":
            self.set_meta(client, switch_topic_head, "title", msg)
        # caption on-off
        elif message.topic == switch_topic_head + "meta_caption/set":
            self.set_meta(client, switch_topic_head, "caption", msg)
        # name on-off
        elif message.topic == switch_topic_head + "meta_name/set":
            self.set_meta(client, switch_topic_head, "name", msg)
        # date on-off
        elif message.topic == switch_topic_head + "meta_date/set":
            self.set_meta(client, switch_topic_head, "date", msg)
        # location on-off
        elif message.topic == switch_topic_head + "meta_location/set":
            self.set_meta(client, switch_topic_head, "location", msg)
        # directory on-off
        elif message.topic == switch_topic_head + "meta_directory/set":
            self.set_meta(client, switch_topic_head, "directory", msg)
        # meta off
        elif message.topic == switch_topic_head + "meta_off/set":
            state_topic = switch_topic_head + "meta_off/state"
            if msg == "ON":
                df.items.show_text = False
                self.set_meta(client, switch_topic_head, "title", "OFF")
                self.set_meta(client, switch_topic_head, "caption", "OFF")
                self.set_meta(client, switch_topic_head, "name", "OFF")
                self.set_meta(client, switch_topic_head, "date", "OFF")
                self.set_meta(client, switch_topic_head, "location", "OFF")
                self.set_meta(client, switch_topic_head, "directory", "OFF")
        # location filter
        elif message.topic == self.device_id + "/location_filter":
            self.logger.debug(f"Received location filter: {msg}")
            df.location_filter = msg
        # tags filter
        elif message.topic == self.device_id + "/tags_filter":
            self.logger.debug(f"Received tags filter: {msg}")
            df.set_tags_filter(msg)
        # set the flag to view extra files
        elif message.topic == self.device_id + "/extra":
            self.logger.debug(f"Received extra: {msg}")
            df.items.private = True if (msg.lower() in ["on", "true", "1"]) else False
        # autosleep
        elif message.topic == self.device_id + "/autosleep":
            self.logger.debug(f"Received autosleep: {msg}")
            df.hdmi_off_timeout = myfloat(msg)

        # stop loops and end program
        elif message.topic == self.device_id + "/stop":
            self.logger.info("Received stop")
            df.close()
        # reboot
        elif message.topic == self.device_id + "/reboot":
            self.logger.info("Received reboot")
            df.reboot()
        # power down
        elif message.topic == self.device_id + "/power_down":
            self.logger.info("Received power down")
            df.power_down()
        # virtual keyboard
        elif message.topic == self.device_id + "/keyboard":
            self.logger.info(f"Received keyboard: {msg}")
            df.devices.send_keys(msg)

    def set_meta(self, client, head, topic, msg):
        state = self.df.items.get_show_text(topic).upper()
        if state == msg:
            return
        state_topic = f"{head}meta_{topic}/state"
        if msg in ("ON", "OFF"):
            self.df.items.set_show_text(topic, msg)
            client.publish(state_topic, msg, retain=True)

    def publish_state(self, image=None, image_attr=None):
        df = self.df
        try:
            if self.client is None:
                self.logger.warning("Cannot publish state. MQTT client is not initialized.")
                return

            if not self.connected:
                self.logger.debug("Not connected to MQTT broker. Attempting to reconnect...")
                self.connect()

            if not self.connected:
                self.logger.warning("Cannot publish state. Not connected to MQTT broker.")
                return

            sensor_topic_head = f"homeassistant/sensor/{self.device_id}/"
            switch_topic_head = f"homeassistant/switch/{self.device_id}/"
            available_topic = switch_topic_head + "available"

            sensor_state_payload = {}
            image_state_payload = {}

            # image
            # image attributes
            if image_attr is not None:
                attributes_topic = sensor_topic_head + "image/attributes"
                self.logger.debug(f"Send image attributes: {image_attr}")
                self.client.publish(attributes_topic, json.dumps(image_attr), qos=0, retain=True)
            # image sensor
            if image is not None:
                _, tail = os.path.split(image)
                image_state_payload["image"] = tail
                image_state_topic = sensor_topic_head + "image/state"
                self.logger.debug(f"Send image state: {image_state_payload}")
                self.client.publish(image_state_topic, json.dumps(image_state_payload), qos=0, retain=True)

            # sensor
            # directory sensor
            actual_dir, dir_list = df.items.get_folders()
            sensor_state_payload["directory"] = actual_dir
            # image counter sensor
            sensor_state_payload["image_counter"] = str(df.items.count())
            # location_filter
            sensor_state_payload["location_filter"] = df.location_filter
            # tags_filter
            sensor_state_payload["tags_filter"] = df.tags_filter
            # number state
            # time_delay
            sensor_state_payload["time_delay"] = df.image_ttl
            # motion
            sensor_state_payload["motion"] = df.get_motion()
            # brightness
            sensor_state_payload["brightness"] = df.get_brightness()
            # lux
            sensor_state_payload["lux"] = df.lux
            # temperature
            sensor_state_payload["temperature"] = get_cpu_temp()
            # autosleep
            sensor_state_payload["autosleep"] = df.hdmi_off_timeout

            # update directory list
            #dir_list.sort()
            self.setup_select(self.client, "directory", dir_list, "mdi:folder-multiple-image", available_topic, init=False)

            # publish sensors
            self.logger.debug(f"Send sensor state: {sensor_state_payload}")
            sensor_state_topic = sensor_topic_head + "state"
            self.client.publish(sensor_state_topic, json.dumps(sensor_state_payload), qos=0, retain=True)

            # publish state of switches
            # pause
            state_topic = switch_topic_head + "paused/state"
            payload = "ON" if df.get_paused() else "OFF"
            self.client.publish(state_topic, payload, retain=True)
            # shuffle
            state_topic = switch_topic_head + "shuffle/state"
            payload = "ON" if df.items.shuffle else "OFF"
            self.client.publish(state_topic, payload, retain=True)
            # display
            state_topic = switch_topic_head + "monitor/state"
            payload = "ON" if df.display_on() else "OFF"
            self.client.publish(state_topic, payload, retain=True)
            # standby
            state_topic = switch_topic_head + "standby/state"
            payload = "ON" if df.is_standby() else "OFF"
            self.client.publish(state_topic, payload, retain=True)
            # clock
            state_topic = switch_topic_head + "clock/state"
            payload = "ON" if df.timer else "OFF"
            self.client.publish(state_topic, payload, retain=True)

            # send last will and testament
            self.client.publish(available_topic, "online", qos=0, retain=True)
        except Exception as e:
            self.logger.error(e)

    def stop(self):
        try:
            self.df._publish_state = None
            if self.client:
                available_topic = f"homeassistant/switch/{self.device_id}/available"
                self.client.publish(available_topic, "offline", qos=0, retain=True)
                self.client.loop_stop()
        except Exception as error:  # pylint: disable=broad-except
            self.logger.error(f"MQTT stopping failed because of: {error}")

