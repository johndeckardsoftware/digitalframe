import logging
import threading
import subprocess
import sys, time, os
from enum import StrEnum

import clock
from pyray import *
from config import Config
from menu import OnScreenMenu
import utils.ddcutil as ddcutil
from utils.metrics import system_metrics, get_cpu_temp
from utils.display import hdmi_toggle

logger = logging.getLogger(__name__)

class Devices:
    def __init__(self, digitalframe):
        logger.setLevel(Config.get("window.log_level", logging.INFO))
        #logger.setLevel(logging.DEBUG)
        self.df = digitalframe
        if Config.get('cron.enabled', True):
            self.cron = Cron(digitalframe)
        else:
            self.cron = None
        if Config.get('boxput.enabled', False):
            self.boxput = BoxPutRemote(digitalframe, self)
        else:
            self.boxput = None

        # raspberry devices
        if Config.get('bluedot.enabled', False):
            from rpi_bluedot import BlueDotRemote
            self.bluedot = BlueDotRemote(digitalframe, self)
        else:
            self.bluedot = None
        if Config.get('pir.enabled', False):
            from rpi_pir import PIRSensor
            self.pir_sensor = PIRSensor(digitalframe)
        else:
            self.pir_sensor = None
        if Config.get('bh1750.enabled', False):
            from rpi_bh1750 import BH1750
            self.bh1750_controller = BH1750(digitalframe)
        else:
            self.bh1750_controller = None

        # map key text to key code
        self.key_map = {name: value for name, value in vars(KeyboardKey).items() if name.startswith("KEY_")}
        key_menu = Config.get('window.menu_key', "KEY_KB_MENU")
        self.key_kb_menu = self.key_map.get(key_menu, KeyboardKey.KEY_KB_MENU)

        self.autosleep = 0
        self.text_pause = None
        self.cur_border = 0
        self.borders = Config.get('items.types.image.borders', [
            {"file": "border01t.png", "opacity": 200, "thick": 6},
            {"file": "border02t.png", "opacity": 200, "thick": 6},
            {"file": "border03t.png", "opacity": 255, "thick": 16},])
        self.cur_matte = 0
        self.mattes = Config.get('items.types.image.mattes', [
            {"texture": "mat_texture1i.jpg", "opacity": 16, "type": 0},
            {"texture": "mat_texture3i.jpg", "opacity": 16, "type": 1},
            {"texture": "mat_texture4i.jpg", "opacity": 16, "type": 2},
            {"texture": "mat_texture5i.jpg", "opacity": 16, "type": 3},
            {"texture": "mat_texture6i.jpg", "opacity": 16, "type": 4},
            {"texture": "mat_texture7.jpg",  "opacity": 16, "type": 9}, ]
            )

        self.actual_dir, self.dir_list = self.df.items.get_folders()
        self.dir_list_index = 0
        self.show_mode = Config.get('items.types.image.show_times', [(60.0, 30.0), (10.0, 60.0), (60.0, 60.0), (15.0, 5.0), (60.0, 10.0)]) #ttl, autosleep
        self.show_mode_index = 0
        self.time_delay, self.autosleep = self.show_mode[0]
        self.inc_value = 5
        self.help = self.load_help()
        self.help_color = Config.get('window.help_color', (255,255,255,255))
        self.metrics_color = Config.get('window.metrics_color', (255,255,255,255))
        self.show = self.df.dttls.show
        self.show3 = self.df.dttls.show3
        self.show4 = self.df.dttls.show4
        # menu and osk
        self.menu = OnScreenMenu(digitalframe, self)
        # plugins
        self.plugins = None

    def get_status(self):
        if self.boxput:
            bp = self.boxput.get_mode()
        else:
            bp = "not installed"
        return f"keyboard: {self.cron.keyboard} BoxPut: {bp}"

    def stop(self) -> None:
        if self.pir_sensor:
            self.pir_sensor.stop()
        if self.bluedot:
            self.bluedot.stop()
        if self.boxput:
            self.boxput.stop()

    def send_keys(self, key_name):
        keys = key_name.strip().upper().split("+")
        vctrl = False
        for key in keys:
            if key == "CTRL": vctrl = True
            else:
                if not key.startswith("KEY_"): key = "KEY_" + key
                if key in self.key_map:
                    vkey = self.key_map[key]
                    self.keyboard(vkey, vctrl)

    def keyboard(self, vkey=None, vctrl=False):
        if vkey: key = vkey
        else: key = get_key_pressed()
        if not key: return

        df = self.df
        if self.menu.is_active and not self.menu.in_action:
            self.menu.update(key)
            return

        if self.plugins.use_keyboard:
            self.plugins.keyboard(key)
            #return

        if (is_key_down(KeyboardKey.KEY_LEFT_CONTROL) or is_key_down(KeyboardKey.KEY_RIGHT_CONTROL) or vctrl):
            if key == KeyboardKey.KEY_M:
                metrics = system_metrics()
                self.show(metrics, 2, 20, tint=self.metrics_color, fs=36, shadow=2, ttl=30)
            elif key == KeyboardKey.KEY_D:
                df.show_debug = not df.show_debug
            elif key == KeyboardKey.KEY_Q:
                f = df.items.filter if df.items.filter != "" else "none"
                self.show3(f"filter: {f}")
            elif key == KeyboardKey.KEY_F:
                df.show_fps = not df.show_fps
            elif key == KeyboardKey.KEY_G:
                fps = clock.get_fps()
                fps = 6 if fps == 1 else 1
                clock.set_fps(fps)
                self.show3(f"{clock.fps} fps")
            elif key == KeyboardKey.KEY_H:
                hdmi_toggle(self.df)
            elif key == KeyboardKey.KEY_S:
                df.publish_state()
            elif key == KeyboardKey.KEY_P:
                df.power_down()
            elif key == KeyboardKey.KEY_R:
                df.reboot()
            elif key == KeyboardKey.KEY_E:
                df.close()
            elif key == KeyboardKey.KEY_ZERO:
                self.inc_value = 20
                self.show3(f"increment: {self.inc_value}")
            elif key >= KeyboardKey.KEY_ONE and key <= KeyboardKey.KEY_NINE:
                self.inc_value = key - 48
                self.show3(f"increment: {self.inc_value}")
            elif key == KeyboardKey.KEY_L:
                msg = df.get_debug_msg()
                logger.info(f"{msg}, display={df.display}, pause={df.paused}")

        elif key == self.key_kb_menu:
            if self.menu.is_active:
                self.menu.is_active = False
                self.df.set_paused(False)
                clock.pop_set_fps()
            else:
                self.menu.is_active = True
                self.df.set_paused(True)
                clock.push_set_fps(6)

        elif key == KeyboardKey.KEY_F1:
            self.show(self.help, 3, 3, tint=self.help_color, fs=-24, shadow=2, ttl=24)

        elif key == KeyboardKey.KEY_F2:
            df.show_remote_help = not df.show_remote_help

        elif key == KeyboardKey.KEY_F3:
            df.paused = not df.paused
            if df.paused:
                self.text_pause = self.show4("pause", ttl=sys.maxsize)
            else:
                df.dttls.remove(self.text_pause)
                self.show4("pause off")

        elif key == KeyboardKey.KEY_F4:
            df.items.set_prev()
            if df.item: df.item.skip()
            self.show3(f"previous")

        elif key == KeyboardKey.KEY_F5:
            df.items.set_next()
            if df.item: df.item.skip()
            self.show3("next")

        elif key == KeyboardKey.KEY_F6:
            df.items.private = not df.items.private
            self.show3(f"private {'on' if df.items.private else 'off'}")

        elif key == KeyboardKey.KEY_F7: #sleep
            self.autosleep = df.hdmi_off_timeout
            df.hdmi_off_timeout = 0.0
            df.motion_enabled = False
            df.display_set_off()

        elif key == KeyboardKey.KEY_F8:
            df.hdmi_off_timeout = self.autosleep
            df.set_motion(77.7)
            df.motion_enabled = True
            #df.display_set_on()
            self.show3("wakeup")

        elif key == KeyboardKey.KEY_F9:
            self.set_folder(self.dir_list_index)
            self.dir_list_index = (self.dir_list_index + 1) % len(self.dir_list)

        elif key == KeyboardKey.KEY_F10:
            self.set_folder(self.dir_list_index)
            self.dir_list_index =  (self.dir_list_index - 1) % len(self.dir_list)

        elif key == KeyboardKey.KEY_F11:
            df.fullscreen = not df.fullscreen
            df.toggle_window_size()

        elif key == KeyboardKey.KEY_L:
            df.ambient_light = not df.ambient_light
            self.show3(f"ambient light: {'on' if df.ambient_light else 'off'}", ttl=2)

        elif key == KeyboardKey.KEY_K:
            self.set_lux_adj(1)

        elif key == KeyboardKey.KEY_J:
            self.set_lux_adj(-1)

        elif key == KeyboardKey.KEY_P:
            self.set_lux(1)

        elif key == KeyboardKey.KEY_O:
            self.set_lux(-1)

        elif key == KeyboardKey.KEY_Y:
            self.set_direction(1)

        elif key == KeyboardKey.KEY_T:
            self.set_direction(-1)

        elif key == KeyboardKey.KEY_B:
            self.set_border(self.cur_border)
            self.cur_border = (self.cur_border + 1) % len(self.borders)

        elif key == KeyboardKey.KEY_M:
            i = self.cur_matte
            self.set_matte(self.cur_matte)
            self.cur_matte = (self.cur_matte + 1) % len(self.mattes)

        elif key == KeyboardKey.KEY_R:
            self.ttl, self.autosleep = self.show_mode[self.show_mode_index]
            self.show_mode_index += 1
            if self.show_mode_index >= len(self.show_mode):
                self.show_mode_index = 0
            df.image_ttl = self.ttl
            df.hdmi_off_timeout = self.autosleep
            self.show3(f"show: {self.ttl} sec. - autosleep: {self.autosleep} min.", ttl=5)

        elif key == KeyboardKey.KEY_C:
            df.timer = not df.timer

        elif key == KeyboardKey.KEY_ZERO:
            df.items.set_show_text("title", "OFF")
            df.items.set_show_text("caption", "OFF")
            df.items.set_show_text("name", "OFF")
            df.items.set_show_text("date", "OFF")
            df.items.set_show_text("location", "OFF")
            df.items.set_show_text("directory", "OFF")

        elif key == KeyboardKey.KEY_ONE:
            df.items.not_show_text("title")

        elif key == KeyboardKey.KEY_TWO:
            df.items.not_show_text("caption")

        elif key == KeyboardKey.KEY_THREE:
            df.items.not_show_text("name")

        elif key == KeyboardKey.KEY_FOUR:
            df.items.not_show_text("date")

        elif key == KeyboardKey.KEY_FIVE:
            df.items.not_show_text("location")

        elif key == KeyboardKey.KEY_SIX:
            df.items.not_show_text("directory")

        elif key == KeyboardKey.KEY_S:
            df.items.shuffle = not df.items.shuffle
            self.show3(f"shuffle {'on' if df.items.shuffle else 'off'}")
            df.items.set_shuffle(df.items.shuffle)

    # menu update functions
    def set_folder(self, index):
        df = self.df
        logger.info(f"{index=}, folder={self.dir_list[index]}")
        df.items.set_subfolder(self.dir_list[index])
        self.show3(df.items.subfolder)
        if df.item: df.item.skip()

    def set_border(self, index):
        for k, v in self.borders[index].items():
            Config.set(f'items.types.image.border.{k}', v)
        self.show3(f"border: {self.borders[index]}", ttl=2)

    def set_matte(self, index):
        for k, v in self.mattes[index].items():
            Config.set(f'items.types.image.matte.{k}', v)
        self.show3(f"texture: {self.mattes[index]}", ttl=3)

    def set_ttl(self, increment):
        df = self.df
        df.image_ttl += increment  # in seconds
        df.image_ttl = max(0, min(df.image_ttl, 300))
        Config.set('items.types.image.ttl', df.image_ttl)

    def set_sleep(self, increment):
        df = self.df
        df.hdmi_off_timeout += increment  # in minutes
        df.hdmi_off_timeout = max(0, min(df.hdmi_off_timeout, 60))
        Config.set('window.hdmi_off_timeout', df.hdmi_off_timeout)

    def set_increment(self, increment):
        self.inc_value += increment
        self.inc_value = max(0, min(self.inc_value, 50))

    def set_lux_adj(self, sign):
        self.df.set_lux_adj(sign*self.inc_value)
        self.show3(f"lux adjustement value: {self.df.lux_adj}", ttl=2)

    def set_lux(self, sign):
        lux = self.df.lux + (sign * self.inc_value)
        if lux < 0: lux = 0
        self.df.set_brightness(lux)
        self.show3(f"lux: {lux}: brightness: {self.df.get_brightness()}")

    def set_direction(self, sign):
        ld = self.df.shader.config_get('uDirection')
        if ld != None:
            ld = (ld + (sign * self.inc_value)) % 360
            self.show3(f"light direction {ld}")
            self.df.shader.config_set('uDirection', ld)

    def set_monitor_brightness(self, sign):
        value = ("+" if sign > 0 else "-") + str(self.inc_value * abs(sign))
        ddcutil.set_vcp_value(ddcutil.BRIGHTNESS, value)
        time.sleep(0.5)
        self.show3(f"brightness: {ddcutil.get_vcp_value(ddcutil.BRIGHTNESS)}")

    def set_monitor_contrast(self, sign):
        value = ("+" if sign > 0 else "-") + str(self.inc_value * abs(sign))
        ddcutil.set_vcp_value(ddcutil.CONTRAST, value)
        time.sleep(0.5)
        self.show3(f"brightness: {ddcutil.get_vcp_value(ddcutil.CONTRAST)}")

    def set_voice_threshold(self, increment):
        vt = Config.get('voice.threshold', 70) + increment
        vt = max(0, min(vt, 100))
        Config.set('voice.threshold', vt)

    def load_help(self):
        with open(os.path.join(Config.RESOURCES_HELP, "help.txt"), "r") as f:
            help = f.read()
        return help

class ControlMode(StrEnum):
    DIGITALFRAME = "Digitalframe"
    MONITOR = "Monitor"
    REMOTE = "Menu D-Pad"

    @classmethod
    def get_next(cls, current):
        members = list(cls)
        next_idx = (members.index(current) + 1) % len(members)
        return members[next_idx]

class BoxPutRemote():
    def __init__(self, controller, device):
        self.df = controller
        self.device = device
        self.boxput = None
        self.wait_time = Config.get('boxput.wait_time', 10)
        self.mode = ControlMode.REMOTE
        self.first_key_hold = True
        self.actual_dir, self.dir_list = controller.items.get_folders()
        logger.debug(f"{self.actual_dir=} {self.dir_list=}")
        self.dir_list_index = 0
        self.show_mode = Config.get('items.types.image.show_times', [(60.0, 30.0), (10.0, 60.0), (60.0, 60.0), (15.0, 5.0), (60.0, 10.0)]) #ttl, autosleep
        self.show_mode_index = 0
        self.time_delay, self.autosleep = self.show_mode[0]
        self.status = ""
        self.text_pause = None
        self.show = self.df.dttls.show4
        self.boxput_thread = threading.Thread(target=self.handle_boxput)
        self.boxput_thread.daemon = True
        self.boxput_thread.start()

    def get_mode(self):
        return self.mode

    def handle_boxput(self):
        import evdev
        df = self.df
        while True:
            self.boxput = None
            try:
                devices = evdev.list_devices("/dev/input")
                for path in devices:
                    device = evdev.InputDevice(path)
                    logger.debug(f"{device.path=} {device.name=}")
                    if "BOXPUT | BPR1S Keyboard" in device.name:
                        logger.debug(f"{device.path=} {device.name=} {device.phys=}")
                        self.boxput = device
                        break

                if self.boxput:
                    logger.debug(f"BoxPut event read loop started")
                    self.status = "running"
                    for event in self.boxput.read_loop():
                        if event.type == evdev.ecodes.EV_KEY:
                            key_event = evdev.categorize(event)
                            #logger.debug(f"{key_event.keystate} {key_event.scancode} {key_event.keycode}")
                            if key_event.keystate == key_event.key_down:
                                logger.debug(f"key_down {evdev.ecodes.KEY[key_event.scancode]}")
                                # set BoxPut control mode
                                if key_event.scancode == evdev.ecodes.KEY_COMPOSE:
                                    if self.mode == ControlMode.REMOTE:
                                        #self.device.keyboard(self.key_kb_menu)  #already from keyboard
                                        pass
                                    else:
                                        df.show_remote_help = not df.show_remote_help
                                        set_window_focused()

                                # change boxput mode
                                elif key_event.scancode == evdev.ecodes.KEY_HOMEPAGE:
                                    self.mode = ControlMode.get_next(self.mode)
                                    self.show(f"mode: {self.mode.value}")
                                    set_window_focused()

                                # sleep / wakeup
                                elif key_event.scancode == evdev.ecodes.KEY_SEARCH:
                                    if df.motion_enabled:
                                        self.show("sleep")
                                        df.motion_enabled = False
                                        df.hdmi_off_timeout = 0.0
                                        df.display_set_off()
                                    else:
                                        df.hdmi_off_timeout = self.autosleep
                                        df.motion_enabled = True
                                        df.set_motion(88.8)
                                        #df.display_set_on()
                                        self.show("wakeup")

                                # pause
                                elif key_event.scancode == evdev.ecodes.KEY_SELECT:
                                    if self.mode == ControlMode.REMOTE:
                                        self.device.keyboard(KeyboardKey.KEY_ENTER)
                                    elif self.mode == ControlMode.DIGITALFRAME:
                                        df.paused = not df.paused
                                        if df.paused:
                                            self.text_pause = self.show("pause", ttl=sys.maxsize)
                                        else:
                                            df.dttls.remove(self.text_pause)
                                    else:
                                        self.show("set focus")
                                        set_window_focused()

                                # directory up
                                elif key_event.scancode == evdev.ecodes.KEY_UP:
                                    if self.mode == ControlMode.REMOTE:
                                        #self.device.keyboard(KeyboardKey.KEY_UP) #already from keyboard
                                        pass
                                    else:
                                        df.items.set_subfolder(self.dir_list[self.dir_list_index])
                                        self.show(df.items.subfolder)
                                        if df.item: df.item.skip()
                                        self.dir_list_index += 1
                                        if self.dir_list_index >= len(self.dir_list):
                                            self.dir_list_index = 0

                                # directory down
                                elif key_event.scancode == evdev.ecodes.KEY_DOWN:
                                    if self.mode == ControlMode.REMOTE:
                                        #self.device.keyboard(KeyboardKey.KEY_DOWN) #already from keyboard
                                        pass
                                    else:
                                        df.items.set_subfolder(self.dir_list[self.dir_list_index])
                                        self.show(df.items.subfolder)
                                        if df.item: df.item.skip()
                                        self.dir_list_index -= 1
                                        if self.dir_list_index < 0:
                                            self.dir_list_index = len(self.dir_list) - 1

                                # back
                                elif key_event.scancode == evdev.ecodes.KEY_LEFT:
                                    if self.mode == ControlMode.REMOTE:
                                        #self.device.keyboard(KeyboardKey.KEY_LEFT) #already from keyboard
                                        pass
                                    else:
                                        self.show("previous")
                                        df.items.set_prev()
                                        if df.item: df.item.skip()

                                # next
                                elif key_event.scancode == evdev.ecodes.KEY_RIGHT:
                                    if self.mode == ControlMode.REMOTE:
                                        #self.device.keyboard(KeyboardKey.KEY_RIGHT) #already from keyboard
                                        pass
                                    else:
                                        self.show("next")
                                        df.items.set_next()
                                        if df.item: df.item.skip()

                                # backspace
                                elif key_event.scancode == evdev.ecodes.KEY_BACKSPACE:
                                    self.device.keyboard(KeyboardKey.KEY_BACKSPACE)

                                # unused
                                elif key_event.scancode == evdev.ecodes.KEY_VOLUMEUP:
                                    pass

                                # unused
                                elif key_event.scancode == evdev.ecodes.KEY_VOLUMEDOWN:
                                    pass

                                # unused
                                elif key_event.scancode == evdev.ecodes.KEY_MUTE:
                                    pass

                                # key back
                                elif key_event.scancode == evdev.ecodes.KEY_BACK:
                                    self.device.keyboard(KeyboardKey.KEY_BACK)

                            elif key_event.keystate == key_event.key_hold:
                                if self.first_key_hold:
                                    logger.info(f"key_hold {evdev.ecodes.KEY[key_event.scancode]}")
                                self.first_key_hold = False
                                # brightness up
                                if key_event.scancode == evdev.ecodes.KEY_VOLUMEUP:
                                    if self.mode == ControlMode.DIGITALFRAME:
                                        self.set_digitalframe_brightness(10)
                                    else:
                                        self.set_monitor_brightness("+10")

                                # brightness down
                                elif key_event.scancode == evdev.ecodes.KEY_VOLUMEDOWN:
                                    if self.mode == ControlMode.DIGITALFRAME:
                                        self.set_digitalframe_brightness(-10)
                                    else:
                                        self.set_monitor_brightness("-10")

                            elif key_event.keystate == key_event.key_up:
                                logger.debug(f"key_up {evdev.ecodes.KEY[key_event.scancode]}")
                                self.first_key_hold = True

                time.sleep(self.wait_time)
            except OSError as e0:
                logger.debug(e0)
                pass
            except Exception as e1:
                logger.exception(e1)

    def set_digitalframe_brightness(self, value):
        b = self.df.brightness
        b += value
        if b > 128 or b < -128:
            b = 0
        self.df.brightness = b
        self.show(f"brightness: {b}")

    def set_monitor_brightness(self, value):
        ddcutil.set_vcp_value(ddcutil.BRIGHTNESS, value)
        self.show(f"brightness: {ddcutil.get_vcp_value(ddcutil.BRIGHTNESS)}")

    def stop(self):
        try:
            self.status = "stopped"
            logger.info(f"BoxPut {self.status}")
            #self.boxput_thread.join()
        except Exception as e:
            logger.error(e)

class Cron():
    def __init__(self, controller):
        self.df = controller
        self.cron_thread = threading.Thread(target=self.handle_cron, daemon=True)
        self.cron_thread.start()
        self.keyboard = True
        self.status = ""

    def pong(self):
        if self.df.platform != "windows":
            result = subprocess.run(["ls", "/dev/input/by-id/"], capture_output=True, text=True)
            ret = result.stdout.find("-event-kbd")
            self.keyboard = ret != -1
        logger.debug(f"i'm alive...")

    def shuffle(self):
        if self.df.items.shuffle:
            self.df.items.set_shuffle(True)
            logger.info(f"Shuffle done.")

    def cloud_sync(self):
        from csync import run_cloud_sync
        run_cloud_sync(Config.config_file)

    def handle_cron(self):
        import schedule
        schedule.every(1).hours.do(self.pong)
        schedule.every(1).hours.do(self.cloud_sync)
        schedule.every().day.at("06:00").do(self.shuffle)
        logger.info(f"Created Cron: {schedule.get_jobs()}")
        self.pong()
        while True:
            schedule.run_pending()
            time.sleep(3600)

