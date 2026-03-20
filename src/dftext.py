import sys
from pyray import *
import clock
from config import Config

class DrawTextTTL:
    def __init__(self, text, row=None, col=None, rh=0, cw=0, font=None, fs=16, spacing=1, tint=(255,255,255,255), shadow=0, ttl=1):
        self.text = text
        self.row = row
        self.col = col
        self.rh = rh
        self.cw = cw
        self.font = font
        self.fs = fs
        self.spacing = spacing
        self.tint = tint
        self.shadow = shadow
        self.ftt = 0
        self.ttl = ttl
        #
        self.id = 0
        self.disposable = False

    def draw(self):
        if self.disposable: return
        dftext(self.text, self.row, self.col, self.rh, self.cw, self.font, self.fs, self.spacing, self.tint, self.shadow)
        self.ftt += clock.rft
        if self.ftt > self.ttl:
            self.disposable = True

class DrawTextTTLList:
    def __init__(self, digitalframe):
        self.df = digitalframe
        self.dtts = []
        self.info_color = Config.get('window.info_color', (255,255,255,255))
        self.id = 0
        self.show_id = -1
        self.show3_id = -1
        self.show4_id = -1

    def get_id(self):
        self.id += 1
        if self.id == sys.maxsize:
            self.id = 0
        return self.id

    def add(self, dt):
        id = self.get_id()
        dt.id = id
        self.dtts.append(dt)
        return id

    def remove(self, id):
        for item in self.dtts:
            if item.id == id:
                item.disposable = True

    def show(self, text, row, col, font=None, fs=22, tint=None, shadow=2, ttl=1):
        if self.show_id != -1:
            self.remove(self.show_id)
        if not font: font = self.df.font
        if not tint: tint = self.info_color
        self.show_id = self.add(DrawTextTTL(text, row, col, font=font, fs=fs, tint=tint, shadow=shadow, ttl=ttl))
        return self.show_id

    def show3(self, text, ttl=1):
        if self.show3_id != -1:
            self.remove(self.show3_id)
        self.show3_id = self.add(DrawTextTTL(text, -3, 2, font=self.df.font, fs=-30, tint=self.info_color, shadow=2, ttl=ttl))
        return self.show3_id

    def show4(self, text, ttl=2):
        if self.show4_id != -1:
            self.remove(self.show4_id)
        self.show4_id = self.add(DrawTextTTL(text, -4, 2, font=self.df.font, fs=-30, tint=self.info_color, shadow=2, ttl=ttl))
        return self.show4_id

    def draw_ttl(self):
        for dtt in self.dtts: dtt.draw()
        self.dtts = [item for item in self.dtts if not item.disposable]

width = 1024
height = 768
row_height = 16
row_max = height // row_height
col_width = 16
col_max = width // col_width
row = 0
col = 0

def update_dftext_vars():
    global width, height, row_height, row_max, col_width, col_max, row, col
    width = get_render_width()
    height = get_render_height()
    row_height = Config.get('window.col_height', 16)
    row_max = height // row_height
    col_width = Config.get('window.col_width', 16)
    col_max = width // col_width
    row = 0
    col = 0

def col2x(c, tl, cw, fs):
    global col, col_width, col_max
    if cw == 0: cw = col_width
    if fs < 0: fs *= -1; cw = fs
    if c == None: c = col
    if type(c) is str:
        if c == 'C':
            x = (col_max - tl) // 2 * cw
        elif c == 'R':
            x = (col_max - tl) * cw
        else: # default 'L'
            x = 0
    else:
        if c >= 0:
            x = c * cw
            if x > width: x = width - cw
        else:
            x = width + ((c - tl) * cw)
            if x < 0: x = 0
    col += tl
    if col > col_max: col = 0
    return x

def row2y(r, rh, fs):
    global row, row_height, max_row
    if rh == 0: rh = row_height
    if fs < 0: fs *= -1; rh = fs
    if r == None: r = row
    if type(r) is str:
        if r == 'C':
            y = row_max // 2 * rh
        elif r == 'B':
            y = col_max * rh
        else: # default 'T'
            y = 0
    else:
        if r >= 0:
            y = r * rh
            if y > height: y = height - rh
        else:
            y = height + (r * rh)
            if y < 0: y = 0
    row += 1
    if row > row_max: row = 0
    return y

def dftext(text, row=None, col=None, rh=0, cw=0, font=None, fs=16, spacing=1, tint=(255,255,255,255), shadow=0):
    global width, height, col_width, row_height, col_max, row_max
    width = get_render_width()
    height = get_render_height()
    row_max = height // row_height
    col_max = width // col_width
    if font:
        size = measure_text_ex(font, text, fs, spacing)
        size = size.x // col_width
        if shadow:
            draw_text_ex(font, text, (col2x(col, size, cw, fs)+shadow, row2y(row, rh, fs)+shadow), abs(fs), spacing, (20,20,20,128))
        draw_text_ex(font, text, (col2x(col, size, cw, fs), row2y(row, rh, fs)), abs(fs), spacing, tint)
    else:
        size = measure_text(text, fs) // col_width
        if shadow:
            draw_text(text, col2x(col, size, cw, fs)+shadow, row2y(row, rh, fs)+shadow, abs(fs), (20,20,20,128))
        draw_text(text, col2x(col, size, cw, fs), row2y(row, rh, fs), abs(fs), tint)
