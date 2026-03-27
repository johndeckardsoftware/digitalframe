
from config import Config, ItemType
from pyray import *
import clock

class DFItemModel:

    def __init__(self, items, folder, entry):
        self.items = items      # DFItemList
        self.df = items.df      # DigitalFrame
        self.file = entry.path.replace("\\", "/")
        self.folder = folder
        self.name = entry.name
        self.type = ItemType.MODEL
        self.tags = {}
        self.paired = False
        self.private = False
        # timing
        self.fps = Config.get('items.types.model.fps', 24)
        self.ttl = Config.get('items.types.model.ttl', 60) # if != 0 override image_ttl
        self.ftt = 0
        self.processed = False
        self._skip = False
        self.model = None
        # Set model space position
        self.model_pos = Vector3(0.0, 0.0, 0.0)
        self.model_scale = Config.get('items.types.model.scale', 1.0)
        self.show_grid = Config.get('items.types.model.grid', False)
        # Camera configuration
        self.camera = Camera3D(
            Vector3(10.0, 10.0, 10.0),          # position
            Vector3(0.0, 0.0, 0.0),             # target
            Vector3(0.0, 1.0, 0.0),             # up
            90.0,                               # fovy
            CameraProjection.CAMERA_PERSPECTIVE # projection
        )

        # update
        self.update = self.model_update
        # drawing
        self.draw = self.model_draw
        # close
        self.close = self.model_close

    def model_process(self):
        if self.model: unload_model(self.model)
        self.model = load_model(self.file)
        clock.push_set_fps(self.fps)
        self.processed = True

    def model_update(self):
        self.ftt += clock.rft
        if not self.processed:
            self.model_process()
            self.processed = True

        update_camera(self.camera, CameraMode.CAMERA_ORBITAL)

    def model_draw(self):
        clear_background(RAYWHITE)

        begin_mode_3d(self.camera)
        draw_model(self.model, self.model_pos, 0.5, RED)
        if self.show_grid:
            draw_grid(10, 1.0)
        end_mode_3d()

        if self.ftt > self.ttl or self._skip:
            clock.pop_set_fps()
            unload_model(self.model)
            self.model = None
            self._skip = False
            self.ftt = 0
            self.processed = False
            self.df.item = None

    def model_close(self):
        if self.model:
            unload_model(self.model)
            self.model = None
