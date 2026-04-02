
from config import Config, ItemType
from pyray import *
import cv2
import numpy as np
import clock

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
        self.processed = False
        self._skip = False
        self.video = None
        self.width = self.df.width
        self.height = self.df.height
        self.channels = 3
        self.x = 0
        self.y = 0
        self.source_rec = None
        self.dest_rec = None
        self.origin = Vector2(0, 0, 0) # Or Vector2 depending on your raylib-py version

        # update
        self.update = self.video_update
        # drawing
        self.draw = self.video_draw
        # close
        self.close = self.video_close

    def skip(self):
        self._skip = True

    def get_fit_rect(self, video_w, video_h, screen_w, screen_h):
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
    
    def video_process(self):
        self.video = cv2.VideoCapture(self.file)
        self.ret, self.frame = self.video.read()

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

        self.fps = self.video.get(cv2.CAP_PROP_FPS)
        clock.push_set_fps(int(self.fps))
        self.processed = True

    def video_update(self):
        self.ftt += clock.rft
        if not self.processed:
            self.video_process()
            self.processed = True

        # Read a frame
        ret, frame = self.video.read()
        if not ret:
            self.video.set(cv2.CAP_PROP_POS_FRAMES, 0) # Loop video
            return

        # Convert BGR (OpenCV) in RGB (Raylib)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        #frame_rgb = np.ascontiguousarray(frame_rgb)

        # Update texture pixels
        pixels_raw = ffi.from_buffer("unsigned char *", frame_rgb)
        pixels_ptr = ffi.cast("void *", pixels_raw)
        update_texture(self.df.texture, pixels_ptr)

    def video_draw(self):
        # draw
        clear_background(BLACK)
        draw_texture_pro(self.df.texture, self.source_rec, self.dest_rec, self.origin, 0.0, WHITE)

        if self.ftt > self.ttl or self._skip:
            clock.pop_set_fps()
            self.video.release()
            self.video = None
            self._skip = False
            self.ftt = 0
            self.processed = False
            self.df.item = None

    def video_close(self):
        if self.video:
            self.video.release()
            self.video = None
