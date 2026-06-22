import sys, os, time, datetime, logging, platform, json
import argparse
import traceback
# https://electronstudio.github.io/raylib-python-cffi/README.html
from pyray import *
# https://www.raylib.com/cheatsheet/cheatsheet.html
import clock
from config import Config, ItemType
from utils.folderwatch import FolderWatch
from utils.display import hdmi_set_on, hdmi_set_off, hdmi_is_connected
from utils.lux2brightness import convert_lux_to_range, get_gauss_hour
from utils.raspberry import is_raspberry_pi, set_autohide_and_notification
from utils.image import resize_to_percentage
from dfshader import create_shader
from dfitems import DFItemList
from dftext import DrawTextTTLList, dftext, update_dftext_vars
from devices import Devices
from mqtt import MQTT
from plugin_manager import PluginManager

class DigitalFrame:
    def __init__(self, fullscreen=None):
        self.exit_code = 0
        self.this = self
        self.platform = platform.system().lower()
        self.logger = logging.getLogger(__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.monitor = 0
        if fullscreen is None:
            self.fullscreen = Config.get('window.fullscreen', True)
        else:
            self.fullscreen = fullscreen
        if self.fullscreen:
            self.width =  Config.get('window.max_width', 3840)  #4K
            self.height = Config.get('window.max_height', 2160)
        else:
            self.width = Config.get('window.width', 1024)
            self.height = Config.get('window.height', 576)
        self.ratio = round(self.width / self.height, 2)
        self.scale_ref_width = Config.get('window.scale_ref_width', 1920)
        self.scale = (self.width / self.scale_ref_width)

        # timing
        clock.fps = Config.get('window.fps', 1)
        clock.ft = 1 / clock.fps
        clock.rft = clock.ft
        self.show_fps = Config.get('window.show_fps', False)
        # draw ttl
        self.dttls = DrawTextTTLList(self)
        # items list
        self.error = None

        self.items = DFItemList(self, Config.get('items.path', ['/path/to/items']))
        # MyHome / Home Assistant control
        self.hdmi_power = Config.get('window.hdmi_power', 2) # 3 for windows
        self.hdmi_is_connected = hdmi_is_connected(self)
        self.hdmi_off_timeout = Config.get('window.hdmi_off_timeout', 0)
        self.image_ttl = Config.get('items.types.image.ttl', 10) # time to live in seconds
        self.hdmi_switch_off_time = time.time() + (self.hdmi_off_timeout * 60)
        self.display = True
        self.paused = False
        # light
        self.lux = 0            # value from the sensor
        self.lux_adj = Config.get('window.lux_adjustment', 40)
        self.brightness = 0     # value in range -128 +128
        self.brightness_normalized = 0 # brightness normalized for the shader
        self.ambient_light = True # True to mimic ambient light
        self.shader = None
        # motion
        self.motion = 0
        self.motion_enabled = True
        self.matting = True
        self.location_filter = None
        self.tags_filter = None
        self.keep_looping = True
        # timer
        self.timer = Config.get('timer.enabled', False)
        self.timer_format = Config.get('timer.format', '%H:%M:%S')
        self.timer_size = Config.get('timer.size', 36)
        self.timer_pos = Config.get('timer.pos', [1, -2])
        self.timer_color = Config.get_color('timer.rgba', [255, 255, 255, 128])
        # actual item
        self.item = None
        # config vars
        self.debug_color = Config.get('window.debug_color', (255, 255, 255, 255))
        self.error_color = Config.get('window.error_color', (255, 0, 0, 255))
        # overlay
        self.show_overlay = False
        self.overlay = None # texture handle
        self.overlay_file = None
        self.overlay_tint = Config.get('window.overlay_color', (255, 255, 255, 192))
        # peripherals
        self.devices = Devices(self)
        self.mqtt = None
        self._publish_state = None
        # plugins
        self.plugins = None
        # sound
        self.sound_enabled = Config.get('items.types.video.sound', False)
        # work handles
        self.texture = None
        self.matte = None
        self.border = None
        self.font = None
        self.show_debug = False
        self.debug = None
        self.show_remote_help = False
        self.help = None

    def update_window(self):
        if self.fullscreen:                 # is_window_resized and get_screen_width/get_screen_height not in sync in raspberry
            set_window_state(ConfigFlags.FLAG_WINDOW_UNDECORATED)
            self.width =  Config.get('window.max_width', 3840)      # get_screen_width()
            self.height = Config.get('window.max_height', 2160)     # get_screen_height()
        else:
            self.width = get_screen_width()
            self.height = get_screen_height()
        self.ratio = round(self.width / self.height, 2)
        self.scale = (self.width / self.scale_ref_width)
        self.devices.menu.set_style_size(self.scale)
        self.devices.menu.osk.set_style_size(self.scale)
        update_dftext_vars()
        if self.help: self.help = unload_texture(self.help)
        if self.item and self.item.type == ItemType.IMAGE:
            self.item.processed = False
        self.logger.debug(f"update_window: {self.fullscreen=}, {self.width=}, {self.height=}")

    def set_full_screen(self):
        set_window_state(ConfigFlags.FLAG_WINDOW_UNDECORATED)
        set_window_position(0, 0)
        set_window_size(Config.get('window.max_width', 3840), Config.get('window.max_height', 2160))
        self.logger.debug(f"set_full_screen: {get_screen_width()=}, {Config.get('window.max_width', 3840)}, {get_screen_height()=}, {Config.get('window.max_height', 2160)}")

    def toogle_window_size(self):
        if self.fullscreen:
            self.set_full_screen()
            self.update_window()
        else:
            clear_window_state(ConfigFlags.FLAG_WINDOW_UNDECORATED)
            set_window_size(Config.get('window.width', 1024), Config.get('window.height', 576))
            set_window_position(Config.get('window.x', 69), Config.get('window.y', 96))
            show_cursor()
            self.update_window()

    def item_process(self):
        if not self.item:
            self.item = self.items.get()
            if self.item:
                self.publish_state(image=self.item.name)
            else:
                #self.error = f"No items to process.\nFolder: '{self.items.subfolder}'\nExtensions: {self.items.all_ext}\nFilter: '{self.items.filter}'\nError: {self.items.filter_error}"
                self.error = f"No items to process.\nFolder: '{self.items.subfolder}'\nFilter: \"{self.items.filter}\"\nError: {self.items.filter_error}"
                return

        self.item.update()

    def main_loop(self):
        self.exit_code = 0

        set_trace_log_level(TraceLogLevel.LOG_WARNING)  #raylib
        #set_trace_log_level(TraceLogLevel.LOG_DEBUG)  #raylib

        self.on_platform_set()
        FolderWatch(self.items)

        if plugins := Config.get('plugins', None):
            self.plugins = PluginManager(self, plugins)
            self.devices.plugins = self.plugins

        if self.fullscreen: set_window_state(ConfigFlags.FLAG_WINDOW_UNDECORATED|ConfigFlags.FLAG_WINDOW_TOPMOST)
        else: set_window_state(ConfigFlags.FLAG_WINDOW_RESIZABLE)
        init_window(self.width, self.height, "DigitalFrame v1.0")
        if self.fullscreen: disable_cursor()
        self.monitor = get_current_monitor()
        if self.fullscreen:
            self.width = get_monitor_width(self.monitor)
            Config.set('window.max_width', self.width)
            self.height = get_monitor_height(self.monitor)
            Config.set('window.max_height', self.height)
            self.logger.debug(f"get_monitor_width: {self.width}, get_monitor_height: {self.height}")

        self.load_icon()

        self.font = load_font(os.path.join(Config.RESOURCES, Config.get('window.font', "LiberationMono-Regular.ttf")))

        self.shader = create_shader(self)

        if self.sound_enabled: init_audio_device()

        self.mqtt_init()

        set_target_fps(clock.fps)
        while not window_should_close() and self.keep_looping:
            clock.rft = get_frame_time()
            if is_window_resized(): self.update_window()

            if self.hdmi_is_connected:
                self.check_switch_off_time()

            self.devices.keyboard()

            if not self.paused and self.items.count():
                self.item_process()

            if self.plugins:
                self.plugins.update_all()

            self.shader.update()

            #
            begin_drawing()

            if self.item:
                self.shader.begin()
                self.item.draw()
                self.shader.end()

            self.dttls.draw_ttl()

            if self.timer:
                now = datetime.datetime.now()
                dftext(now.strftime(self.timer_format), self.timer_pos[0], self.timer_pos[1], font=self.font, fs=self.timer_size*self.scale, tint=self.timer_color, shadow=2)

            if self.show_debug and self.debug:
                msg = self.get_debug_msg()
                dftext(msg, -1, 0, font=self.font, fs=-12*self.scale, tint=self.debug_color, shadow=2)

            if self.show_fps:
                draw_fps(10, 10)

            if self.show_remote_help:
                self.draw_remote_help()

            if self.plugins:
                self.plugins.draw_all()

            if self.devices.menu.is_active:
                self.devices.menu.draw()

            if self.error:
                clear_background(BLACK)
                dftext(self.error, 'C', 'C', font=self.font, fs=24*self.scale, tint=self.error_color, shadow=0)
                self.error = None

            end_drawing()

        self.stop()

        return self.exit_code

    def mqtt_init(self):
        if Config.get('mqtt.enabled', False):
            self.mqtt = MQTT(self)
        else:
            conf = Config.get('mqtt', None)
            if conf and 'server' not in conf:
                conf["server"] = "server"
                conf["port"] = 1883
                conf["login"] = "user"
                conf["password"] = "password"
                conf["tls"] = ""
                conf["client_id"] = "digitalframe"
                conf["device_id"] = "digitalframe"

    def publish_state(self, image=None, image_meta=None):
        if self.mqtt and self._publish_state:
            self._publish_state(image, image_meta)

    def get_motion(self):
        return self.motion

    def set_motion(self, value):
        if self.motion_enabled:
            self.motion = value
            if value > 0:
                self.hdmi_switch_off_time = time.time() + (self.hdmi_off_timeout * 60)
            #self.publish_state()

    def get_paused(self):
        return self.paused

    def set_paused(self, value):
        if self.item: self.item.set_paused(value)
        p = self.paused
        self.paused = value
        if value != p: self.publish_state()

    def get_brightness(self):
        return self.brightness

    def get_brightness_normalized(self): # for the shader
        if self.ambient_light:
            return self.brightness_normalized
        else:
            return 0    # for original brightness

    def set_brightness(self, value):
        self.lux = value
        value += self.lux_adj * get_gauss_hour()
        b = self.brightness
        self.brightness = convert_lux_to_range(value)
        self.brightness_normalized = self.brightness / 128.0
        if self.brightness != b: self.publish_state()

    def set_lux_adj(self, value):
        self.lux_adj += value
        Config.set('window.lux_adjustment', self.lux_adj)
        self.set_brightness(self.lux)

    def set_matting(self, value):
        self.matting = True if value else False

    def set_tags_filter(self, value):
        if value == "*": value = ""
        self.tags_filter = value
        self.items.set_filter(value)
        Config.set('items.filter', value)
        self.logger.info(f"filter: {value}")

    def display_on(self):
        return self.display

    def display_off(self):
        return not self.display

    def display_set_on(self):
        self.display = True
        hdmi_set_on(self)
        if self.platform != "windows": time.sleep(5)
        set_window_focused()
        self.set_paused(False)

    def display_set_off(self):
        self.set_paused(True)
        self.display = False
        hdmi_set_off(self)

    def check_switch_off_time(self):
        if self.hdmi_off_timeout == 0:
            return

        if time.time() > self.hdmi_switch_off_time:
            if self.display_on():
                self.display_set_off()
                self.publish_state()
        else:
            if self.display_off():
                self.display_set_on()
                self.publish_state()

    def get_debug_msg(self):
        msg = f"screen={self.width}x{self.height}, ratio={self.ratio}, folder={self.items.folder}, \
sleep={self.hdmi_off_timeout} min., ttl={self.image_ttl}, ambient={self.ambient_light}, \
brightness={self.brightness}, lux={self.lux}, adj={self.lux_adj}, shader={self.shader.name}, motion_enabled={self.motion_enabled}, \
motion={self.motion}, {self.debug}"
        return msg

    def draw_remote_help(self):
        if not self.help:
            help = load_image(os.path.join(Config.RESOURCES, Config.get('boxput.help', "boxput.png")))
            resize_to_percentage(help, self.width, self.height, 60)
            self.help = load_texture_from_image(help)
            help = unload_image(help)

        draw_texture(self.help, (self.width - self.help.width) // 2, (self.height - self.help.height) // 2, (255, 255, 255, 255))

    def on_platform_set(self):
        if self.platform == "windows":
            self.hdmi_power = 3
        elif is_raspberry_pi():
            self.hdmi_power = 2
        else:
            self.hdmi_power = 4

    def load_icon(self):
        icon = load_image(os.path.join(Config.RESOURCES, "icon.png"))
        set_window_icon(icon)
        icon = unload_image(icon)

    def stop(self):
        try:
            self.logger.info(f"start stopping...")
            self.keep_looping = False
            if self.item: self.item.close()
            if self.shader: self.shader = self.shader.unload()
            if self.texture: self.texture = unload_texture(self.texture)
            if self.matte: self.matte = unload_texture(self.matte)
            if self.border: self.border = unload_texture(self.border)
            if self.help: self.help = unload_texture(self.help)
            pos = get_window_position()
            Config.set('window.x', int(pos.x))
            Config.set('window.y', int(pos.y))
            if self.sound_enabled: close_audio_device()
            close_window()
            if self.devices:
                self.devices.stop()
            if self.mqtt:
                self.mqtt.stop()
            Config.save()
            self.logger.info("stopped.")
        except Exception as e:
            self.logger.error(e)

    def close(self):
        self.exit_code = 0
        self.keep_looping = False

    def reboot(self):
        self.exit_code = 100
        self.keep_looping = False

    def power_down(self):
        self.exit_code = 101
        self.keep_looping = False

def ask_item_path():
    while True:
        path = input("Since this is the first time you're launching the app, enter the path to your media file:")
        if os.path.exists(path):
            break
        else:
            print(f"'{path}' does not exist, please input a valid path")
    return path

def main(args):
    try:
        logging.basicConfig(filename=args.log_file, filemode='a', format="%(asctime)s %(levelname)s %(module)s %(lineno)s: %(message)s", level=logging.INFO)
        #logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info(f"starting {sys.argv}")

        if Config.init(args.config_file):
            if not Config.configured(args.reset_config):
                path = ask_item_path()
                Config.configure(path)

            log_level = Config.get("window.log_level", logging.INFO)
            logger.setLevel(log_level)
            if Config.get("window.hide_taskbar", True): set_autohide_and_notification(True)
            df = DigitalFrame(fullscreen=args.fullscreen)
            ret = df.main_loop()
            if Config.get("window.hide_taskbar", True): set_autohide_and_notification(False)
            return ret
        else:
            return 128
    except Exception as e:
        logger.error(traceback.format_exc())
        return 129

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='digitalframe 1.0')
    parser.add_argument("-c", "--config", help="Config filename", dest="config_file", default="config.json")
    parser.add_argument("-l", "--log", help="Log file", dest="log_file", default="digitalframe.log")
    parser.add_argument("-f", "--fullscreen", action="store_true", help="Start app in fullscreen")
    parser.add_argument("--reset-config", action="store_true", help="Reset config as the first run")
    args = parser.parse_args()
    exit(main(args))
