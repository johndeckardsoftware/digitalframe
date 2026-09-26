import os, json, logging, ast
from pyray import *
from text_to_num import text2num
import clock
from config import Config
from config import config_setup # used menu_xx.json
from osk import OnScreenKeyboard
from color_picker import ColorPicker
from dftext import dftext
import utils.ddcutil as ddcutil # used in exec

"""
MENU ITEM CONFIGURATION KEYS:
--------------------------------------------------------------------------------
Key    Description
--------------------------------------------------------------------------------
t     : Static Display Text
        String shown directly in the menu item.
        Example: {"t": "Previous"}

g     : Dynamic Display Text (Evaluated Python Expression)
        String expression evaluated dynamically each frame to generate item label text.
        Example: {"g": "f'Pause ({self.on_off(self.df.paused)})'"}

e     : Spinbox / Value Evaluator Display Text
        String expression evaluated to format and render interactive numeric/spinbox items.
        Example: {"e": "f'Display time < {self.df.image_ttl} > sec.'"}

f     : Action Callback (Executed Python Code)
        Python code evaluated/executed when the item is activated (ENTER button or voice selection).
        Example: {"f": "self.devices.set_video_sound()"}

k     : Keyboard Shortcut / Virtual Input Action
        Simulates a keypress or shortcut command via virtual input devices when activated.
        Example: {"k": "KEY_F4"} or {"k": "CTRL+KEY_D"}

m     : Static Navigation Submenu Target
        Submenu name identifier to switch to upon pressing ENTER.
        Example: {"m": "light"}

fm    : Dynamic Navigation Submenu Target
        Python function/expression evaluated on selection that returns the target menu key name.
        Example: {"fm": "self.menu_border()"}

fl    : Spinbox Decrement Callback (LEFT Arrow)
        Python expression executed when pressing LEFT while editing a spinbox item ('e').
        Example: {"fl": "self.devices.set_ttl(-10)"}

fr    : Spinbox Increment Callback (RIGHT Arrow)
        Python expression executed when pressing RIGHT while editing a spinbox item ('e').
        Example: {"fr": "self.devices.set_ttl(10)"}

fv    : Spinbox Direct Voice Input Callback
        Python expression executed when setting a spinbox value directly via voice commands.
        Example: {"fv": "self.devices.set_ttl(self.number, delta=False)"}

back  : Navigation Flag
        Boolean flag (`true`/`false`). When `true`, indicates a navigation back/exit button.
        Example: {"t": "Back", "back": true, "m": "menu"}

d     : Default Value for Virtual Keyboard / Color Picker
        Evaluated Python expression providing initial string or RGBA state to inputs.
        Example: {"d": "f'{self.df.items.get_filter()}'"}

vk    : Full Virtual Keyboard Input Trigger
        Boolean (`true`). Opens full On-Screen Keyboard (OSK) for text editing.
        Example: {"t": "Edit Filter", "vk": true}

np    : Numpad Virtual Keyboard Trigger
        Boolean (`true`). Opens numeric On-Screen Keyboard layout for number entry.
        Example: {"np": true}

cp    : Color Picker Trigger
        Boolean (`true`). Opens RGBA Color Picker widget for color adjustment.
        Example: {"cp": true}

_     : Boolean Toggle Trigger
        Used internally in dynamic dictionary menus for boolean toggling.
--------------------------------------------------------------------------------
SPECIAL VOICE ASSISTANT KEYS (for 'voice_action'):
--------------------------------------------------------------------------------
s     : Require Voice Keyword Prefix
        Boolean (`true`/`false`). Requires preceding action phrase or command context.

r     : Regex Pattern Matching Flag
        Boolean (`true`/`false`). Indicates whether command requires regex phrase expansion.
--------------------------------------------------------------------------------
"""

logger = logging.getLogger(__name__)

MENU_DYNAMIC = "dynamic"

class DynamicMenuState:
    """Holds data for a single dynamic menu layer."""
    def __init__(self, name: str):
        self.name: str = name
        self.list: list | None = None
        self.dict: dict | None = None
        self.entered: dict | None = None
        self.help: str | None = None
        self.ktree: dict[str, list[str]] | None = None

class MenuDynamic:
    """Manager class controlling all dynamic menu states and instances."""
    def __init__(self):
        self._instances: dict[str, DynamicMenuState] = {}
        self.active_name: str = MENU_DYNAMIC
        # Always create default dynamic instance
        self.get_instance(MENU_DYNAMIC)

    def get_instance(self, name: str) -> DynamicMenuState:
        if name not in self._instances:
            self._instances[name] = DynamicMenuState(name)
        return self._instances[name]

    @property
    def current(self) -> DynamicMenuState:
        """Returns the currently active dynamic menu state."""
        return self.get_instance(self.active_name)

    def set_active(self, name: str = MENU_DYNAMIC) -> DynamicMenuState:
        self.active_name = name
        return self.get_instance(name)

    def set_current(self, name: str = MENU_DYNAMIC) -> DynamicMenuState:
        if name in self._instances:
            self.active_name = name
            return True
        else:
            return False

class OnScreenMenu:
    def __init__(self, digitalframe, devices):
        #logger.setLevel(logging.DEBUG)
        self.df = digitalframe
        self.devices = devices
        # VoiceAssistant class instance (set by digitalframe)
        self.va = None
        # voice assistant support
        self.number = 0
        # virtual input devices
        self.osk = OnScreenKeyboard(self)
        self.is_osk = False
        self.in_osk = False
        self.color_picker = ColorPicker(digitalframe)
        self.is_color_picker = False
        self.in_color_picker = False
        # Style
        self.set_style_size(self.df.scale)
        # Menus state
        self.conf = Config #trick for config autogeneration
        self.lang = Config.get("voice.lang", "en")
        self.menus = self.load_menus()
        self.current = "menu"
        self.options = self.menus['menu']
        self.selected = 0
        self.option = self.set_option()
        self.is_dynamic = False
        self.is_active = False
        self.in_action = False
        self.is_spinbox = False
        self.in_spinbox = False
        # menu dynamic
        self.config_ktree = Config.get_key_tree()
        self.dynamic = MenuDynamic()
        self.dynamic.current.list = None
        self.dynamic.current.dict = None
        self.dynamic.current.entered = None
        self.dynamic.current.help = None
        self.dynamic.current.ktree = None
        # shortcut
        self.show = self.df.dttls.show
        self.show3 = self.df.dttls.show3
        self.show4 = self.df.dttls.show4

    def set_style_size(self, scale):
        self.text_h = int(40 * scale)
        self.text_b = int(10 * scale)
        self.back_h = int(40 * scale)
        self.back_b = int(5 * scale)
        self.font_h = 28 * scale

    def load_menus(self):
        with open(os.path.join(Config.RESOURCES_MENU, Config.get('window.menu.menus', "menus_en.json")), "r", encoding="UTF-8") as f:
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

    def set_menu(self, menu):
        self.current = menu
        self.is_dynamic = self.dynamic.set_current(menu)
        self.options = self.menus[menu]
        self.selected = self.menus[f"{menu}_sel"]
        self.option = self.set_option()

    def set_option(self):
        option = self.options[self.selected]
        self.is_spinbox = 'e' in option
        self.in_spinbox = False
        self.is_osk = 'vk' in option or 'np' in option
        self.in_osk = False
        self.is_color_picker = 'cp' in option
        self.in_color_picker = False
        if self.is_osk:
            self.osk.load_layout(type="osk_full" if 'vk' in option else "osk_numpad")
        return option

    # load a dynamic menu from a string array
    def create_menu_from_list(self, values, default="", f=None, fm=None, back="menu", name="dynamic"):
        self.dynamic.set_active(name)
        self.dynamic.current.list = self.conf.get(values, []) if isinstance(values, str) else values
        lmo = []
        for item in self.dynamic.current.list:
            option = {"t": f"{item}", "f": f"self.set_dynamic_text(self.selected, {f})"}
            if fm: option['fm'] = fm
            lmo.append(option)
            if item == default:
                self.dynamic.current.entered = option
        lmo.append({"t": "Back", "back": True, "m": back})
        self.menus[name] = lmo
        self.menus[f"{name}_sel"] = 0
        return ""

    # load a dynamic menu from a dictionary
    def create_menu_from_dict(self, values, default="", f=None, back="menu", conf_key=None, key=None, name="dynamic"):
        self.dynamic.set_active(name)
        self.dynamic.current.dict = self.conf.get(values, {}) if isinstance(values, str) else values
        lmo = []
        self.menus[f"{name}_help"] = ""
        self.dynamic.current.help = None
        for k, v in self.dynamic.current.dict.items():
            if k == "help":
                self.menus[f"{name}_help"] = v
                self.dynamic.current.help = v
            else:
                input, output = self.get_in_out(k, v)
                option = {"g": self.get_dynamic_fkv(k), input: True, "d": self.get_dynamic_fv(k),
                          "f": f"self.set_dynamic_kv('{k}', '{output}', '{f}')"}
                lmo.append(option)
                if k == default:
                    self.dynamic.current.entered = option
        if conf_key:
            lmo.append({"t": "Save", "f": f"self.save('{conf_key}', '{key}', self.dynamic.current.dict)"})
        lmo.append({"t": "Back", "back": True, "m": back})
        self.menus[name] = lmo
        self.menus[f"{name}_sel"] = 0
        return ""

    def set_dynamic_text(self, index, f=None):
        name = self.dynamic.current.name
        self.dynamic.current.entered = self.menus[name][index]
        self.menus[f"{name}_text"] = self.menus[name][index]['t']
        if f: exec(f)

    def get_dynamic_text(self):
        return self.menus[f"{self.dynamic.current.name}_text"]

    def get_dynamic_fkv(self, k):
        return "f'" + k + " (" + "{self.dynamic.current.dict[\"" + k + "\"]})'"

    def get_dynamic_fv(self, k):
        return "f'{self.dynamic.current.dict[\"" + k + "\"]}'"

    def set_dynamic_kv(self, k, fv, f):
        v = self.try_eval(fv)
        if isinstance(v, str):
            try:
                v = ast.literal_eval(v)
            except (ValueError, SyntaxError):
                pass
        self.dynamic.current.dict[k] = v
        if f:
            try:
                exec(f)
            except:
                logger.error(f"{k=}, {fv=} {f=}")
                return
        self.dynamic.current.entered = self.menus[self.current][self.selected]

    def get_in_out(self, key, value):
        # Parse string representation if necessary
        if isinstance(value, str):
            try:
                value = ast.literal_eval(value)
            except:
                pass

        # 1. Color Picker check (tuples/lists of 3 or 4 RGB(A) ints 0-255)
        if isinstance(value, (list, tuple)) and len(value) in (3, 4):
            if all(isinstance(x, int) and 0 <= x <= 255 for x in value):
                return "cp", "self.color_picker.get_rgba()"

        # 2. Boolean check
        if isinstance(value, bool):
            return "_", f"not self.dynamic.current.dict[\"{key}\"]"

        # 3. Numeric check (integers or floats)
        if type(value) in (int, float):
            return "np", "self.osk.typed_text"

        return "vk", "self.osk.typed_text"

    def save(self, conf_key, key, new_value):
        cur_value = self.conf.get(conf_key, None)
        if cur_value is not None:
            if isinstance(cur_value, list):
                if key and key != "None":
                    found = False
                    for i, item in enumerate(cur_value):
                        # Match item by key identifier (e.g., item['file'] == id)
                        if isinstance(item, dict) and item.get(key) == new_value.get(key):
                            cur_value[i] = new_value  # Update element directly in list
                            found = True
                            break

                    if found:
                        Config.set(conf_key, cur_value)
                        Config.save()  # Write back to config.json
                    else:
                        self.show3(f"{key=} not found", ttl=3)
                else:
                    Config.set(conf_key, next(iter(new_value.values())))
                    Config.save()

            elif isinstance(cur_value, dict):
                Config.set(conf_key, new_value)
                Config.save()
            else:
                # Handles int, float, str, bool
                v = next(iter(new_value.values()))
                try: v = ast.literal_eval(v)
                except (ValueError, SyntaxError): pass
                Config.set(conf_key, v)
                Config.save()
        else:
            self.show3(f"{conf_key=} not found", ttl=3)

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

            if self.in_color_picker:
                # Update D-pad navigation
                self.in_color_picker = self.color_picker.update_dpad(key)
                if not self.in_color_picker: # Picker closed
                    if "f" in self.option:
                        exec(self.option['f'])
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
                    self.dynamic.current.help = None
                    return

                if self.is_spinbox:
                    self.in_spinbox = True
                    return

                if self.is_osk:
                    self.in_osk = True
                    if 'd' in self.option:
                        self.osk.set_typed_text(eval(self.option['d']))
                    return

                if self.is_color_picker:
                    self.in_color_picker = True
                    if 'd' in self.option:
                        self.color_picker.set_rgba(eval(self.option['d']))
                    return

                self.in_action = True
                if "f" in self.option:
                    exec(self.option['f'])
                elif "k" in self.option:
                    self.devices.send_keys(self.option['k'])
                self.in_action = False

                if menu := self.option.get('fm', None):
                    self.set_menu(self.try_eval(menu))
                    return

            elif key in (KeyboardKey.KEY_BACK, KeyboardKey.KEY_BACKSPACE):
                self.set_menu(self.options[len(self.options) - 1].get('m', "menu"))
                self.dynamic.current.help = None
            elif key == KeyboardKey.KEY_END:
                self.set_menu("menu")
                self.dynamic.current.help = None

    def draw(self):
        # Draw a semi-transparent background overlay
        draw_rectangle(0, 0, get_screen_width(), get_screen_height(), fade(BLACK, 0.5))

        # 1. Calculate Maximum Visible Items based on Screen Height
        if self.in_osk: max_visible_items = Config.get('window.menu.osk_max_visible', 6)
        else:           max_visible_items = Config.get('window.menu.max_visible', 24)
        screen_max = (get_screen_height() - int(100 * self.df.scale)) // self.back_h
        if screen_max > 0:
            max_visible_items = min(max_visible_items, screen_max)

        total_items = len(self.options)
        visible_count = min(total_items, max_visible_items)

        # 2. Calculate Scrolling Window Offset
        start_index = 0
        if total_items > visible_count:
            # Keep selected item visible within the sliding window
            if self.selected >= visible_count:
                start_index = self.selected - visible_count + 1
            if start_index + visible_count > total_items:
                start_index = total_items - visible_count

        end_index = start_index + visible_count

        # 3. Dynamic Menu Dimensions
        menu_w = int(self.menus.get(f'{self.current}_width', 800) * self.df.scale)
        menu_h = self.back_h * visible_count + self.back_b * 2
        start_x = (get_screen_width() - menu_w) // 2
        start_y = (get_screen_height() - menu_h) // 2

        # 4. Render Scroll Indicator (Top)
        if start_index > 0:
            draw_text_ex(self.df.font, "▲", (start_x + menu_w - int(30 * self.df.scale), start_y - int(25 * self.df.scale)), self.font_h, 1.0, SKYBLUE)

        # 5. Draw Visible Window of Options
        for visible_i, i in enumerate(range(start_index, end_index)):
            option = self.options[i]
            spinbox = 'e' in option
            if spinbox:
                text = self.try_eval(option['e'])
            elif 'g' in option:
                text = self.try_eval(option['g'])
            else:
                text = option['t']

            color = LIGHTGRAY
            y_pos = start_y + self.back_b + (visible_i * self.back_h)

            if i == self.selected:
                back_color = DARKGREEN if spinbox and self.in_spinbox else SKYBLUE
                text_size = measure_text_ex(self.df.font, text, self.font_h, 1.0)
                draw_rectangle(start_x + self.back_b, y_pos, int(text_size.x) + self.back_b * 2, self.back_h, back_color)
                color = WHITE
            elif self.is_dynamic and self.dynamic.current.entered == option:
                back_color = WHITE
                text_size = measure_text_ex(self.df.font, text, self.font_h, 1.0)
                draw_rectangle(start_x + self.back_b, y_pos, int(text_size.x) + self.back_b * 2, self.back_h, back_color)
                color = SKYBLUE

            draw_text_ex(self.df.font, text, (start_x + self.text_b, y_pos + (self.text_b // 2)), self.font_h, 1.0, color)

        # 6. Render Scroll Indicator (Bottom)
        if end_index < total_items:
            draw_text_ex(self.df.font, "▼", (start_x + menu_w - int(30 * self.df.scale), start_y + menu_h + int(5 * self.df.scale)), self.font_h, 1.0, SKYBLUE)

        if self.dynamic.current.help:
            draw_text_ex(self.df.font, self.dynamic.current.help, (32, 64), int(self.font_h/1.5), 1.0, SKYBLUE)

        if self.in_osk:
            self.osk.draw()

        if self.in_color_picker:
            self.color_picker.update_mouse()
            self.color_picker.draw(font=self.df.font)

        dftext(self.devices.get_status(), -2, -3, font=self.df.font, fs=self.font_h - 2, tint=WHITE, shadow=2)

    #
    # menu helper
    #
    def on_off(self, value):
        return "on" if value else "off"

    def get_piper_enabled(self):
        return self.va.piper_enabled if self.va else False

    def set_piper_voice(self, value=None):
        if self.va:
            self.va.piper_enabled = value if value else not  self.va.piper_enabled
            Config.set('voice.piper.enabled', self.va.piper_enabled)

    def menu_tag(self):
        current = self.df.items.get_filter()
        self.create_menu_from_list("items.recent_filter", default=current, f="self.df.set_tags_filter(self.get_dynamic_text())", back="tag")
        return MENU_DYNAMIC

    def get_tag(self):
        return self.df.items.get_filter()

    def menu_labels(self):
        if self.df.indexer:
            current = self.df.indexer.get_labels()
            self.create_menu_from_list("indexer.recent_labels", default=current, f="self.df.indexer.set_labels(self.get_dynamic_text())", back="indexer")
            return MENU_DYNAMIC
        else:
            return "indexer"

    def get_labels(self):
        if self.df.indexer:
            return self.df.indexer.get_labels()
        else:
            return "tag"

    def menu_border(self):
        key = "file"
        current = Config.get('items.types.image.border', {})
        self.create_menu_from_dict(current, default=current, back="menu", conf_key="items.types.image.borders", key=key)
        return MENU_DYNAMIC

    def menu_matte(self):
        key = "texture"
        current = Config.get('items.types.image.matte', {})
        self.create_menu_from_dict(current, default=current, back="menu", conf_key="items.types.image.mattes", key=key)
        return MENU_DYNAMIC

    def menu_config_keys(self):
        menu = "config_keys"
        self.dynamic.set_active(menu)
        keys = [k for k in self.config_ktree.keys()]
        self.create_menu_from_list(keys, fm="self.menu_config_subkeys(self.get_dynamic_text())", back="debug", name=menu)
        return menu

    def menu_config_subkeys(self, key=None):
        menu = "config_subkeys"
        self.dynamic.set_active(menu)
        if key is None: key = "window"
        subkeys = self.config_ktree.get(key, [])
        self.create_menu_from_list(subkeys, fm="self.menu_config_values(self.get_dynamic_text())", back="config_keys", name=menu)
        return menu

    def menu_config_values(self, key=None):
        menu = "config_values"
        self.dynamic.set_active(menu)
        if key is not None:
            conf_key = f"{self.menus['config_keys_text']}.{key}"
            values = self.conf(conf_key, [])
            if isinstance(values, list):
                temp_dict = {key: f"{values}"}
                self.create_menu_from_dict(temp_dict, conf_key=conf_key, back="config_subkeys", name=menu)
            elif isinstance(values, dict):
                self.create_menu_from_dict(values, conf_key=conf_key, back="config_subkeys", name=menu)
            else:
                temp_dict = {key: values}
                self.create_menu_from_dict(temp_dict, conf_key=conf_key, back="config_subkeys", name=menu)
            return menu
        return "config_keys"

    #
    # voice assistant support functions
    #
    def select(self, text):
        for index, option in enumerate(self.options):
            if "t" in option and option["t"] == text:
                self.selected = index
                return index
        return -1

    def osk_show(self, option=None):
        if option:
            self.option = option
            if "d" in option:
                self.osk.set_typed_text(eval(option['d']))
        else:
            self.option = None
        self.is_osk = True
        self.in_osk = True
        logger.debug(f"{self.is_osk=} {self.in_osk=} {self.osk.typed_text=}")

    def osk_hide(self):
        if self.option:
            if "f" in self.option: exec(self.option['f'])
        self.is_osk = False
        self.in_osk = False

    def osk_clear(self):
        self.osk.set_typed_text("")

    def osk_backspace(self):
        osk = self.osk
        if osk.cursor > 0:
            osk.typed_text = osk.typed_text[:osk.cursor - 1] + osk.typed_text[osk.cursor:]
            osk.cursor -= 1

    def osk_left(self):
        osk = self.osk
        if osk.cursor > 0:
            osk.cursor -= 1

    def osk_right(self):
        osk = self.osk
        if osk.cursor < len(osk.typed_text):
            osk.cursor += 1

    def osk_blank(self):
        self.osk._insert_char(" ")

    def osk_shift(self):
        osk = self.osk
        osk.is_shift = not osk.is_shift
        osk.layout = osk.layouts['shift'] if osk.is_shift else osk.layouts['base']

    def set_number(self, sign, num):
        try:
            self.number = text2num(num, lang=self.lang)
            self.number *= sign
        except Exception as e:
            logger.error(f"{e}")

    def try_eval(self, func):
        try:
            return eval(func)
        except Exception as e:
            logger.error(f"{func=}, {e}")
            return "error"
