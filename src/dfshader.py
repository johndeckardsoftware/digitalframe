# https://registry.khronos.org/OpenGL-Refpages/es3.0/
# https://thebookofshaders.com

import os, re, math
import clock
from config import Config
from pyray import *

class ShaderWrapper:
    def __init__(self, digitalframe, fs_name, vs_name=None):
        self.df = digitalframe
        self.name = fs_name
        self.fs_path =  os.path.join(Config.RESOURCES, f"{fs_name}.fs")
        self.config = Config.get(f'shader.{self.name}', {})
        if not vs_name: vs_path = ffi.NULL
        self.shader = load_shader(vs_path, self.fs_path)
        self.uniforms = {}
        if os.path.exists(self.fs_path):
            self._parse_shader(self.fs_path)
        else:
            self.df.logger.error(f"[Shader] {self.fs_path} Not found.")

    def _parse_shader(self, path):
        with open(path, 'r') as f:
            content = f.read()

        # Regex to find: uniform [tipo] [nome];
        # Support float, vec2, vec3, vec4
        pattern = r"uniform\s+(\w+)\s+(\w+);"
        matches = re.findall(pattern, content)

        for type_name, var_name in matches:
            # texture0 automatically managed by Raylib
            if var_name == "texture0": continue

            location = get_shader_location(self.shader, var_name)
            if location != -1:
                self.uniforms[var_name] = {
                    "location": location,
                    "type": self._get_raylib_type(type_name)
                }
            else:
                self.df.logger.error(f"[Shader] Not found uniform: {var_name} ({type_name}) at loc: {location}")

    def _get_raylib_type(self, glsl_type):
        types = {
            "float": ShaderUniformDataType.SHADER_UNIFORM_FLOAT,
            "vec2":  ShaderUniformDataType.SHADER_UNIFORM_VEC2,
            "vec3":  ShaderUniformDataType.SHADER_UNIFORM_VEC3,
            "vec4":  ShaderUniformDataType.SHADER_UNIFORM_VEC4,
        }
        return types.get(glsl_type, ShaderUniformDataType.SHADER_UNIFORM_FLOAT)

    def set_value(self, name, value):
        """
        Send the value to GPU.
        'value' actually can be a float o a list of float
        """
        if name not in self.uniforms:
            return

        u = self.uniforms[name]

        # value conversion in ffi for pyray
        if isinstance(value, (int, float)):
            data = ffi.new("float *", value)
        else:
            data = ffi.new(f"float[{len(value)}]", value)

        set_shader_value(self.shader, u["location"], data, u["type"])

    def begin(self):
        begin_shader_mode(self.shader)

    def end(self):
        end_shader_mode()

    def unload(self):
        unload_shader(self.shader)

    def config_get(self, key, default=None):
        return self.config.get(key, default)

    def config_set(self, key, value):
        self.config[key] = value

    def config_setd(self, key, value):
        if self.config.get(key, None) is None:
            self.config[key] = value

class Lightness(ShaderWrapper):
    def __init__(self, digitalframe, fs_path, vs_path=None, ):
        super().__init__(digitalframe, fs_path, vs_path)
        self.df = digitalframe

    def update(self):
        self.set_value("uBrightness", self.df.get_brightness_normalized())

class LightGradient(ShaderWrapper):
    def __init__(self, digitalframe, fs_path, vs_path=None, ):
        super().__init__(digitalframe, fs_path, vs_path)
        self.df = digitalframe
        self.config_setd('uIntensity', 0.0)
        self.config_setd('uDirection', 180.0)
        # Lower values (0.2) make a "hard line" of light, higher values (2.0) make the light very subtle and spread out
        self.config_setd('uSoftness', 3.0)
        # Imposta una luce solare calda (Giallo paglierino)
        # I valori vanno da 0.0 a 1.0
        self.config_setd("uLightColor", [1.0, 0.9, 0.6])
        # Imposta un'ombra cinematografica (Blu notte scuro)
        self.config_setd("uShadowColor", [0.2, 0.2, 0.5])


    def update(self):
        # Convert Degrees to a Direction Vector
        radians = math.radians(self.config.get('uDirection'))
        dir_x = math.cos(radians)
        dir_y = math.sin(radians)

        # Send to GPU
        self.set_value("uIntensity", self.df.get_brightness_normalized())
        self.set_value("uDirection", [dir_x, dir_y])
        self.set_value("uSoftness", self.config_get('uSoftness'))
        self.set_value("uLightColor", self.config_get('uLightColor'))
        self.set_value("uShadowColor", self.config_get('uShadowColor'))

class ColorWave(ShaderWrapper):
    def __init__(self, digitalframe, fs_path, vs_path=None, ):
        super().__init__(digitalframe, fs_path, vs_path)
        self.df = digitalframe
        self.config_setd('uTolerance', 0.25) # How "strict" the color matching is (0.1 to 0.5)
        self.fps = self.config_get('fps', 12)
        clock.push_set_fps(self.fps)

    def update(self):
        # Send to GPU
        current_time = get_time()
        self.set_value("uTime", current_time)
        self.set_value("uTolerance", self.config_get('uTolerance'))
        self.set_value("uBrightness", self.df.get_brightness_normalized())

class Fireplace(ShaderWrapper):
    def __init__(self, digitalframe, fs_path, vs_path=None, ):
        super().__init__(digitalframe, fs_path, vs_path)
        self.df = digitalframe
        self.seconds = 0
        self.config_setd('uIntensity', 0.1)
        self.config_setd('fps', 6)
        self.fps = self.config_get('fps', 6)
        clock.push_set_fps(self.fps)

    def update(self):
        current_time = get_time()
        self.set_value("uTime", current_time)
        self.set_value("uIntensity", self.config_get('uIntensity'))
        self.set_value("uBrightness", self.df.get_brightness_normalized())

class CRT(ShaderWrapper):
    def __init__(self, digitalframe, fs_path, vs_path=None, ):
        super().__init__(digitalframe, fs_path, vs_path)
        self.df = digitalframe
        self.seconds = 0

    def update(self):
        self.seconds += 1/60 #get_frame_time()
        self.set_value("uTime", self.seconds)

def create_shader(self, name=None):
    if not name:
        name = Config.get(f'shader.name', None)
        if not name:
            name = "lightness"
            Config.set('shader.name', name)
            self.logger.warning(f"[Shader] no shader specified, using 'lightness'")

    if name == "lightness":
        return Lightness(self, name)

    elif name == "light_gradient":
        return LightGradient(self, name)

    elif name == "colorwave":
        return ColorWave(self, name)

    elif name == "fireplace":
        return Fireplace(self, name)

    elif name == "crt":
        return CRT(self, name)

    else:
        return Lightness(self, "lightness")
