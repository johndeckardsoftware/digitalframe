import os, json, logging
import clock
from config import Config
from osk import OnScreenKeyboard
from pyray import *
from dftext import dftext

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

class OnScreenMenu:
    def __init__(self, digitalframe, devices):
        self.df = digitalframe
        self.devices = devices
        # Style
        self.set_style_size(self.df.scale)
        # Menus state
        self.menus = self.load_menus()
        self.current = "menu"
        self.options = self.menus['menu']
        self.selected = 0
        self.option = self.set_option()
        self.is_active = False
        self.in_action = False
        self.is_spinbox = False
        self.in_spinbox = False
        self.osk = OnScreenKeyboard(self)
        self.is_osk = False
        self.in_osk = False

    def set_style_size(self, scale):
        self.text_h = int(40 * scale)
        self.text_b = int(10 * scale)
        self.back_h = int(40 * scale)
        self.back_b = int(5 * scale)
        self.font_h = 28 * scale

    def load_menus(self):
        with open(os.path.join(Config.RESOURCES, "menus.json"), "r") as f:
            menus = json.load(f)

        # add select folders menu
        actual_dir, dir_list = self.df.items.get_folders()
        lmo = []
        for d in dir_list:
            lmo.append({"t": d, "f": "self.devices.set_folder(self.selected)"})
        lmo.append({"t": "Back", "back": True, "m": "menu"})
        menus['folders'] = lmo
        menus['folders_sel'] = 0

        # add select borders menu
        borders = Config.get('items.types.image.borders', [])
        lmo = []
        for b in borders:
            lmo.append({"t": b['file'], "f": "self.devices.set_border(self.selected)"})
        lmo.append({"t": "Back", "back": True, "m": "menu"})
        menus['borders'] = lmo
        menus['borders_sel'] = 0

        # add select mattes menu
        mattes = Config.get('items.types.image.mattes', [])
        lmo = []
        for m in mattes:
            lmo.append({"t": m['texture'], "f": "self.devices.set_matte(self.selected)"})
        lmo.append({"t": "Back", "back": True, "m": "menu"})
        menus['mattes'] = lmo
        menus['mattes_sel'] = 0

        return menus

    def update(self, key):
        #logger.debug(f"{key=}")
        if key == self.devices.key_kb_menu:
            if self.is_active:
                self.is_active = False
                self.df.set_paused(False)
                clock.pop_set_fps()
            return

        if self.is_active:
            if self.in_osk:
                self.in_osk = self.osk.update(key)
                if not self.in_osk: # input ended
                    if "f" in self.option: exec(self.option['f'])
                return

            # D-pad Navigation
            if key == KeyboardKey.KEY_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
                self.option = self.set_option()
            elif key == KeyboardKey.KEY_UP:
                self.selected = (self.selected - 1) % len(self.options)
                self.option = self.set_option()
            elif self.in_spinbox and key == KeyboardKey.KEY_LEFT:
                if "fl" in self.option: exec(self.option['fl'])
            elif self.in_spinbox and key == KeyboardKey.KEY_RIGHT:
                if "fr" in self.option: exec(self.option['fr'])

            # Action (OK Button)
            elif key == KeyboardKey.KEY_ENTER:
                #logger.debug(f"Selected: {self.option}")
                if not self.option.get('back', False):
                    self.menus[f"{self.current}_sel"] = self.selected

                if menu := self.option.get('m', None):
                    self.set_menu(menu)
                    return

                if self.is_spinbox:
                    self.in_spinbox = True
                    return

                if self.is_osk:
                    self.in_osk = True
                    if 'd' in self.option:
                        self.osk.typed_text = eval(self.option['d'])
                    return

                self.in_action = True
                if "f" in self.option:
                    exec(self.option['f'])
                else:
                    self.devices.send_keys(self.option['k'])
                self.in_action = False

            elif key == KeyboardKey.KEY_BACK or key == KeyboardKey.KEY_END:
                self.set_menu("menu")

    def set_menu(self, menu):
        self.current = menu # TODO manage more levels
        self.options = self.menus[menu]
        self.selected = self.menus[f"{menu}_sel"]
        self.option = self.set_option()

    def on_off(self, value):
        return "ON" if value else "OFF"

    def set_option(self):
        option = self.options[self.selected]
        self.is_spinbox = 'e' in option
        self.in_spinbox = False
        self.is_osk = 'vk' in option
        self.in_osk = False
        return option

    def draw(self):
        # Draw a semi-transparent background overlay
        draw_rectangle(0, 0, get_screen_width(), get_screen_height(), fade(BLACK, 0.5))

        # Draw Menu Box
        menu_w, menu_h = 400, self.back_h * len(self.options) + self.back_b * 2
        start_x = (get_screen_width() - menu_w) // 2
        start_y = (get_screen_height() - menu_h) // 2

        #draw_rectangle(start_x, start_y, menu_w, menu_h, RAYWHITE)
        #draw_rectangle_lines(start_x, start_y, menu_w, menu_h, DARKGRAY)

        # Draw Options
        for i, option in enumerate(self.options):
            spinbox = 'e' in option
            if spinbox: text = eval(option['e'])
            elif 'g' in option: text = eval(option['g'])
            else: text = option['t']
            color = LIGHTGRAY
            if i == self.selected:
                back_color = DARKGREEN if spinbox and self.in_spinbox else SKYBLUE
                text_size = (measure_text_ex(self.df.font, text, self.font_h, 1.0))
                draw_rectangle(start_x + self.back_b, start_y + self.back_b + (i * self.back_h), int(text_size.x) + self.back_b*2, self.back_h, back_color)
                color = WHITE

            draw_text_ex(self.df.font, text, (start_x + self.text_b, start_y + self.text_b + (i * self.text_h)), self.font_h, 1.0, color)

        if self.in_osk:
            self.osk.draw()

        dftext(self.devices.get_status(), -2, -3, font=self.df.font, fs=self.font_h-2, tint=WHITE, shadow=2)