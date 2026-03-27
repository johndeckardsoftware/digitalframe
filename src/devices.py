import logging
import subprocess
import threading
import sys, time, os

import clock
from pyray import *
from config import Config
import utils.ddcutil as ddcutil
from utils.metrics import system_metrics, get_cpu_temp
from utils.display import hdmi_toogle

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

class Devices:
    def __init__(self, digitalframe):
        self.df = digitalframe
        if Config.get('pir.enabled', False):
            self.pir_sensor = PIRSensor(digitalframe)
        else:
            self.pir_sensor = None
        if Config.get('bluedot.enabled', False):
            self.bluedot = BlueDotRemote(digitalframe)
        else:
            self.bluedot = None
        if Config.get('boxput.enabled', False):
            self.boxput = BoxPutRemote(digitalframe)
        else:
            self.boxput = None
        if Config.get('fan.enabled', False):
            from gpiozero import MotionSensor
            self.fan_controller = FanController(digitalframe)
        else:
            self.fan_controller = None

        # map key text to key code
        self.key_map = {name: value for name, value in vars(KeyboardKey).items() if name.startswith("KEY_")}

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
        self.help_color=Config.get('window.help_color', (255,255,255,255))
        self.metrics_color=Config.get('window.metrics_color', (255,255,255,255))
        self.show = self.df.dttls.show
        self.show3 = self.df.dttls.show3
        self.show4 = self.df.dttls.show4

    def stop(self) -> None:
        if self.pir_sensor:
            self.pir_sensor.stop()
        if self.bluedot:
            self.bluedot.stop()
        if self.boxput:
            self.boxput.stop()
        if self.fan_controller:
            self.fan_controller.stop()

    def vkeyboard(self, key_name):
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
        if vkey:
            key = vkey
        else:
            key = get_key_pressed()
        if not key:
            return

        elif (is_key_down(KeyboardKey.KEY_LEFT_CONTROL) or is_key_down(KeyboardKey.KEY_RIGHT_CONTROL) or vctrl):
            if key == KeyboardKey.KEY_M:
                metrics = system_metrics()
                self.show(metrics, 10, 20, tint=self.metrics_color, fs=36, shadow=2, ttl=30)
            elif key == KeyboardKey.KEY_D:
                self.df.show_debug = not self.df.show_debug
            elif key == KeyboardKey.KEY_Q:
                f = self.df.items.filter if self.df.items.filter != "" else "none"
                self.show3(f"filter: {f}")
            elif key == KeyboardKey.KEY_F:
                self.df.show_fps = not self.df.show_fps
            elif key == KeyboardKey.KEY_G:
                fps = clock.get_fps()
                fps = 6 if fps == 1 else 1
                clock.set_fps(fps)
                self.show3(f"{clock.fps} fps")
            elif key == KeyboardKey.KEY_H:
                hdmi_toogle(self.df)
            elif key == KeyboardKey.KEY_S:
                self.df.publish_state()
            elif key == KeyboardKey.KEY_P:
                self.df.power_down()
            elif key == KeyboardKey.KEY_R:
                self.df.reboot()
            elif key == KeyboardKey.KEY_E:
                self.df.close()
            elif key == KeyboardKey.KEY_ZERO:
                self.inc_value = 20
                self.show3(f"increment: {self.inc_value}")
            elif key >= KeyboardKey.KEY_ONE and key <= KeyboardKey.KEY_NINE:
                self.inc_value = key - 48
                self.show3(f"increment: {self.inc_value}")

        elif key == KeyboardKey.KEY_F1:
            self.show(self.help, 3, 3, tint=self.help_color, fs=-28, shadow=2, ttl=24)

        elif key == KeyboardKey.KEY_F2:
            self.df.show_remote_help = not self.df.show_remote_help

        elif key == KeyboardKey.KEY_F3:
            self.df.paused = not self.df.paused
            if self.df.paused:
                self.text_pause = self.show4("pause", ttl=sys.maxsize)
            else:
                self.df.dttls.remove(self.text_pause)
                self.show4("pause off")

        elif key == KeyboardKey.KEY_F4:
            self.df.items.set_prev()
            if self.df.item: self.df.item.skip()
            self.show3(f"previous")

        elif key == KeyboardKey.KEY_F5:
            self.df.items.set_next()
            if self.df.item: self.df.item.skip()
            self.show3("next")

        elif key == KeyboardKey.KEY_F6:
            self.df.items.private = not self.df.items.private
            self.show3(f"private {'on' if self.df.items.private else 'off'}")

        elif key == KeyboardKey.KEY_F7: #sleep
            self.df.display_set_off()
            self.autosleep = self.df.hdmi_off_timeout
            self.df.hdmi_off_timeout = 0.0
            self.df.motion_enabled = False

        elif key == KeyboardKey.KEY_F8:
            self.df.display_set_on()
            self.df.hdmi_off_timeout = self.autosleep
            self.df.set_motion(88.8)
            self.df.motion_enabled = True
            self.show3("wakeup")

        elif key == KeyboardKey.KEY_F9:
            self.df.items.set_subfolder(self.dir_list[self.dir_list_index])
            self.show3(self.df.items.subfolder)
            if self.df.item: self.df.item.skip()
            self.dir_list_index = self.dir_list_index + 1 if self.dir_list_index < len(self.dir_list) - 1 else 0

        elif key == KeyboardKey.KEY_F10:
            self.df.items.set_subfolder(self.dir_list[self.dir_list_index])
            self.show3(self.df.items.subfolder)
            if self.df.item: self.df.item.skip()
            self.dir_list_index = self.dir_list_index - 1 if self.dir_list_index > 0 else len(self.dir_list) - 1

        elif key == KeyboardKey.KEY_F11:
            self.df.fullscreen = not self.df.fullscreen
            self.df.toogle_window_size()

        elif key == KeyboardKey.KEY_L:
            self.df.ambient_light = not self.df.ambient_light
            self.show3(f"ambient light: {'on' if self.df.ambient_light else 'off'}", ttl=2)

        elif key == KeyboardKey.KEY_K:
            self.df.set_lux_adj(self.inc_value)
            self.show3(f"lux adjustement value: {self.df.lux_adj}", ttl=2)

        elif key == KeyboardKey.KEY_J:
            self.df.set_lux_adj(-self.inc_value)
            self.show3(f"lux adjustement value: {self.df.lux_adj}", ttl=2)

        elif key == KeyboardKey.KEY_P:
            lux = self.df.lux + self.inc_value
            self.df.set_brightness(lux)
            self.show3(f"lux value: {lux}", ttl=2)

        elif key == KeyboardKey.KEY_O:
            lux = self.df.lux - self.inc_value if self.df.lux > 0 else 0
            self.df.set_brightness(lux)
            self.show3(f"lux value: {lux}", ttl=2)

        elif key == KeyboardKey.KEY_UP:
            if not self.df.ambient_light:
                self.df.brightness = self.df.brightness + 3 if self.df.brightness < 64 else -64
                self.show3(f"brightness {self.df.brightness}")

        elif key == KeyboardKey.KEY_DOWN:
            if not self.df.ambient_light:
                self.df.brightness = self.df.brightness - 3 if self.df.brightness > -64 else 64
                self.show3(f"brightness {self.df.brightness}")

        elif key == KeyboardKey.KEY_LEFT:
            ld = self.df.shader.config_get('uDirection')
            ld = ld + 10 if ld < 360 else 0
            self.show3(f"light direction {ld}")
            self.df.shader.config_set('uDirection', ld)

        elif key == KeyboardKey.KEY_RIGHT:
            ld = self.df.shader.config_get('uDirection')
            ld = ld - 10 if ld > 0 else 360
            self.show3(f"light direction {ld}")
            self.df.shader.config_set('uDirection', ld)

        elif key == KeyboardKey.KEY_B:
            i = self.cur_border
            Config.set('items.types.image.border.file', self.borders[i]['file'])
            Config.set('items.types.image.border.opacity', self.borders[i]['opacity'])
            Config.set('items.types.image.border.thick', self.borders[i]['thick'])
            self.show3(f"border: {self.borders[i]['file']}", ttl=2)
            self.cur_border += 1
            if self.cur_border >= len(self.borders): self.cur_border = 0

        elif key == KeyboardKey.KEY_M:
            i = self.cur_matte
            Config.set('items.types.image.matte.texture', self.mattes[i]['texture'])
            Config.set('items.types.image.matte.opacity', self.mattes[i]['opacity'])
            Config.set('items.types.image.matte.type', self.mattes[i]['type'])
            self.show3(f"texture: {self.mattes[i]['texture']}", ttl=3)
            self.cur_matte += 1
            if self.cur_matte >= len(self.mattes): self.cur_matte = 0

        elif key == KeyboardKey.KEY_T:
            self.ttl, self.autosleep = self.show_mode[self.show_mode_index]
            self.show_mode_index += 1
            if self.show_mode_index >= len(self.show_mode):
                self.show_mode_index = 0
            self.df.image_ttl = self.ttl
            self.df.hdmi_off_timeout = self.autosleep
            self.show3(f"show: {self.ttl} sec. - autosleep: {self.autosleep} min.", ttl=5)

        elif key == KeyboardKey.KEY_C:
            self.df.timer = not self.df.timer

        elif key == KeyboardKey.KEY_ZERO:
            self.df.items.set_show_text("title", "OFF")
            self.df.items.set_show_text("caption", "OFF")
            self.df.items.set_show_text("name", "OFF")
            self.df.items.set_show_text("date", "OFF")
            self.df.items.set_show_text("location", "OFF")
            self.df.items.set_show_text("directory", "OFF")

        elif key == KeyboardKey.KEY_ONE:
            self.df.items.set_show_text("title", "OFF" if self.df.items.text_is_on("title") else "ON")

        elif key == KeyboardKey.KEY_TWO:
            self.df.items.set_show_text("caption", "OFF" if self.df.items.text_is_on("caption") else "ON")

        elif key == KeyboardKey.KEY_THREE:
            self.df.items.set_show_text("name", "OFF" if self.df.items.text_is_on("name") else "ON")

        elif key == KeyboardKey.KEY_FOUR:
            self.df.items.set_show_text("date", "OFF" if self.df.items.text_is_on("date") else "ON")

        elif key == KeyboardKey.KEY_FIVE:
            self.df.items.set_show_text("location", "OFF" if self.df.items.text_is_on("location") else "ON")

        elif key == KeyboardKey.KEY_SIX:
            self.df.items.set_show_text("directory", "OFF" if self.df.items.text_is_on("directory") else "ON")

        elif key == KeyboardKey.KEY_S:
            self.df.items.shuffle = not self.df.items.shuffle
            self.show3(f"shuffle {'on' if self.df.items.shuffle else 'off'}")
            self.df.items.set_shuffle(self.df.items.shuffle)

    def load_help(self):
        with open(os.path.join(Config.RESOURCES, "help.txt"), "r") as f:
            help = f.read()
        return help

class PIRSensor():
    def __init__(self, controller):
        self.df = controller
        self.pir_thread = threading.Thread(target=self.handle_pir_sensor)
        self.pir_thread.start()
        self.pir = None
        self.status = ""

    def handle_pir_sensor(self):
        from gpiozero import MotionSensor
        pin = Config.get('pir.pin', 18)
        queue_len = Config.get('pir.queue_len', 10)
        threshold = Config.get('pir.threshold', 0.5)
        wait_time = Config.get('pir.wait_time', 5)
        hdmi_off_timeout = Config.get('window.hdmi_off_timeout', 5)
        self.pir = MotionSensor(pin=pin, queue_len=queue_len, threshold=threshold)
        self.status = "running"
        logger.debug(f"Created MotionSensor: {self.pir.pin=} {self.pir.queue_len=} {self.pir.threshold=}")

        switch_off_time = time.time() + (hdmi_off_timeout * 60)

        while self.status == "running":
            if self.pir.wait_for_motion(wait_time):
                logger.debug(f"motion detected {self.pir.value}")
                if not self.df.display_on():
                    self.df.display_set_on()
                    logger.debug("hdmi on")
                switch_off_time = time.time() + (hdmi_off_timeout * 60)

            if self.pir.wait_for_no_motion(wait_time):
                logger.debug(f"no motion detected {self.pir.value}")
                if self.df.display_on():
                    if time.time() > switch_off_time:
                        self.df.display_set_off()
                        logger.debug("hdmi off")

        self.pir.close()
        self.status = "stopped"

    def stop(self):
        self.status = "stopping"
        self.pir_thread.join()

class BoxPutRemote():
    CTRL_DIGITALFRAME = 0
    CTRL_MONITOR = 1

    def __init__(self, controller):
        self.df = controller
        self.boxput = None
        self.wait_time = Config.get('boxput.wait_time', 10)
        self.mode = BoxPutRemote.CTRL_DIGITALFRAME
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

    def handle_boxput(self):
        import evdev
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
                                logger.info(f"key_down {evdev.ecodes.KEY[key_event.scancode]}")
                                # set BoxPut control mode
                                if key_event.scancode == evdev.ecodes.KEY_COMPOSE:
                                    self.df.show_remote_help = not self.df.show_remote_help

                                # wakeup
                                elif key_event.scancode == evdev.ecodes.KEY_HOMEPAGE:
                                    self.df.hdmi_off_timeout = self.autosleep
                                    self.df.motion_enabled = True
                                    self.df.set_motion(88.8)
                                    #self.df.display_set_on()
                                    self.show("wakeup")

                                # sleep
                                elif key_event.scancode == evdev.ecodes.KEY_SEARCH:
                                    self.show("sleep")
                                    self.df.motion_enabled = False
                                    self.df.hdmi_off_timeout = 0.0
                                    self.df.display_set_off()

                                # pause
                                elif key_event.scancode == evdev.ecodes.KEY_SELECT:
                                    if self.mode == BoxPutRemote.CTRL_DIGITALFRAME:
                                        self.df.paused = not self.df.paused
                                        if self.df.paused:
                                            self.text_pause = self.show("pause", ttl=sys.maxsize)
                                        else:
                                            self.df.dttls.remove(self.text_pause)
                                    else:
                                        self.show("set focus")
                                        set_window_focused()

                                # directory up
                                elif key_event.scancode == evdev.ecodes.KEY_UP:
                                    self.df.items.set_subfolder(self.dir_list[self.dir_list_index])
                                    self.show(self.df.items.subfolder)
                                    if self.df.item: self.df.item.skip()
                                    self.dir_list_index += 1
                                    if self.dir_list_index >= len(self.dir_list):
                                        self.dir_list_index = 0

                                # directory down
                                elif key_event.scancode == evdev.ecodes.KEY_DOWN:
                                    self.df.items.set_subfolder(self.dir_list[self.dir_list_index])
                                    self.show(self.df.items.subfolder)
                                    if self.df.item: self.df.item.skip()
                                    self.dir_list_index -= 1
                                    if self.dir_list_index < 0:
                                        self.dir_list_index = len(self.dir_list) - 1

                                # back
                                elif key_event.scancode == evdev.ecodes.KEY_LEFT:
                                    self.show("previous")
                                    self.df.items.set_prev()
                                    if self.df.item: self.df.item.skip()

                                # next
                                elif key_event.scancode == evdev.ecodes.KEY_RIGHT:
                                    self.show("next")
                                    self.df.items.set_next()
                                    if self.df.item: self.df.item.skip()

                                # show times
                                elif key_event.scancode == evdev.ecodes.KEY_BACKSPACE:
                                    self.ttl, self.autosleep = self.show_mode[self.show_mode_index]
                                    self.show_mode_index += 1
                                    if self.show_mode_index >= len(self.show_mode):
                                        self.show_mode_index = 0
                                    self.df.image_ttl = self.ttl
                                    self.df.hdmi_off_timeout = self.autosleep
                                    self.show(f"show: {self.ttl} sec. - autosleep: {self.autosleep} min.", ttl=5)

                                # brightness up
                                elif key_event.scancode == evdev.ecodes.KEY_VOLUMEUP:
                                    if self.mode == BoxPutRemote.CTRL_DIGITALFRAME:
                                        self.set_digitalframe_brightness(1)
                                        if self.df.item: self.df.item.processed = False
                                    else:
                                        self.set_monitor_brightness("+1")

                                # brightness down
                                elif key_event.scancode == evdev.ecodes.KEY_VOLUMEDOWN:
                                    if self.mode == BoxPutRemote.CTRL_DIGITALFRAME:
                                        self.set_digitalframe_brightness(-1)
                                        if self.df.item: self.df.item.processed = False
                                    else:
                                        self.set_monitor_brightness("-1")

                                # ambient light
                                elif key_event.scancode == evdev.ecodes.KEY_MUTE:
                                    if self.mode == BoxPutRemote.CTRL_DIGITALFRAME:
                                        self.df.ambient_light = not self.df.ambient_light
                                        self.show(f"ambient light: {'on' if self.df.ambient_light else 'off'}")
                                    else:
                                        self.show(f"key unconfigured")

                                # stop
                                elif key_event.scancode == evdev.ecodes.KEY_BACK:
                                    if self.mode == BoxPutRemote.CTRL_DIGITALFRAME:
                                        self.mode = BoxPutRemote.CTRL_MONITOR
                                    else:
                                        self.mode = BoxPutRemote.CTRL_DIGITALFRAME
                                    self.show(f"mode: {'DIGITALFRAME' if self.mode == BoxPutRemote.CTRL_DIGITALFRAME else 'MONITOR'}")

                            elif key_event.keystate == key_event.key_hold:
                                if self.first_key_hold:
                                    logger.info(f"key_hold {evdev.ecodes.KEY[key_event.scancode]}")
                                self.first_key_hold = False
                                # brightness up
                                if key_event.scancode == evdev.ecodes.KEY_VOLUMEUP:
                                    if self.mode == BoxPutRemote.CTRL_DIGITALFRAME:
                                        self.set_digitalframe_brightness(10)
                                    else:
                                        self.set_monitor_brightness("+10")

                                # brightness down
                                elif key_event.scancode == evdev.ecodes.KEY_VOLUMEDOWN:
                                    if self.mode == BoxPutRemote.CTRL_DIGITALFRAME:
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

class BlueDotRemote():
    def __init__(self, controller):
        self.df = controller
        self.bluedot_thread = threading.Thread(target=self.handle_bluedot)
        self.bluedot_thread.start()
        self.bluedot = None
        self.status = ""
        self.count = 0

    def btn_wakeup(self):
        self.df.set_motion(77.7)

    def btn_sleep(self):
        self.df.set_motion(0.0)

    def btn_back(self):
        self.df.items.set_prev()
        if self.df.item: self.df.item.skip()

    def btn_next(self):
        self.df.items.set_next()
        if self.df.item: self.df.item.skip()

    def btn_pause(self):
        self.df.paused = not self.df.paused

    def btn_pause_moved(self, pos):
        horizontal = ((pos.x + 1) / 2)
        percentage = round(horizontal * 100, 2)
        logger.debug(f"button {pos.col}.{pos.row} {round(pos.distance * 100, 2)} {percentage=}")

    def btn_pause_swiped(self, swipe):
        direction = ""
        if swipe.up:
            direction = "up"
            logger.info(f"swipe up. nmcli radio wifi on...")
            try:
                output = subprocess.run(["sudo", "nmcli", "radio", "wifi", "on"], capture_output=True)
                if output.returncode == 0:
                    logger.error(f"{output.stdout.decode('utf-8')}")
                else:
                    logger.error(f"{output.stderr.decode('utf-8')}")
            except Exception as e:
                logger.error(e)

        elif swipe.down:
            direction = "down"
            logger.info(f"swipe down. nmcli dev up wlan0...")
            # bad idea
            try:
                output = subprocess.run(["sudo", "nmcli", "dev", "up", "wlan0", ], capture_output=True)
                if output.returncode == 0:
                    logger.error(f"{output.stdout.decode('utf-8')}")
                else:
                    logger.error(f"{output.stderr.decode('utf-8')}")
            except Exception as e:
                logger.error(e)

        elif swipe.left:
            logger.info(f"swipe down. nmcli dev down wlan0...")
            # bad idea
            try:
                #output = subprocess.run(["sudo", "nmcli", "con", "down", "FRITZ!Box 7530 FY"], capture_output=True)
                output = subprocess.run(["sudo", "nmcli", "dev", "down", "wlan0"], capture_output=True)
                if output.returncode == 0:
                    logger.error(f"{output.stdout.decode('utf-8')}")
                else:
                    logger.error(f"{output.stderr.decode('utf-8')}")
            except Exception as e:
                logger.error(e)

        elif swipe.right:
            direction = "right"
            logger.info(f"swipe right. close picframe...")
            self.df.close()
        logger.debug(f"button pause swiped {direction=} {swipe.speed=} {swipe.angle=} {swipe.distance=}")

    def btn_pause_rotated(self, rotation):
        self.count += rotation.value
        logger.debug("{} {} {}".format(self.count,
                                rotation.clockwise,
                                rotation.anti_clockwise))

    def on_client_connects(self):
        logger.info(f"BlueDot client connected. {self.bluedot.paired_devices}")

    def on_client_disconnects(self):
        logger.info(f"BlueDot client disconnected.")

    def handle_bluedot(self):
        try:
            from bluedot import BlueDot
            self.bluedot = BlueDot(cols=3, rows=5, print_messages=False)

            # configure dot matrix
            self.bluedot[0, 0].border = True
            self.bluedot[0, 0].color = (0, 255, 0)
            self.bluedot[0, 0].when_pressed = self.btn_wakeup
            self.bluedot[1, 0].visible = False
            self.bluedot[2, 0].border = True
            self.bluedot[2, 0].color = (255, 0, 0)
            self.bluedot[2, 0].when_pressed = self.btn_sleep

            self.bluedot[0, 1].visible = False
            self.bluedot[1, 1].visible = False
            self.bluedot[2, 1].visible = False

            self.bluedot[0, 2].border = True
            self.bluedot[0, 2].color = (128, 128, 128)
            self.bluedot[0, 2].when_pressed = self.btn_back
            self.bluedot[1, 2].visible = False
            self.bluedot[2, 2].border = True
            self.bluedot[2, 2].color = (160, 160, 160)
            self.bluedot[2, 2].when_pressed = self.btn_next

            self.bluedot[0, 3].visible = False
            self.bluedot[1, 3].visible = False
            self.bluedot[2, 3].visible = False

            self.bluedot[0, 4].visible = False
            self.bluedot[1, 4].border = True
            self.bluedot[1, 4].color = (32, 32, 128)
            self.bluedot[1, 4].when_pressed = self.btn_pause
            self.bluedot[1, 4].when_moved = self.btn_pause_moved
            self.bluedot[1, 4].when_swiped = self.btn_pause_swiped
            self.bluedot[1, 4].when_ratated = self.btn_pause_rotated
            self.bluedot[2, 4].visible = False

            self.bluedot.when_client_connects = self.on_client_connects
            self.bluedot.when_client_disconnects = self.on_client_disconnects

            self.status = "running"
            logger.info(f"BlueDot server started")

            while self.status == "running":
                if self.bluedot.wait_for_press(5):
                    pass

            if self.bluedot:
                self.bluedot.stop()
            self.status = "stopped"
            logger.info(f"BlueDot {self.status}")
        except Exception as e:
            logger.error(e)

    def stop(self):
        try:
            self.status = "stopping"
            logger.info(f"BlueDot {self.status}")
            self.bluedot_thread.join()
        except Exception as e:
            logger.error(e)

class FanController():
    def __init__(self, controller):
        self.df = controller
        self.fan_thread = threading.Thread(target=self.handle_fan)
        self.fan_thread.start()
        self.fan_device = None
        self.status = ""
        self.count = 0

    def handle_fan(self):
        from utils.metrics import get_cpu_temp
        try:
            from gpiozero import OutputDevice
            pin = Config.get('fan.pin', 14)
            trigger = Config.get('fan.trigger', 50)
            sleep = Config.get('fan.sleep', 60)
            self.fan_device = OutputDevice(pin=pin)
            self.status = "running"
            logger.info(f"Fan controller started")

            while self.status == "running":
                temp = get_cpu_temp()
                if temp > trigger:
                    self.fan_device.on()
                else:
                    self.fan_device.off()
                time.sleep(sleep)

            if self.fan_device:
                self.fan_device.close()
            self.status = "stopped"
            logger.info(f"Fan controller {self.status}")
        except Exception as e:
            logger.error(e)

    def stop(self):
        try:
            self.status = "stopping"
            logger.info(f"Fan controller {self.status}")
            self.fan_thread.join()
        except Exception as e:
            logger.error(e)
