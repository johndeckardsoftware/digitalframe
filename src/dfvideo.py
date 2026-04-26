
import os
from pyray import *
import cv2
import clock
from config import Config, ItemType
from utils.video import extract_sound
from dftext import dftext

class DFItemVideo:

    def __init__(self, items, folder, entry):
        self.items = items      # DFItemList
        self.df = items.df      # DigitalFrame
        self.file = entry.path.replace("\\", "/")
        self.folder = folder
        self.name = entry.name
        self.type = ItemType.VIDEO
        self.tags = {}
        self.paired = False
        self.private = False
        self.df.logger.debug(f"{self.file=} {self.name=}")
        # timing
        self.fps = 24
        self.ttl = Config.get('items.types.video.ttl', 60) # if != 0 override image_ttl
        self.ftt = 0
        self.rtft = 0
        self.processed = False
        self._skip = False
        self.video = None
        self.total_frames = 0
        self.width = self.df.width
        self.height = self.df.height
        self.channels = 3
        self.x = 0
        self.y = 0
        self.source_rec = None
        self.dest_rec = None
        self.origin = Vector2(0, 0, 0) # Or Vector2 depending on your raylib-py version
        self.skip_frames = Config.get('items.types.video.skip_frames', False) # number of frameif != 0 override image_ttl
        self.background = None
        self.draw_background = True
        # sound
        self.sound_enabled = Config.get('items.types.video.sound', False)
        self.has_sound = None
        self.filemp3 = None
        self.sound = None
        self.sound_start = True
        self.pause = False

        # update
        self.update = self.video_update
        # drawing
        self.draw = self.video_draw
        # close
        self.close = self.video_close

        # work
        self.tags2text = ""
        self.tags_color=Config.get('window.tags_color', (200,200,200,255))

    def skip(self):
        self._skip = True

    def set_paused(self, value):
        if self.sound:
            if value:
                pause_music_stream(self.sound)
            else:
                play_music_stream(self.sound)

    def get_fit_rect_down(self, video_w, video_h, screen_w, screen_h):
        if video_w > screen_w:
            scale = min(screen_w / video_w, screen_h / video_h)
            new_w = video_w * scale
            new_h = video_h * scale
        else:
            new_w = video_w
            new_h = video_h

        # Center the video
        off_x = (screen_w - new_w) / 2
        off_y = (screen_h - new_h) / 2

        return Rectangle(off_x, off_y, new_w, new_h)

    def get_fit_rect(self, video_w, video_h, screen_w, screen_h):
        scale = min(screen_w / video_w, screen_h / video_h)
        new_w = video_w * scale
        new_h = video_h * scale

        # Center the video
        off_x = (screen_w - new_w) / 2
        off_y = (screen_h - new_h) / 2

        return Rectangle(off_x, off_y, new_w, new_h)

    def video_process(self):
        if self.sound_enabled:
            err = None
            if self.has_sound == None:
                self.has_sound, err, self.filemp3 = extract_sound(self.file)
            if self.has_sound:
                self.sound = load_music_stream(self.filemp3)
            else:
                self.sound = None
                if err: self.df.logger.error(f"{self.has_sound=}, {self.filemp3=}, {err=}")

        try:
            self.video = cv2.VideoCapture(self.file)
            ret, self.frame = self.video.read()

            self.height, self.width, self.channels = self.frame.shape
            # Define the source rectangle (the full size of the video frame)
            self.source_rec = Rectangle(0, 0, self.width, self.height)
            # Define the destination rectangle (the full size of the window/viewport)
            self.dest_rec = self.get_fit_rect(self.width, self.height, self.df.width, self.df.height)

            # Create the texture for the video frame
            image = gen_image_color(self.width, self.height, (255,255,255,255))
            if self.df.texture: unload_texture(self.df.texture)
            self.df.texture = load_texture_from_image(image)
            unload_image(image)

            # background
            texture_name = Config.get('items.types.image.matte.texture', "mat_texture2i.jpg")
            texture_file = os.path.join(Config.RESOURCES, texture_name)
            image = load_image(texture_file)
            image_resize(image, self.df.width, self.df.height)
            self.background = load_texture_from_image(image)
            image = unload_image(image)

            # time
            self.fps = self.video.get(cv2.CAP_PROP_FPS)
            self.total_frames = self.video.get(cv2.CAP_PROP_FRAME_COUNT)
            self.ttl = self.total_frames / self.fps
            clock.push_set_fps(int(self.fps))
        except Exception as e:
            self.video = None
            self.df.logger.error(f"{self.file}: {str(e)}")

    def video_update(self):
        if not self.processed:
            self.video_process()
            self.processed = True

        #self.rtft += clock.rft  # real total frames time
        self.ftt += clock.ft    # to show all the frames at a cost of longer time

        # Read a frame
        if self.skip_frames:
            sf = clock.rft - clock.ft
            while sf > 0: ret, frame = self.video.read(); sf -= 1; self.ftt += clock.ft

        ret, frame = self.video.read()
        if not ret:
            self.video.release()
            self.video = cv2.VideoCapture(self.file)
            return

        # Convert BGR (OpenCV) in RGB (Raylib)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        #frame_rgb = np.ascontiguousarray(frame_rgb)

        # Update texture pixels
        pixels_raw = ffi.from_buffer("unsigned char *", frame_rgb)
        pixels_ptr = ffi.cast("void *", pixels_raw)
        update_texture(self.df.texture, pixels_ptr)

        if self.sound_start and self.sound:
            play_music_stream(self.sound)
            set_music_volume(self.sound, 0.5) # Set volume to 50%
            self.sound_start = False

    def video_draw(self):
        if self.draw_background:
            draw_texture(self.background, 0, 0, WHITE)
            self.draw_background = False
        else:
            clear_background(BLACK)
        draw_texture_pro(self.df.texture, self.source_rec, self.dest_rec, self.origin, 0.0, WHITE)

        if self.sound: update_music_stream(self.sound)

        if self.items.meta_show:
            self.show_tags()

        if self.ftt > self.ttl or self._skip:
            clock.pop_set_fps()
            self.video.release()
            self.video = None
            self._skip = False
            self.ftt = 0
            self.rtft = 0
            self.processed = False
            self.sound_start = True
            self.df.item = None

    def video_close(self):
        if self.video:
            self.video = self.video.release()
        if self.sound:
            self.sound = unload_music_stream(self.sound)
        if self.background:
            self.background = unload_texture(self.background)
            self.draw_background = True

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
