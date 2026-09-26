import math, ast
from pyray import *

class ColorPicker:
    """
    Interactive RGBA Color Picker widget for Raylib.
    Supports both Mouse dragging and D-Pad / Keyboard navigation with toggle-focus mode.
    """
    def __init__(self, digitalframe, x=0, y=0):
        self.df = digitalframe
        self.scale = digitalframe.scale
        self.width = int(480 * self.scale)
        self.height = int(320 * self.scale)
        self.x = x
        self.y = y
        if x == 0:
            self.x = (self.df.width - self.width) // 2
        if y == 0:
            self.y = self.df.height - self.height

        # Geometry setup
        self.wheel_radius = int(90 * self.scale)
        self.wheel_center_x = self.x + self.wheel_radius + int(20 * self.scale)
        self.wheel_center_y = self.y + self.wheel_radius + int(20 * self.scale)

        # Slider positions
        self.slider_w = int(24 * self.scale)
        self.slider_h = self.wheel_radius * 2
        self.val_slider_x = self.wheel_center_x + self.wheel_radius + int(30 * self.scale)
        self.alpha_slider_x = self.val_slider_x + self.slider_w + int(20 * self.scale)
        self.slider_y = self.wheel_center_y - self.wheel_radius

        # Color State (HSV + Alpha)
        self.hue = 0.0          # 0.0 - 360.0
        self.saturation = 1.0   # 0.0 - 1.0
        self.value = 1.0        # 0.0 - 1.0
        self.alpha = 1.0        # 0.0 - 1.0

        # D-pad State
        self.focus_index = 0    # 0: Wheel, 1: Value, 2: Alpha
        self.is_focused = False  # True when locked into editing a specific component
        self.active_drag = None
        self._wheel_texture = None

    def set_position(self, x, y):
        self.x = x
        self.y = y
        self.wheel_center_x = self.x + self.wheel_radius + int(20 * self.scale)
        self.wheel_center_y = self.y + self.wheel_radius + int(20 * self.scale)
        self.val_slider_x = self.wheel_center_x + self.wheel_radius + int(30 * self.scale)
        self.alpha_slider_x = self.val_slider_x + self.slider_w + int(20 * self.scale)
        self.slider_y = self.wheel_center_y - self.wheel_radius

    def _generate_wheel_texture(self):
        size = self.wheel_radius * 2
        img = gen_image_color(size, size, BLANK)

        for y in range(size):
            for x in range(size):
                dx = x - self.wheel_radius
                dy = y - self.wheel_radius
                dist = math.hypot(dx, dy)

                if dist <= self.wheel_radius:
                    angle = (math.atan2(dy, dx) * 180.0 / math.pi) % 360.0
                    sat = dist / self.wheel_radius
                    col = color_from_hsv(angle, sat, 1.0)
                    image_draw_pixel(img, x, y, col)

        self._wheel_texture = load_texture_from_image(img)
        unload_image(img)

    def set_rgba(self, rgba):
        if isinstance(rgba, str):
            try:
                rgba = ast.literal_eval(rgba)
            except (ValueError, SyntaxError):
                rgba = [255, 255, 255, 255]

        if isinstance(rgba, (list, tuple)) and len(rgba) >= 3:
            r, g, b = rgba[0], rgba[1], rgba[2]
            a = rgba[3] if len(rgba) == 4 else 255
        else:
            r = g = b = a = 255

        color = Color(r, g, b, a)
        hsv = color_to_hsv(color)
        self.hue = hsv.x
        self.saturation = hsv.y
        self.value = hsv.z
        self.alpha = a / 255.0

    def get_rgba(self) -> tuple[int, int, int, int]:
        rgb = color_from_hsv(self.hue, self.saturation, self.value)
        return (rgb.r, rgb.g, rgb.b, int(self.alpha * 255))

    def get_color(self) -> Color:
        rgb = color_from_hsv(self.hue, self.saturation, self.value)
        rgb.a = int(self.alpha * 255)
        return rgb

    def update_dpad(self, key) -> bool:
        """Processes D-pad input using toggle-focus logic. Returns False when exiting."""
        # Enter key toggles active editing focus on/off
        if key == KeyboardKey.KEY_ENTER:
            self.is_focused = not self.is_focused
            return True

        # Back or End key exits focus mode first; if already unfocused, exits picker
        if key in (KeyboardKey.KEY_BACK, KeyboardKey.KEY_END):
            if self.is_focused:
                self.is_focused = False
                return True
            return False

        # --- MODE 1: NAVIGATION MODE (is_focused == False) ---
        if not self.is_focused:
            if key == KeyboardKey.KEY_LEFT:
                self.focus_index = (self.focus_index - 1) % 3
            elif key == KeyboardKey.KEY_RIGHT:
                self.focus_index = (self.focus_index + 1) % 3
            return True

        # --- MODE 2: EDITING MODE (is_focused == True) ---
        # 1. Wheel Editing (Focus Index 0)
        if self.focus_index == 0:
            if key == KeyboardKey.KEY_LEFT:
                self.hue = (self.hue - 5.0) % 360.0
            elif key == KeyboardKey.KEY_RIGHT:
                self.hue = (self.hue + 5.0) % 360.0
            elif key == KeyboardKey.KEY_UP:
                self.saturation = min(1.0, self.saturation + 0.05)
            elif key == KeyboardKey.KEY_DOWN:
                self.saturation = max(0.0, self.saturation - 0.05)

        # 2. Value Slider Editing (Focus Index 1)
        elif self.focus_index == 1:
            if key in (KeyboardKey.KEY_UP, KeyboardKey.KEY_RIGHT):
                self.value = min(1.0, self.value + 0.05)
            elif key in (KeyboardKey.KEY_DOWN, KeyboardKey.KEY_LEFT):
                self.value = max(0.0, self.value - 0.05)

        # 3. Alpha Slider Editing (Focus Index 2)
        elif self.focus_index == 2:
            if key in (KeyboardKey.KEY_UP, KeyboardKey.KEY_RIGHT):
                self.alpha = min(1.0, self.alpha + 0.05)
            elif key in (KeyboardKey.KEY_DOWN, KeyboardKey.KEY_LEFT):
                self.alpha = max(0.0, self.alpha - 0.05)

        return True

    def update_mouse(self) -> bool:
        """Processes mouse dragging interactions."""
        mouse_pos = get_mouse_position()
        mouse_down = is_mouse_button_down(MouseButton.MOUSE_BUTTON_LEFT)
        mouse_pressed = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)

        if not mouse_down:
            self.active_drag = None
            return False

        if mouse_pressed:
            dx = mouse_pos.x - self.wheel_center_x
            dy = mouse_pos.y - self.wheel_center_y
            if math.hypot(dx, dy) <= self.wheel_radius:
                self.active_drag = "wheel"
                self.focus_index = 0
                self.is_focused = True
            elif (self.val_slider_x <= mouse_pos.x <= self.val_slider_x + self.slider_w and
                  self.slider_y <= mouse_pos.y <= self.slider_y + self.slider_h):
                self.active_drag = "val"
                self.focus_index = 1
                self.is_focused = True
            elif (self.alpha_slider_x <= mouse_pos.x <= self.alpha_slider_x + self.slider_w and
                  self.slider_y <= mouse_pos.y <= self.slider_y + self.slider_h):
                self.active_drag = "alpha"
                self.focus_index = 2
                self.is_focused = True

        if self.active_drag == "wheel":
            dx = mouse_pos.x - self.wheel_center_x
            dy = mouse_pos.y - self.wheel_center_y
            dist = min(math.hypot(dx, dy), self.wheel_radius)
            self.hue = (math.atan2(dy, dx) * 180.0 / math.pi) % 360.0
            self.saturation = dist / self.wheel_radius
            return True
        elif self.active_drag == "val":
            y_clamped = max(self.slider_y, min(mouse_pos.y, self.slider_y + self.slider_h))
            self.value = 1.0 - ((y_clamped - self.slider_y) / self.slider_h)
            return True
        elif self.active_drag == "alpha":
            y_clamped = max(self.slider_y, min(mouse_pos.y, self.slider_y + self.slider_h))
            self.alpha = 1.0 - ((y_clamped - self.slider_y) / self.slider_h)
            return True

        return False

    def draw(self, font=None):
        if not self._wheel_texture:
            self._generate_wheel_texture()

        draw_rectangle(self.x, self.y, self.width, self.height, fade(BLACK, 0.85))
        draw_rectangle_lines(self.x, self.y, self.width, self.height, DARKGRAY)

        # Highlight ring color logic:
        # SKYBLUE = Section selected (Navigation Mode)
        # GOLD = Section active/focused for editing (Focus Mode)
        wheel_outline = GOLD if (self.focus_index == 0 and self.is_focused) else (SKYBLUE if self.focus_index == 0 else BLANK)
        val_outline = GOLD if (self.focus_index == 1 and self.is_focused) else (SKYBLUE if self.focus_index == 1 else WHITE)
        alpha_outline = GOLD if (self.focus_index == 2 and self.is_focused) else (SKYBLUE if self.focus_index == 2 else WHITE)

        # 1. Wheel Section
        draw_texture(self._wheel_texture, self.wheel_center_x - self.wheel_radius, self.wheel_center_y - self.wheel_radius, WHITE)
        if wheel_outline != BLANK:
            draw_circle_lines(self.wheel_center_x, self.wheel_center_y, self.wheel_radius + 4, wheel_outline)

        angle_rad = math.radians(self.hue)
        sat_dist = self.saturation * self.wheel_radius
        sel_x = int(self.wheel_center_x + math.cos(angle_rad) * sat_dist)
        sel_y = int(self.wheel_center_y + math.sin(angle_rad) * sat_dist)
        draw_circle_lines(sel_x, sel_y, 6, WHITE)
        draw_circle_lines(sel_x, sel_y, 7, BLACK)

        # 2. Value Slider Section
        for i in range(self.slider_h):
            val_step = 1.0 - (i / self.slider_h)
            col = color_from_hsv(self.hue, self.saturation, val_step)
            draw_line(self.val_slider_x, self.slider_y + i, self.val_slider_x + self.slider_w, self.slider_y + i, col)

        val_handle_y = int(self.slider_y + (1.0 - self.value) * self.slider_h)
        draw_rectangle_lines(self.val_slider_x - 2, val_handle_y - 3, self.slider_w + 4, 6, val_outline)

        # 3. Alpha Slider Section
        base_col = color_from_hsv(self.hue, self.saturation, self.value)
        for i in range(self.slider_h):
            alpha_step = 1.0 - (i / self.slider_h)
            col = Color(base_col.r, base_col.g, base_col.b, int(alpha_step * 255))
            draw_line(self.alpha_slider_x, self.slider_y + i, self.alpha_slider_x + self.slider_w, self.slider_y + i, col)

        alpha_handle_y = int(self.slider_y + (1.0 - self.alpha) * self.slider_h)
        draw_rectangle_lines(self.alpha_slider_x - 2, alpha_handle_y - 3, self.slider_w + 4, 6, alpha_outline)

        # 4. Preview & Text
        preview_x = self.alpha_slider_x + self.slider_w + int(30 * self.scale)
        preview_y = self.slider_y
        preview_size = int(60 * self.scale)

        draw_rectangle(preview_x, preview_y, preview_size, preview_size, RAYWHITE)
        draw_rectangle(preview_x, preview_y, preview_size // 2, preview_size // 2, LIGHTGRAY)
        draw_rectangle(preview_x + preview_size // 2, preview_y + preview_size // 2, preview_size // 2, preview_size // 2, LIGHTGRAY)

        draw_rectangle(preview_x, preview_y, preview_size, preview_size, self.get_color())
        draw_rectangle_lines(preview_x, preview_y, preview_size, preview_size, WHITE)

        r, g, b, a = self.get_rgba()
        text_str = f"R: {r}\nG: {g}\nB: {b}\nA: {a}"
        if font:
            draw_text_ex(font, text_str, (preview_x, preview_y + preview_size + 15), 18 * self.scale, 1.0, SKYBLUE)
        else:
            draw_text(text_str, preview_x, preview_y + preview_size + 15, int(16 * self.scale), SKYBLUE)

    def unload(self):
        if self._wheel_texture:
            unload_texture(self._wheel_texture)