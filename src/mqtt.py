
import logging
import json, os, ssl
from typing import Optional, List
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
        _client: mqtt.Client,
        _userdata: object,
        _disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode | int | None,
        _properties: Optional[mqtt.Properties] = None,
    ):
        if isinstance(reason_code, mqtt.ReasonCode):
            reason_code_str = f"{reason_code} (value: {reason_code.value})"
        else:
            reason_code_str = str(reason_code)
        self.logger.warning(f"Disconnected from MQTT broker. Return code: {reason_code_str}")
        self.connected = False

    def on_connect(
        self,
        client: mqtt.Client,
        _userdata: object,
        _flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode | int,
        _properties: Optional[mqtt.Properties] = None,
    ):
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
        
        df = self.df

        #client.subscribe(f"{self.device_id}/#")
        client.subscribe(f"homeassistant/switch/{self.device_id}/#")

        # send last will and testament
        available_topic = f"homeassistant/switch/{self.device_id}/available"
        client.publish(available_topic, "online", qos=0, retain=True)

        # sensors
        self.setup_text(client, "location_filter", "mdi:map-search", available_topic, entity_category="config")
        self.setup_text(client, "tags_filter", "mdi:image-search", available_topic, entity_category="config")
        self.setup_sensor(client, "image_counter", "mdi:camera-burst", available_topic, entity_category="diagnostic")
        self.setup_sensor(client, "image", "mdi:file-image", available_topic, has_attributes=True, entity_category="diagnostic")
        self.setup_sensor(client, "temperature", "mdi:temperature", available_topic, entity_category="diagnostic")

        # numbers
        self.setup_number(client, "brightness", 0.0, 10000.0, 1, "mdi:brightness-6", available_topic)
        self.setup_number(client, "time_delay", 1, 3600, 1, "mdi:image-plus", available_topic)
        self.setup_number(client, "motion", 0.0, 100.0, 1, "mdi:motion-sensor", available_topic)
        self.setup_number(client, "autosleep", 0.0, 3600.0, 1, "mdi:power-sleep", available_topic)

        # selects
        _, dir_list = df.items.get_folders()
        #dir_list.sort()
        self.setup_select(client, "directory", dir_list, "mdi:folder-multiple-image", available_topic, init=True)
        command_topic = self.device_id + "/directory"
        client.subscribe(command_topic, qos=0)

        # switches
        self.setup_switch(client, "name_toggle", "mdi:subtitles", available_topic, df.items.text_is_on("name"), entity_category="config")
        self.setup_switch(client, "title_toggle", "mdi:subtitles", available_topic, df.items.text_is_on("title"), entity_category="config")
        self.setup_switch(client, "caption_toggle", "mdi:subtitles", available_topic, df.items.text_is_on("caption"), entity_category="config")
        self.setup_switch(client, "date_toggle", "mdi:calendar-today", available_topic,  df.items.text_is_on("date"), entity_category="config")
        self.setup_switch(client, "location_toggle", "mdi:crosshairs-gps", available_topic, df.items.text_is_on("location"), entity_category="config")
        self.setup_switch(client, "directory_toggle", "mdi:folder", available_topic, df.items.text_is_on("directory"), entity_category="config")
        self.setup_switch(client, "text_off", "mdi:badge-account-horizontal-outline", available_topic, entity_category="config")
        self.setup_switch(client, "display", "mdi:panorama", available_topic, df.display_on())
        self.setup_switch(client, "clock", "mdi:clock-outline", available_topic, df.timer, entity_category="config")
        self.setup_switch(client, "shuffle", "mdi:shuffle-variant", available_topic, df.items.shuffle)
        self.setup_switch(client, "paused", "mdi:pause", available_topic, df.paused)

        # buttons
        self.setup_button(client, "back", "mdi:skip-previous", available_topic)
        self.setup_button(client, "next", "mdi:skip-next", available_topic)

        #client.subscribe(self.device_id + "/motion", qos=0)  # motion detected
        #client.subscribe(self.device_id + "/autosleep", qos=0) # autosleep in minutes (0 for no sleep)
        client.subscribe(self.device_id + "/extra", qos=0)  # show extra images
        client.subscribe(self.device_id + "/stop", qos=0)  # close app
        client.subscribe(self.device_id + "/reboot", qos=0)  # close app ad reboot
        client.subscribe(self.device_id + "/power_down", qos=0)  # close app and shutdown
        client.subscribe(self.device_id + "/keyboard", qos=0)  # virtual keyboard. key_name to send to keyboard function

    def get_dev_element(self) -> dict:
        dev = {
            "ids": [self.device_id],
            "name": self.device_id,
            "mdl": "DigitalFrame",
            "sw": "1.00.00",
            "mf": "DigitalFrame project"
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
        sensor_topic_head = "homeassistant/sensor/" + self.device_id
        config_topic = sensor_topic_head + "_" + topic + "/config"
        name = self.device_id + "_" + topic
        config_dict = {
            "name": topic,
            "icon": icon,
            "value_template": "{{ value_json." + topic + "}}",
            "avty_t": available_topic,
            "uniq_id": name,
            "dev": self.get_dev_element()
        }
        if has_attributes is True:
            config_dict["state_topic"] = sensor_topic_head + \
                "_" + topic + "/state"
            config_dict["json_attributes_topic"] = sensor_topic_head + \
                "_" + topic + "/attributes"
        else:
            config_dict["state_topic"] = sensor_topic_head + "/state"
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
        text_topic_head = "homeassistant/text/" + self.device_id
        config_topic = text_topic_head + "_" + topic + "/config"
        name = self.device_id + "_" + topic
        config_dict = {
            "name": topic,
            "icon": icon,
            "value_template": "{{ value_json." + topic + "}}",
            "state_topic": "homeassistant/sensor/" + self.device_id + "/state",
            "command_topic": self.device_id + "/" + topic,
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
        available_topic: str
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
        number_topic_head = "homeassistant/number/" + self.device_id
        config_topic = number_topic_head + "_" + topic + "/config"
        command_topic = self.device_id + "/" + topic
        state_topic = "homeassistant/sensor/" + self.device_id + "/state"
        name = self.device_id + "_" + topic
        config_payload = json.dumps({"name": topic,
                                     "min": min_value,
                                     "max": max_value,
                                     "step": step,
                                     "icon": icon,
                                     "entity_category": "config",
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
        select_topic_head = "homeassistant/select/" + self.device_id
        config_topic = select_topic_head + "_" + topic + "/config"
        command_topic = self.device_id + "/" + topic
        state_topic = "homeassistant/sensor/" + self.device_id + "/state"
        name = self.device_id + "_" + topic

        config_payload = json.dumps({"name": topic,
                                     "entity_category": "config",
                                     "icon": icon,
                                     "options": options,
                                     "state_topic": state_topic,
                                     "command_topic": command_topic,
                                     "value_template": "{{ value_json." + topic + "}}",
                                     "avty_t": available_topic,
                                     "uniq_id": name,
                                     "dev": self.get_dev_element()})
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
        entity_category: Optional[str] = None
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
        switch_topic_head = "homeassistant/switch/" + self.device_id
        config_topic = switch_topic_head + "_" + topic + "/config"
        command_topic = switch_topic_head + "_" + topic + "/set"
        state_topic = switch_topic_head + "_" + topic + "/state"
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
        client.publish(state_topic, "ON" if is_on else "OFF",
                       qos=0, retain=True)

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
        button_topic_head = "homeassistant/button/" + self.device_id
        config_topic = button_topic_head + "_" + topic + "/config"
        command_topic = button_topic_head + "_" + topic + "/set"
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
        switch_topic_head = "homeassistant/switch/" + self.device_id
        button_topic_head = "homeassistant/button/" + self.device_id

        self.logger.debug(message.topic+"="+msg)

        # ##### switches ######
        # display
        if message.topic == switch_topic_head + "_display/set":
            state_topic = switch_topic_head + "_display/state"
            if msg == "ON":
                df.display_set_on()
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                df.display_set_off()
                client.publish(state_topic, "OFF", retain=True)
        # clock
        elif message.topic == switch_topic_head + "_clock/set":
            state_topic = switch_topic_head + "_clock/state"
            if msg == "ON":
                df.timer = True
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                df.timer = False
                client.publish(state_topic, "OFF", retain=True)
        # shuffle
        elif message.topic == switch_topic_head + "_shuffle/set":
            state_topic = switch_topic_head + "_shuffle/state"
            if msg == "ON":
                df.items.set_shuffle(True)
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                df.items.set_shuffle(False)
                client.publish(state_topic, "OFF", retain=True)
        # paused
        elif message.topic == switch_topic_head + "_paused/set":
            state_topic = switch_topic_head + "_paused/state"
            if msg == "ON":
                df.set_paused(True)
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                df.set_paused(False)
                client.publish(state_topic, "OFF", retain=True)
        # back buttons
        elif message.topic == button_topic_head + "_back/set":
            if msg == "ON":
                df.items.set_prev()
                if df.item: df.item.skip()
        # next buttons
        elif message.topic == button_topic_head + "_next/set":
            if msg == "ON":
                df.items.set_next()
                if df.item: df.item.skip()
        # title on
        elif message.topic == switch_topic_head + "_title_toggle/set":
            state_topic = switch_topic_head + "_title_toggle/state"
            if msg in ("ON", "OFF"):
                df.items.set_show_text("title", msg)
                client.publish(state_topic, msg, retain=True)
        # caption on
        elif message.topic == switch_topic_head + "_caption_toggle/set":
            state_topic = switch_topic_head + "_caption_toggle/state"
            if msg in ("ON", "OFF"):
                df.items.set_show_text("caption", msg)
                client.publish(state_topic, msg, retain=True)
        # name on
        elif message.topic == switch_topic_head + "_name_toggle/set":
            state_topic = switch_topic_head + "_name_toggle/state"
            if msg in ("ON", "OFF"):
                df.items.set_show_text("name", msg)
                client.publish(state_topic, msg, retain=True)
        # date_on
        elif message.topic == switch_topic_head + "_date_toggle/set":
            state_topic = switch_topic_head + "_date_toggle/state"
            if msg in ("ON", "OFF"):
                df.items.set_show_text("date", msg)
                client.publish(state_topic, msg, retain=True)
        # location_on
        elif message.topic == switch_topic_head + "_location_toggle/set":
            state_topic = switch_topic_head + "_location_toggle/state"
            if msg in ("ON", "OFF"):
                df.items.set_show_text("location", msg)
                client.publish(state_topic, msg, retain=True)
        # directory_on
        elif message.topic == switch_topic_head + "_directory_toggle/set":
            state_topic = switch_topic_head + "_directory_toggle/state"
            if msg in ("ON", "OFF"):
                df.items.set_show_text("directory", msg)
                client.publish(state_topic, msg, retain=True)
        # text_off
        elif message.topic == switch_topic_head + "_text_off/set":
            state_topic = switch_topic_head + "_text_off/state"
            if msg == "ON":
                df.items.show_text = False
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_directory_toggle/state"
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_location_toggle/state"
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_date_toggle/state"
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_name_toggle/state"
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_title_toggle/state"
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_caption_toggle/state"
                client.publish(state_topic, "OFF", retain=True)

        # #### values ########
        # change subdirectory
        elif message.topic == self.device_id + "/directory":
            self.logger.debug("Received subdirectory: %s", msg)
            df.items.set_subfolder(msg)
        # time_delay
        elif message.topic == self.device_id + "/time_delay":
            self.logger.debug("Received time_delay: %s", msg)
            df.image_ttl = myfloat(msg)
        # brightness (lux)
        elif message.topic == self.device_id + "/brightness":
            self.logger.debug("Received brightness: %s", msg)
            df.set_brightness(myfloat(msg))
        # location filter
        elif message.topic == self.device_id + "/location_filter":
            self.logger.debug("Received location filter: %s", msg)
            df.location_filter = msg
        # tags filter
        elif message.topic == self.device_id + "/tags_filter":
            self.logger.debug("Received tags filter: %s", msg)
            df.set_tags_filter(msg)
        # set the flag to view extra files
        elif message.topic == self.device_id + "/extra":
            self.logger.debug("Received extra: %s", msg)
            df.items.private = True if (msg.lower() in ["on", "true", "1"]) else False
        # motion
        elif message.topic == self.device_id + "/motion":
            self.logger.debug("Received motion: %s", msg)
            df.set_motion(myfloat(msg))
        # autosleep
        elif message.topic == self.device_id + "/autosleep":
            self.logger.debug("Received autosleep: %s", msg)
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

            sensor_topic_head = "homeassistant/sensor/" + self.device_id
            switch_topic_head = "homeassistant/switch/" + self.device_id
            available_topic = switch_topic_head + "/available"

            sensor_state_payload = {}
            image_state_payload = {}

            # image
            # image attributes
            if image_attr is not None:
                attributes_topic = sensor_topic_head + "_image/attributes"
                self.logger.debug("Send image attributes: %s", image_attr)
                self.client.publish(attributes_topic, json.dumps(image_attr), qos=0, retain=True)
            # image sensor
            if image is not None:
                _, tail = os.path.split(image)
                image_state_payload["image"] = tail
                image_state_topic = sensor_topic_head + "_image/state"
                self.logger.debug("Send image state: %s", image_state_payload)
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
            # temperature
            sensor_state_payload["temperature"] = get_cpu_temp()
            # autosleep
            sensor_state_payload["autosleep"] = df.hdmi_off_timeout

            # update directory list
            #dir_list.sort()
            self.setup_select(self.client, "directory", dir_list, "mdi:folder-multiple-image", available_topic, init=False)

            # publish sensors
            self.logger.debug("Send sensor state: %s", sensor_state_payload)
            sensor_state_topic = sensor_topic_head + "/state"
            self.client.publish(sensor_state_topic, json.dumps(sensor_state_payload), qos=0, retain=True)

            # publish state of switches
            # pause
            state_topic = switch_topic_head + "_paused/state"
            payload = "ON" if df.get_paused() else "OFF"
            self.client.publish(state_topic, payload, retain=True)
            # shuffle
            state_topic = switch_topic_head + "_shuffle/state"
            payload = "ON" if df.items.shuffle else "OFF"
            self.client.publish(state_topic, payload, retain=True)
            # display
            state_topic = switch_topic_head + "_display/state"
            payload = "ON" if df.display_on() else "OFF"
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

