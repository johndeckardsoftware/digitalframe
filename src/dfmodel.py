import os, math, time, json
from config import Config, ItemType
from pyray import *
from pygltflib import GLTF2
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
        self.ftt = 0
        self.processed = False
        self._skip = False
        # model
        self.model = None
        self.gltf = None
        self.config = {}
        # Camera configuration
        self.camera = None
        # update
        self.update = self.model_update
        # drawing
        self.draw = self.model_draw
        # close
        self.close = self.model_close

    def skip(self):
        self._skip = True

    def set_paused(self, value):
        pass

    def model_process(self):
        df = self.df
        self.load_global_conf()
        self.load_model_conf(self.file)
        if self.model: unload_model(self.model)
        self.model = load_model(self.file)

        self.camera = Camera3D(
            self.cam_pos,
            self.cam_target,
            self.cam_up,
            self.cam_fovy,
            CameraProjection.CAMERA_PERSPECTIVE
        )

        if self.bg_texture_file:
            if not os.path.isabs(self.bg_texture_file):
                self.bg_texture_file = os.path.join(Config.RESOURCES, self.bg_texture_file)
            image = load_image(self.bg_texture_file)
            image_resize(image, df.width, df.height)
            if df.texture: df.texture = unload_texture(df.texture)
            df.texture = load_texture_from_image(image)
            image = unload_image(image)

        clock.push_set_fps(self.fps)

        self.processed = True

    def model_update(self):
        self.ftt += clock.rft
        if not self.processed:
            self.model_process()
            self.processed = True

        if self.cam_enabled:     # camera movment
            update_camera(self.camera, CameraMode.CAMERA_ORBITAL)
        else:                   # object movent
            t = _t(); t1 = _t1(); t2 = _t2()
            s = self.speed
            self.angle = eval(self.motion_expr)

    def model_draw(self):
        df = self.df
        clear_background(WHITE)

        if self.texture and self.bg_texture_file:
            draw_texture(df.texture, 0, 0, WHITE)

        begin_mode_3d(self.camera)

        #rl_disable_backface_culling()
        if self.billboard and self.bg_texture_file:
            draw_billboard(self.camera, df.texture, self.billboard_pos, self.billboard_size, WHITE)

        if self.billboard_pro and self.bg_texture_file:
            size = Vector2(self.billboard_size, self.billboard_size)
            origin = Vector2(size.x / 2, size.y / 2)
            draw_billboard_pro(
                self.camera,
                df.texture,
                Rectangle(0, 0, df.width, df.height),      # Part of texture to use
                self.billboard_pos,                                  # World position
                self.cam_up,                                         # UP vector (keeps it vertical)
                size,                                                # Size in world units
                origin,                                              # Origin offset
                self.angle,                                          # FIXED ROTATION ANGLE in degrees
                WHITE                                                # Tint
            )

        if self.cam_enabled:
            draw_model(self.model, self.pos, self.scale, self.tint)
        else:
            draw_model_ex(self.model, self.pos, self.axes, self.angle, self.scale_v3, self.tint)

        if self.grid_show:
            draw_grid(self.grid_slices, self.grid_spacing)
            draw_line_3d(Vector3(0,0,0), Vector3(self.grid_axis_height,0,0), RED)   # X-axis
            draw_line_3d(Vector3(0,0,0), Vector3(0,self.grid_axis_height,0), GREEN) # Y-axis
            draw_line_3d(Vector3(0,0,0), Vector3(0,0,self.grid_axis_height), BLUE)  # Z-axis

        #rl_enable_backface_culling()

        end_mode_3d()

        if self.ftt > self.ttl or self._skip:
            clock.pop_set_fps()
            self.model = unload_model(self.model)
            self._skip = False
            self.ftt = 0
            self.processed = False
            df.item = None

    def model_close(self):
        if self.model:
            unload_model(self.model)
            self.model = None

    def load_global_conf(self):
        self.config['fps'] = Config.get('items.types.model.fps', 24)
        self.config['ttl'] = Config.get('items.types.model.ttl', 60)
        self.config['use_glf'] = Config.get('items.types.model.use_gltf', False)
        self.config['pos'] = v3(Config.get('items.types.model.pos', [0.0, 0.0, 0.0]))
        self.config['axes'] = v3(Config.get('items.types.model.axes', [0.0, 1.0, 0.0]))
        self.config['angle'] = Config.get('items.types.model.angle', 0.0)
        self.config['motion_expr'] = Config.get('items.types.model.motion_expr', "t * s")
        self.config['speed'] = Config.get('items.types.model.speed', 1.0)
        scale = Config.get('items.types.model.scale', 1.0)
        self.config['scale'] = scale
        self.config['scale_v3'] = v3(Config.get('items.types.model.scale_v3', [scale, scale, scale]))
        self.config['tint'] = Config.get('items.types.model.tint', (255, 255, 255, 255))
        self.config['grid_show'] = Config.get('items.types.model.grid', False)
        self.config['grid_slices'] = Config.get('items.types.model.grid_slices', 70)
        self.config['grid_spacing'] = Config.get('items.types.model.grid_slices', 1.0)
        self.config['grid_axis_height'] = Config.get('items.types.model.grid_axis_height', 69.0)
        self.config['bg_texture_file'] = None
        self.config['cam_enabled'] = Config.get('items.types.model.cam_enabled', True)
        self.config['cam_pos'] = v3(Config.get('items.types.model.camera.position', [0.0, 0.0, 30.0]))
        self.config['cam_target'] = v3(Config.get('items.types.model.camera.target', [0.0, 0.0, 0.0]))
        self.config['cam_up'] = v3(Config.get('items.types.model.camera.up', [0.0, 1.0, 0.0]))  # Up standard
        self.config['cam_fovy'] = Config.get('items.types.model.camera.fovy', 50.0)
        self.config['billboard'] = Config.get('items.types.model.billboard', False)
        self.config['billboard_pro'] = Config.get('items.types.model.billboard_pro', False)
        self.config['billboard_pos'] = v3(Config.get('items.types.model.billboard_pos', [0.0, 0.0, -40.0]))
        self.config['billboard_size'] = Config.get('items.types.model.billboard_size', 100.0)
        self.config['texture'] = Config.get('items.types.model.texture', True)

    def load_model_conf(self, file_path):
        file, ext = os.path.splitext(file_path)

        if ext == ".glb":
            # Load Metadata with pygltflib
            self.gltf = GLTF2.load(file_path)
        else:
           self.config['use_glf'] = False
 
        gltf_extras = {}
        if self.config['use_glf']:
            # the first node.extras not empty could contain custom properties
            for node in self.gltf.nodes:
                if node.extras:
                    gltf_extras = node.extras
                    break

        # Load possible model config
        conf_json = {}
        file += ".json"
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8") as f:
                conf_json = json.load(f)

        for key, value in self.config.items():
            v = conf_json.get(key, None)
            if v == None:
                v = gltf_extras.get(key, None)
            if v != None:
                if "struct Vector" in str(value):
                    v = a2v(v)
                self.config[key] = v
                setattr(self, key, v)
            else:
                setattr(self, key, value)

    def get_prop(self, name, default=None):
        for node in self.gltf.nodes:
            if node.extras:
                if name in node.extras:
                    v = node.extras[name]
                    if isinstance(v, list):
                        return a2v(v)
                    else:
                        return v
        return default

def a2v(va:list):
    if len(va) == 4:
        return Vector4(va[0], va[1], va[2], va[3])
    if len(va) == 3:
        return Vector3(va[0], va[1], va[2])
    elif len(va == 2):
        return Vector2(va[0], va[1])
    else:
        return va

def v3(va:list):
    return Vector3(va[0], va[1], va[2])

def _t():
    return (time.time()) % 360

def _t1():
    return (time.time()*10) % 360

def _t2():
    return (time.time()*100) % 360
