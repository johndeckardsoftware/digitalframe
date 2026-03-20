import sys, os, time, datetime, logging, platform, math
import traceback
# https://electronstudio.github.io/raylib-python-cffi/README.html
from pyray import *
# https://www.raylib.com/cheatsheet/cheatsheet.html
#from raylib import *
import clock
from config import Config, ItemType
from utils.folderwatch import FolderWatch
from utils.display import hdmi_set_on, hdmi_set_off, hdmi_is_connected
from utils.lux2brightness import convert_lux_to_range
from dfitems import DFItemList
from dftext import DrawTextTTLList, dftext, update_dftext_vars
from devices import Devices
from mqtt import MQTT

class DigitalFrame:
    def __init__(self):
        self.exit_code = 0
        self.this = self
        self.platform = platform.system().lower()
        self.logger = logging.getLogger(__name__)
        #self.logger.setLevel(logging.DEBUG)
        self.monitor = 0
        self.fullscreen = Config.get('window.fullscreen', True)
        if self.fullscreen:
            self.width =  Config.get('window.max_width', 3840)  #4K
            self.height = Config.get('window.max_height', 2160)
        else:
            self.width = Config.get('window.width', 1024)
            self.height = Config.get('window.height', 576)
        self.ratio = round(self.width / self.height, 2)
        # timing
        clock.fps = Config.get('window.fps', 1)
        clock.rft = 1 / clock.fps
        self.fps = clock.fps
        self.ft = clock.rft
        self.ftt = 0
        self.show_fps = Config.get('window.show_fps', False)
        # draw ttl
        self.dttls = DrawTextTTLList(self)
        # items list
        self.error = None
        self.items = DFItemList(self, Config.get('items.path', ['C:/temp/rpi4-frame/Pictures']))
        # peripherals
        self.devices = Devices(self)
        self.mqtt = None
        self._publish_state = None
        # MyHome / Home Assistant control
        self.hdmi_power = Config.get('window.hdmi_power', 3)
        self.hdmi_is_connected = hdmi_is_connected(self)
        self.hdmi_off_timeout = Config.get('window.hdmi_off_timeout', 0)
        self.image_ttl = Config.get('items.types.image.ttl', 10) # time to live in seconds
        self.hdmi_switch_off_time = time.time() + (self.hdmi_off_timeout * 60)
        self.display = True
        self.paused = False
        # light
        self.lux = 0            # value from the sensor
        self.lux_adj = Config.get('window.lux_adjustment', 130) 
        self.brightness = 0     # value form image_brigthness or ligth_shader
        self.brightness_enabled = True
        self.use_light_shader = Config.get('items.types.image.use_light_shader', True)
        self.light_direction = Config.get('items.types.image.light_direction', 0)
        self.shader = None
        # Lower values (0.2) make a "hard line" of light, higher values (2.0) make the light very subtle and spread out
        self.light_softness = Config.get('items.types.image.light_softness', 3.0)
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
        self.timer_size = Config.get('timer.size', -30)
        self.timer_color = Config.get_color('timer.rgba', [255, 255, 255, 128])
        # actual item
        self.item = None
        # config vars
        self.debug_color=Config.get('window.debug_color', (255,255,255,255))
        self.error_color=Config.get('window.error_color', (255,0,0,255))
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
        update_dftext_vars()
        if self.item and self.item.type == ItemType.IMAGE:
            self.item.processed = False

    def set_full_screen(self):
        set_window_state(ConfigFlags.FLAG_WINDOW_UNDECORATED)
        set_window_position(0, 0)
        set_window_size(Config.get('window.max_width', 3840), Config.get('window.max_height', 2160))

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
                self.error = f"No item to process.\nFolder: \"{self.items.subfolder}\"\nFilter: \"{self.items.filter}\"\nError: {self.items.filter_error}"
                return

        self.item.update()

    def main_loop(self):
        self.exit_code = 0

        set_trace_log_level(TraceLogLevel.LOG_WARNING)  #raylib
        #set_trace_log_level(TraceLogLevel.LOG_DEBUG)  #raylib

        self.mqtt_init()

        FolderWatch(self.items)

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

        icon = load_image(os.path.join(Config.RESOURCES,"icon.png"))
        set_window_icon(icon)
        unload_image(icon)

        # Load font
        self.font = load_font(os.path.join(Config.RESOURCES, Config.get('window.font', "LiberationMono-Regular.ttf")))

        # Load shader
        if self.use_light_shader:
            self.shader = load_shader(ffi.NULL, "src/resources/linear_light.fs")
            int_loc = get_shader_location(self.shader, "uIntensity")
            dir_loc = get_shader_location(self.shader, "uDirection")
            soft_loc = get_shader_location(self.shader, "uSoftness")

        set_target_fps(clock.fps)
        while not window_should_close() and self.keep_looping:
            clock.rft = get_frame_time()
            if is_window_resized(): self.update_window()

            if self.hdmi_is_connected:
                self.check_switch_off_time()

            self.devices.keyboard()

            if not self.paused and self.items.count():
                self.item_process()

            # Set shader
            if self.use_light_shader:
                self.set_light_shader(self.shader, int_loc, dir_loc, soft_loc)

            #
            begin_drawing()

            if self.item:
                if self.use_light_shader:
                    begin_shader_mode(self.shader)
                self.item.draw()
                if self.use_light_shader:
                    end_shader_mode()

            self.dttls.draw_ttl()

            if self.timer:
                now = datetime.datetime.now()
                dftext(now.strftime(self.timer_format), 1, -3, fs=self.timer_size, tint=self.timer_color, shadow=2)

            if self.show_debug and self.debug:
                msg = self.get_debug_msg()
                dftext(msg, -1, 0, font=self.font, fs=-24, tint=self.debug_color, shadow=2)

            if self.show_fps:
                draw_fps(10, 10)

            if self.show_remote_help:
                self.remote_help()

            if self.error:
                clear_background(BLACK)
                dftext(self.error, 'C', 'C', font=self.font, fs=48, tint=self.error_color, shadow=0)
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
            self.publish_state()

    def get_paused(self):
        return self.paused

    def set_paused(self, value):
        p = self.paused
        self.paused = value
        if value != p: self.publish_state()

    def get_brightness(self):
        return self.brightness

    def set_brightness(self, value):
        value += self.lux_adj
        self.lux = value
        b = self.brightness
        self.brightness= convert_lux_to_range(value)
        if value != b: self.publish_state()

    def set_light_shader(self, shader, int_loc, dir_loc, soft_loc):
        # 1. Normalize Intensity: map -64/64 to roughly -1.0/1.0
        # You can adjust the divisor (64.0) to control how "harsh" the light is
        norm_intensity = self.brightness / 128.0

        # 2. Convert Degrees to a Direction Vector
        radians = math.radians(self.light_direction)
        dir_x = math.cos(radians)
        dir_y = math.sin(radians)

        # 3. Send to GPU
        set_shader_value(shader, int_loc, ffi.new("float *", norm_intensity), ShaderUniformDataType.SHADER_UNIFORM_FLOAT)
        set_shader_value(shader, dir_loc, ffi.new("float[2]", [dir_x, dir_y]), ShaderUniformDataType.SHADER_UNIFORM_VEC2)
        # Send softness to GPU
        # Lower values (0.2) make a "hard line" of light, higher values (2.0) make the light very subtle and spread out
        set_shader_value(shader, soft_loc, ffi.new("float *", self.light_softness), ShaderUniformDataType.SHADER_UNIFORM_FLOAT)

    def set_matting(self, value):
        self.matting = True if value else False

    def set_tags_filter(self, value):
        if value == "*": value = ""
        self.tags_filter = value
        self.items.filter = value
        self.logger.info(f"filter: {value}")

    def display_on(self):
        return self.display

    def display_off(self):
        return not self.display

    def display_set_on(self):
        self.display = True
        hdmi_set_on(self)
        if self.platform != "windows":
            time.sleep(30)
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
        else:
            if self.display_off():
                self.display_set_on()

    def get_debug_msg(self):
        msg = f"screen={self.width}x{self.height}, ratio={self.ratio}, folder={self.items.folder}, \
hdmi_off_timeout={self.hdmi_off_timeout}, image_ttl={self.image_ttl}, brightness_enabled={self.brightness_enabled}, \
brightness={self.brightness}, lux={self.lux}, shader={self.use_light_shader}, motion_enabled={self.motion_enabled}, motion={self.motion}, \
{self.debug}"
        return msg

    def remote_help(self):
        if not self.help:
            help = load_image(os.path.join(Config.RESOURCES, Config.get('boxput.help', "boxput.png")))
            if help.height > self.height:
                ratio = help.width / help.height
                height = self.height - 32
                width = int(ratio * height)
                image_resize(help, width, height)
                #if self.help: unload_texture(self.help)
            self.help = load_texture_from_image(help)
            unload_image(help)

        draw_texture(self.help, (self.width - self.help.width) // 2, (self.height - self.help.height) // 2, (255, 255, 255, 255))

    def stop(self):
        try:
            self.logger.info(f"start stopping...")
            self.keep_looping = False
            if self.item: self.item.close()
            if self.use_light_shader: unload_shader(self.shader)
            if self.texture: unload_texture(self.texture)
            if self.matte: unload_texture(self.matte)
            if self.border: unload_texture(self.border)
            if self.help: unload_texture(self.help)
            pos = get_window_position()
            Config.set('window.x', int(pos.x))
            Config.set('window.y', int(pos.y))
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
        self.exit_code = 1
        self.keep_looping = False

    def power_down(self):
        self.exit_code = 2
        self.keep_looping = False

def main():
    config_file = None if len(sys.argv) == 1 else sys.argv[1]
    if not Config.exists(config_file):
        while True:
            path = input("As first run (config.json not found) input the images path:")
            if os.path.exists(path):
                break
            else:
                print(f"'{path}' does not exist, please input a valid path")
    else:
        path = None

    if Config.init(config_file, path):
        try:
            log_level = Config.get("window.log_level", logging.INFO)
            logging.basicConfig(filename='digitalframe.log', filemode='a', format="%(asctime)s %(levelname)s %(module)s %(lineno)s: %(message)s", level=log_level)
            #logging.basicConfig(stream=sys.stdout, level=logging.INFO)
            logger = logging.getLogger(__name__)
            logger.info(f"starting {sys.argv}")
            df = DigitalFrame()
            return df.main_loop()
        except Exception as e:
            logger.error(traceback.format_exc())
            return 129
    else:
        return 128

if __name__ == "__main__":
    exit(main())
