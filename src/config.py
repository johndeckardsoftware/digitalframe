import os
import json, re

class ItemType:
    IMAGE = 0
    VIDEO = 1
    MODEL = 2
    UNDEFINED = 9

class Config:
    WORK_PATH = None
    RESOURCES = None
    AUTO_SET = True
    config_file = None
    config = {}

    @staticmethod
    def init(file=None, path=None):
        Config.WORK_PATH = os.path.realpath(os.path.dirname(__file__))
        if not (file and os.path.exists(file)):
            Config.config_file = 'config.json'

        if os.path.exists(Config.config_file):
            try:
                with open(Config.config_file, "r", encoding="utf-8") as f:
                    Config.config = json.load(f)
            except Exception as e:
                print(f"Error loading {Config.config_file}: {e}")
                return False

        Config.RESOURCES = Config.get('window.resources', os.path.join(Config.WORK_PATH, 'resources'))
        if path:
            Config.set('items.path', [path])
        return True

    @staticmethod
    def exists(file=None):
        if not (file and os.path.exists(file)):
            if not file: file = 'config.json'
            if os.path.exists(file):
                return True
            else:
                return False
        else:
            return True

    @staticmethod
    def save():
        with open(Config.config_file, "w", encoding="utf-8") as f:
            json_style = json.dumps(Config.config, indent=4)
            compact_json = re.sub(r'\[\s+([^\]]+?)\s+\]', 
                      lambda m: "[" + re.sub(r'\s+', ' ', m.group(1)).strip() + "]", json_style)
            f.write(compact_json)

    @staticmethod
    def get(key: str, _default: any, c: dict = None) -> any:
        if not c: c = Config.config
        s = key.split('.')
        i = 1; l = len(s); r = True
        for k in s:
            if k in c:
                c = c[k]
            else:
                if i == l:
                    r = False
                    break
                else:
                    c[k] = {}
                    c = c[k]
            i += 1
        if r:
            return c
        else:
            if Config.AUTO_SET:
                #Config.set(key, _default)
                c[k] = _default
            return _default

    @staticmethod
    def set(key: str, value: any, c: dict = None) -> any:
        if not c: c = Config.config
        s = key.split('.')
        r = True
        for k in s:
            if k in c:
                pc = c
                c = c[k]
            else:
                c[k] = {}
                pc = c
                c = c[k]
        if r:
            pc[k] = value

    @staticmethod
    def get_color(key: str, _default: any, c: dict = None) -> any:
        color = Config.get(key, _default, c)
        return (color[0], color[1], color[2], color[3])
