import os, re
from pyray import *
import clock
from config import Config, ItemType
from utils.histogram import Histogram
from utils.image import fast_image_info
from dftext import dftext

class DFItemImage:
    PORTRAIT = 0
    LANDSCAPE = 1

    def __init__(self, items, folder, entry):
        self.items = items      # DFItemList
        self.df = items.df      # DigitalFrame
        self.file = entry.path.replace("\\", "/")
        self.folder = folder
        self.name = entry.name
        self.type = ItemType.IMAGE
        #self.df.logger.debug(f"{self.file=} {self.name=}")
        self.width, self.height, self.tags = fast_image_info(self.file, self.df.logger)
        self.ratio = round(self.width / self.height, 2)
        self.x = 0
        self.y = 0
        self.orientation = self.LANDSCAPE if self.width > self.height else self.PORTRAIT
        self.histogram = None
        self.matte_rgb = None
        self.pair = None
        self.paired = False
        self.private = True if self.name.startswith('@') else False
        self.processed = False
        self._skip = False   # exit image show (prev or next button)
        # timing
        self.ftt = 0
        self.ttl = 0 # if != 0 override image_ttl
        # fade
        self.fade = Config.get('items.types.image.fade', False)
        self._fade = False
        self.fade_speed = Config.get('items.types.image.fade_speed', 2.0)
        self.fade_inc = int(255 / (clock.fps * self.fade_speed))
        self.alpha = 0
        # update
        self.update = self.image_update
        # drawing
        self.draw = self.image_draw
        # close
        self.close = self.image_close
        # work
        self.tags2text = ""
        self.tags_color=Config.get('window.tags_color', (200,200,200,255))

    def skip(self):
        self._skip = True

    def set_paused(self, value):
        pass

    def set_ttl(self, value):
        self.ttl = value

    def set_border(self, width, height):
        self.border_name = Config.get('items.types.image.border.file', "border02t.png")
        self.border_file = os.path.join(Config.RESOURCES, self.border_name)
        if not os.path.exists(self.border_file):
            return None, 0, 0, 0

        scale = width / self.width

        border_thick = Config.get('items.types.image.border.thick', 8)

        self.border_thick = int(border_thick * scale)
        self.border_width = width + (self.border_thick * 2)
        self.border_height = height + (self.border_thick * 2)
        self.border_opacity = Config.get('items.types.image.border.opacity', 200)

        border = load_image(self.border_file)
        image_resize(border, self.border_width, self.border_height)
        return border, self.border_width, self.border_height, self.border_thick

    def set_matte(self):
        df = self.df
        self.texture_name = Config.get('items.types.image.matte.texture', "mat_texture2i.jpg")
        self.texture_file = os.path.join(Config.RESOURCES, self.texture_name)
        matte_type = Config.get('items.types.image.matte.type', 0)
        if matte_type == 0:         # color from image
            matte = gen_image_color(df.width, df.height, self.matte_rgb)
        elif matte_type == 1:         # fixed color
            color = Config.get('items.types.image.matte.color', (200, 200, 200, 255))
            matte = gen_image_color(df.width, df.height, color)
        elif matte_type == 2:         # perlin noise
            offset_x  = Config.get('items.types.image.matte.offset_x', 0)
            offset_y = Config.get('items.types.image.matte.offset_y', 0)
            scale     = Config.get('items.types.image.matte.scale', 0.5)
            matte = gen_image_perlin_noise(df.width, df.height, offset_x, offset_y, scale)
            image_color_tint(matte, self.matte_rgb)
        elif matte_type == 3:         # gradient
            direction = Config.get('items.types.image.matte.direction', 90)
            color_start = Config.get('items.types.image.matte.start_color', (247, 226, 162, 255))
            color_end   = Config.get('items.types.image.matte.end_color', (250, 243, 221, 255))
            matte = gen_image_gradient_linear(df.width, df.height, direction, color_start, color_end)
        elif matte_type == 4:         # gradient from image color
            direction = Config.get('items.types.image.matte.direction', 90)
            color_start = self.matte_rgb
            factor = Config.get('items.types.image.matte.gradient_factor', 0.1)
            color_end = color_brightness(color_start, factor)
            matte = gen_image_gradient_linear(df.width, df.height, direction, color_start, color_end)
        else:
            matte = load_image(self.texture_file)
            image_resize(matte, df.width, df.height)
            return matte

        _matte_ = load_image(self.texture_file)
        image_resize(_matte_, df.width, df.height)
        matte_opacity = Config.get('items.types.image.matte.opacity', 16)
        image_draw(matte, _matte_, Rectangle(0, 0, df.width, df.height), Rectangle(0, 0, df.width, df.height), (255,255,255,matte_opacity))

        _matte_ = unload_image(_matte_)

        return matte

    def image_process(self):
        df = self.df
        image = load_image(self.file)

        if not self.histogram:
            self.histogram = Histogram(self.name, image)
        self.matte_rgb = self.histogram.get_mat_color()

        width = height = left_margin = top_margin = 0
        if df.ratio == self.ratio:
            if df.width != self.width and df.height != self.height:
                image_resize(image, df.width, df.height)
            self.x = self.y = 0
            self.texture_name = None
            self.border_name = None
        else:
            if not self.pair:
                top_margin = df.height * Config.get('items.types.image.matte.top_margin', 5) // 100
                height = df.height - top_margin
                width = int(self.ratio * height)
                image_resize(image, width, height)
                y = top_margin // 2
                x = (df.width - width) // 2
                # border
                border, bw, bh, bt = self.set_border(width, height)
                # matte
                matte = self.set_matte()
                image_draw(matte, image,  Rectangle(0, 0, width, height), Rectangle(x, y, width, height), (255,255,255,255))
                if border:
                    image_draw(matte, border, Rectangle(0, 0, bw, bh), Rectangle(x-bt, y-bt, bw, bh), (255, 255, 255, self.border_opacity))

                unload_image(image)
                if border: border = unload_image(border)
                image = matte
            else:
                imagep = load_image(self.pair.file)
                top_margin = df.height * Config.get('items.types.image.matte.top_margin', 5) // 100
                left_margin = df.width * Config.get('items.types.image.matte.left_margin', 5) // 100
                height = df.height - top_margin
                width = int(self.ratio * height)
                image_resize(image, width, height)
                image_resize(imagep, width, height)
                y = top_margin // 2
                x = (df.width - left_margin - width*2) // 3
                # border
                border, bw, bh, bt = self.set_border(width, height)
                lm = left_margin // 2
                # matte
                matte = self.set_matte()
                image_draw(matte, image,  Rectangle(0, 0, width, height), Rectangle(lm+x, y, width, height), (255,255,255,255))
                image_draw(matte, imagep, Rectangle(0, 0, width, height), Rectangle(lm+x+width+x, y, width, height), (255,255,255,255))
                if border:
                    image_draw(matte, border, Rectangle(0, 0, bw, bh), Rectangle(lm+x-bt, y-bt, bw, bh), (255,255,255,self.border_opacity))
                    image_draw(matte, border, Rectangle(0, 0, bw, bh), Rectangle(lm+x+width+x-bt, y-bt, bw, bh), (255,255,255,self.border_opacity))

                unload_image(image)
                imagep = unload_image(imagep)
                if border: unload_image(border)
                image = matte

        if self.fade:
            self.alpha = 0
            self._fade = True
            self.fade_inc = int(255 / (clock.fps * self.fade_speed))
        else:
            self.alpha = 255

        df.debug = f"{self.name=}, resize={width}x{height} {self.ratio=} {left_margin=} {top_margin=}"

        if df.texture: unload_texture(df.texture)
        df.texture = load_texture_from_image(image)
        image = unload_image(image)

    def image_update(self):
        self.ftt += clock.rft

        if self._fade:
            self.alpha += self.fade_inc
            if self.alpha > 255:
                self.alpha = 255
                self._fade = False

        if not self.processed:
            self.image_process()
            self.processed = True

    def image_draw(self):
        df = self.df
        draw_texture(df.texture, self.x, self.y, (255, 255, 255, self.alpha))
        if self.items.meta_show:
            self.show_tags()
        #self.histogram.draw()
        if self.ftt > df.image_ttl or self._skip:
            self._skip = False
            self.ftt = 0
            self.processed = False
            df.item = None

    def image_close(self):
        pass

    def show_tags(self):
        if not self.items.meta_config: return
        code = ""
        try:
            for k, v in self.items.meta_config.items():
                if v.get('enabled', False):
                    tag = v.get('tag', "")
                    if tag != "":
                        if tag[0:1] == "=":
                            tv = tag[1:]
                            code += f"{k}={tv}\n"
                        elif '|' in tag:
                            tags = tag.split('|')
                            for tag in tags:
                                tv = self.get_tag(tag)
                                if tv != "": break
                            code += f"{k}='{tv}'\n"
                        elif '&' in tag:
                            tv = ""
                            tags = tag.split('&')
                            for tag in tags:
                                v = self.get_tag(tag)
                                if v != "": tv += ", " + v if tv != "" else v
                            code += f"{k}='{tv}'\n"
                        else:
                            tv = self.get_tag(tag)
                            code += f"{k}='{tv}'\n"
                    else:
                        code += f"{k}=''\n"
                else:
                    code += f"{k}=''\n"
            code += "self.tags2text = f'" + Config.get('items.types.image.metadata_format', "") + "'"
            exec(code)
        except Exception as e:
            self.df.logger.warning(f"{self.name=}{self.tags=}{code=}\n{e}")
        dftext(self.tags2text, -2, 2, fs=-28, tint=self.tags_color, shadow=2)

    def get_tag(self, tag):
        tv = self.tags.get(tag, None)
        if not tv: return ""
        if tv != "":
            if not isinstance(tv, str): tv = str(tv)
            tv = tv.replace("\\", "/")
            tv = tv.replace("'", "\\'")
        return tv
