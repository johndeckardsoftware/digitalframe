import os, logging, json
from pyray import *
from config import Config

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

class OnScreenKeyboard:
    def __init__(self, parent, x=None, y=None):
        self.parent = parent
        self.pos_x = x
        self.pos_y = y
        # keyboard geometry
        self.scale = Config.get('window.menu.osk_scale', 1.0)
        self.layouts = self.load_layout()
        self.layout = self.layouts['base']
        self.info = self.layouts['base_info']
        self.key_size = int(self.info['key_size'] * self.scale)
        self.spacing = int(self.info['spacing'] * self.scale)
        self.font_size = int(self.info['font_size'] * self.scale)
        # kb state
        self.row = 0
        self.col = 0
        self.cursor = 0
        self.typed_text = ""
        self.is_shift = False
        self.get_kb_pos()

    def load_layout(self):
        with open(os.path.join(Config.RESOURCES, Config.get('window.menu.osk_layout', "osk_en_layout.json")), "r") as f:
            return json.load(f)

    def get_kb_pos(self):
        if not self.pos_x:
            width = len(self.layout[0]) * (self.key_size + self.spacing)
            self.pos_x = (self.parent.df.width - width) // 2
        if not self.pos_y:
            height = len(self.layout) * (self.key_size + self.spacing)
            self.pos_y = self.parent.df.height - height

    def update(self, key):
        # Navigation
        # key_back from remote, key_end from keyboard
        if key == KeyboardKey.KEY_BACK or key == KeyboardKey.KEY_END:
            return False

        if key == KeyboardKey.KEY_BACKSPACE:
            self.typed_text = self.typed_text[:-1]
            return True

        if key == KeyboardKey.KEY_UP:
            self.row = (self.row - 1) % len(self.layout)
        elif key == KeyboardKey.KEY_DOWN:
            self.row = (self.row + 1) % len(self.layout)

        # Clamp column when changing rows
        if self.col >= len(self.layout[self.row]):
            self.col = len(self.layout[self.row]) - 1

        if key == KeyboardKey.KEY_LEFT:
            self.col = (self.col - 1) % len(self.layout[self.row])
        elif key == KeyboardKey.KEY_RIGHT:
            self.col = (self.col + 1) % len(self.layout[self.row])

        # Selection
        if key == KeyboardKey.KEY_ENTER or key == KeyboardKey.KEY_SPACE:
            key_val = self.layout[self.row][self.col]
            #if key_val == "ENTER": return False # use remote 'back' or 'end' key to close the keyboard
            self._handle_input(key_val)

        return True

    def _handle_input(self, key):
        if key == "LEFT":
            if self.cursor > 0:
                self.cursor -= 1
        elif key == "RIGHT":
            if self.cursor < len(self.typed_text):
                self.cursor += 1
        elif key == "BACK":
            if self.cursor > 0:
                # Remove character BEFORE cursor
                self.typed_text = self.typed_text[:self.cursor - 1] + self.typed_text[self.cursor:]
                self.cursor -= 1
        elif key == "SPACE":
            self._insert_char(" ")
        elif key == "ENTER":
            self._insert_char("\n")
        elif key == "SHIFT":
            self.is_shift = not self.is_shift
            self.layout = self.layouts['shift'] if self.is_shift else self.layouts['base']
        else:
            #char = key.upper() if self.is_shift else key.lower()
            self._insert_char(key)

    def _insert_char(self, char):
        # Insert at cursor position and advance cursor
        self.typed_text = self.typed_text[:self.cursor] + char + self.typed_text[self.cursor:]
        self.cursor += len(char)

    def draw(self):
        # Calculate cursor position for visual feedback
        # We slice the text up to the cursor to find the offset
        text_before_cursor = self.typed_text[:self.cursor]
        text_width = measure_text(text_before_cursor, self.font_size)

        # Draw the text
        draw_text(f"Typed: {self.typed_text}", self.pos_x, self.pos_y - self.key_size, self.font_size, WHITE)

        # Draw the blinking cursor bar (simple version: always on)
        cursor_x = self.pos_x + measure_text("Typed: ", self.font_size) + text_width
        if int(get_time() * 2) % 2 == 0: # Blinks twice per second
            draw_rectangle(cursor_x, self.pos_y - self.key_size, 2, self.font_size, GOLD)

        for r, row in enumerate(self.layout):
            for c, key in enumerate(row):
                is_selected = (r == self.row and c == self.col)

                # X-Offset logic to center specific rows or keys
                if key in self.info: # key with specific x and width
                    x_draw, width = self.info[key]
                    x_draw = int(x_draw * self.scale)
                    x_draw += self.pos_x
                    width = int(width * self.scale)
                else:
                    width = self.key_size
                    x_draw = self.pos_x + (c * (self.key_size + self.spacing))

                y_draw = self.pos_y + (r * (self.key_size + self.spacing))

                # Colors
                back_color = DARKBLUE if not is_selected else GOLD
                text_color = WHITE if not is_selected else BLACK

                # Draw Key Body
                draw_rectangle(x_draw, y_draw, width, self.key_size, back_color)

                # Draw Border for focused key
                if is_selected:
                    draw_rectangle_lines(x_draw, y_draw, width, self.key_size, ORANGE)

                # Draw Text
                draw_text(key, x_draw + self.spacing*2, y_draw + self.spacing*2, self.font_size, text_color)
