import os
from pyray import *
from config import Config
from plugin import PluginWrapper

class TextEditor(PluginWrapper):
    def __init__(self, pm, config):
        super().__init__(pm, config)
        # Configure file target from plugin settings or default to settings.txt
        self.file_path = self.config.get('file_path', 'config.json')

        # Text Editor State
        self.lines = [""]
        self.cursor_row = 0
        self.cursor_col = 0
        self.scroll_top_row = 0
        self.frames_counter = 0
        self.is_modified = False  # Track unsaved changes

        # Load file immediately on init
        self.load_file()

    def load_file(self):
        try:
            with open(self.file_path, "r") as f:
                self.lines = f.read().splitlines()
            if not self.lines:
                self.lines = [""]
        except FileNotFoundError:
            self.lines = ["File not found. Type here to create it...", "Press CTRL+S to save."]

        self.is_modified = False  # Reset on load

    def save_file(self):
        try:
            with open(self.file_path, "w") as f:
                f.write("\n".join(self.lines))

            # to reload modifications
            if self.file_path == Config.config_file:
                Config.init()

            self.logger.info(f"Text Editor saved: {self.file_path}")
            self.is_modified = False  # Reset on successful save
        except Exception as e:
            self.logger.error(f"Failed to save text file: {e}")

    def keyboard(self, key):
        # If the plugin is not active on screen, ignore keystrokes
        if not self.active:
            return

        current_line = self.lines[self.cursor_row]

        # --- NAVIGATION & UTILITY KEYS ---
        if key == KeyboardKey.KEY_ENTER:
            self.lines.insert(self.cursor_row + 1, current_line[self.cursor_col:])
            self.lines[self.cursor_row] = current_line[:self.cursor_col]
            self.cursor_row += 1
            self.cursor_col = 0
            self.is_modified = True  # Content modified

        elif key == KeyboardKey.KEY_BACKSPACE:
            if self.cursor_col > 0:
                self.lines[self.cursor_row] = current_line[:self.cursor_col - 1] + current_line[self.cursor_col:]
                self.cursor_col -= 1
                self.is_modified = True  # Content modified
            elif self.cursor_row > 0:
                self.cursor_col = len(self.lines[self.cursor_row - 1])
                self.lines[self.cursor_row - 1] += current_line
                self.lines.pop(self.cursor_row)
                self.cursor_row -= 1
                self.is_modified = True  # Content modified

        elif key == KeyboardKey.KEY_LEFT:
            if self.cursor_col > 0:
                self.cursor_col -= 1
            elif self.cursor_row > 0:
                self.cursor_row -= 1
                self.cursor_col = len(self.lines[self.cursor_row])

        elif key == KeyboardKey.KEY_RIGHT:
            if self.cursor_col < len(current_line):
                self.cursor_col += 1
            elif self.cursor_row < self.lines_count() - 1:
                self.cursor_row += 1
                self.cursor_col = 0

        elif key == KeyboardKey.KEY_UP:
            if self.cursor_row > 0:
                self.cursor_row -= 1
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))

        elif key == KeyboardKey.KEY_DOWN:
            if self.cursor_row < self.lines_count() - 1:
                self.cursor_row += 1
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))

        # Page Controls (Using layout parameters dynamically)
        elif key == KeyboardKey.KEY_PAGE_UP:
            visible_lines = int((self.df.height * 0.7) // (26 * self.df.scale))
            self.cursor_row = max(0, self.cursor_row - visible_lines)
            self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))

        elif key == KeyboardKey.KEY_PAGE_DOWN:
            visible_lines = int((self.df.height * 0.7) // (26 * self.df.scale))
            self.cursor_row = min(self.lines_count() - 1, self.cursor_row + visible_lines)
            self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))

    def lines_count(self):
        return len(self.lines)

    def update(self):
        if not self.active:
            return

        if not self.df.get_paused():
            self.df.set_paused(True)

        self.frames_counter += 1

        # Shortcut: Ctrl + S to Save
        if is_key_down(KeyboardKey.KEY_LEFT_CONTROL) and is_key_pressed(KeyboardKey.KEY_S):
            self.save_file()

        # Shortcut: Ctrl + W to Close
        if is_key_down(KeyboardKey.KEY_LEFT_CONTROL) and is_key_pressed(KeyboardKey.KEY_W):
            self.active = False
            self.df.set_paused(False) # Resume digitalframe slideshow

        # --- STREAM TEXT INPUT CHARACTERS ---
        # Polling char queue matches smooth high-speed typing
        char_key = get_char_pressed()
        while char_key > 0:
            if (char_key >= 32) and (char_key <= 125):
                current_line = self.lines[self.cursor_row]
                self.lines[self.cursor_row] = current_line[:self.cursor_col] + chr(char_key) + current_line[self.cursor_col:]
                self.cursor_col += 1
                self.is_modified = True  # Content modified
            char_key = get_char_pressed()

        # Compute dynamic layout dimensions depending on parent resolution scale
        visible_lines = int((self.df.height * 0.7) // (26 * self.df.scale))

        # Camera viewport adjustment logic
        if self.cursor_row >= self.scroll_top_row + visible_lines:
            self.scroll_top_row = self.cursor_row - visible_lines + 1
        elif self.cursor_row < self.scroll_top_row:
            self.scroll_top_row = self.cursor_row

    def draw(self):
        if not self.active:
            return

        # Dim background
        draw_rectangle(0, 0, self.df.width, self.df.height, fade(BLACK, 0.8))

        # Dynamic Scale configurations matching your df.py ecosystem
        scale = self.df.scale
        font_size = int(20 * scale)
        line_height = int(26 * scale)

        # Main Bounding Box Dimensions (Centered, taking 80% width and 70% height)
        box_w = int(self.df.width * 0.8)
        box_h = int(self.df.height * 0.7)
        box_x = (self.df.width - box_w) // 2
        box_y = (self.df.height - box_h) // 2

        visible_lines = box_h // line_height

        # Dynamic header context depending on modification state
        if self.is_modified:
            header_text = f"Editing: {self.file_path}* (CTRL+S: Save | CTRL+W: Close)"
            header_color = RED  # Highlight color when unsaved changes exist
        else:
            header_text = f"Editing: {self.file_path} (CTRL+S: Save | CTRL+W: Close)"
            header_color = GREEN  # Default clean color

        # Header Title
        draw_text_ex(self.df.font, header_text,
                     Vector2(box_x, box_y - int(35 * scale)), font_size, 1.0, header_color)

        # Editor Surface Canvas
        draw_rectangle(box_x, box_y, box_w, box_h, get_color(0x1C1C1CFF))
        draw_rectangle_lines_ex(Rectangle(box_x, box_y, box_w, box_h), 2, DARKGRAY)

        # Scissor mode constraints graphics seamlessly inside our box bounds
        begin_scissor_mode(box_x, box_y, box_w, box_h)

        for i in range(visible_lines):
            line_index = self.scroll_top_row + i
            if line_index >= self.lines_count():
                break

            draw_y = box_y + int(10 * scale) + (i * line_height)

            # Line numbers margin
            line_num_str = f"{line_index + 1:3d} "
            draw_text_ex(self.df.font, line_num_str, Vector2(box_x + int(10 * scale), draw_y), font_size, 1.0, DARKGRAY)

            # Text payload
            text_x_offset = box_x + int(60 * scale)
            line_color = WHITE if line_index == self.cursor_row else LIGHTGRAY
            draw_text_ex(self.df.font, self.lines[line_index], Vector2(text_x_offset, draw_y), font_size, 1.0, line_color)

            # Dynamic Cursor Rendering
            if line_index == self.cursor_row and (self.frames_counter // 1) % 2 == 0:
                text_before_cursor = self.lines[line_index][:self.cursor_col]
                # Measure text width using your shared global frame font asset
                cursor_x_weight = measure_text_ex(self.df.font, text_before_cursor, font_size, 1.0).x
                draw_rectangle(int(text_x_offset + cursor_x_weight), draw_y, int(2 * scale), font_size, RED)

        end_scissor_mode()