import os, logging
import json, re
import ast
from pathlib import Path

class ItemType:
    IMAGE = 0
    VIDEO = 1
    MODEL = 2
    UNDEFINED = 9

class Config:
    WORK_PATH = None
    SOURCE_PATH = None
    RESOURCES = None
    RESOURCES_3D = None
    RESOURCES_BORDER = None
    RESOURCES_CONFIG = None
    RESOURCES_FONT = None
    RESOURCES_HELP = None
    RESOURCES_ICON = None
    RESOURCES_MATTE = None
    RESOURCES_MENU = None
    RESOURCES_SHADER = None
    RESOURCES_VOSK = None
    AUTO_SET = False
    config_file = None
    config = {}

    @staticmethod
    def init(file=None, path=None):
        Config.WORK_PATH = os.getcwd()
        #if not (file and os.path.exists(file)):
        if not file:
            Config.config_file = 'config.json'
        else:
            Config.config_file = file

        if os.path.exists(Config.config_file):
            try:
                with open(Config.config_file, "r", encoding="utf-8") as f:
                    Config.config = json.load(f)
            except Exception as e:
                print(f"Error loading {Config.config_file}: {e}")
                return False

        Config.SOURCE_PATH = os.path.realpath(os.path.dirname(__file__))
        Config.RESOURCES = Config.get('window.resources', os.path.join(Config.SOURCE_PATH, 'resources'))
        Config.RESOURCES_3D = os.path.join(Config.RESOURCES, '3d')
        Config.RESOURCES_BORDER = os.path.join(Config.RESOURCES, 'border')
        Config.RESOURCES_CONFIG = os.path.join(Config.RESOURCES, 'config')
        Config.RESOURCES_FONT = os.path.join(Config.RESOURCES, 'font')
        Config.RESOURCES_HELP = os.path.join(Config.RESOURCES, 'help')
        Config.RESOURCES_ICON = os.path.join(Config.RESOURCES, 'icon')
        Config.RESOURCES_MATTE = os.path.join(Config.RESOURCES, 'matte')
        Config.RESOURCES_MENU = os.path.join(Config.RESOURCES, 'menu')
        Config.RESOURCES_SHADER = os.path.join(Config.RESOURCES, 'shader')
        Config.RESOURCES_VOSK = os.path.join(Config.RESOURCES, 'vosk')

        return True

    @staticmethod
    def configured(reset_config):
        path = Config.get('items.path', None)
        Config.AUTO_SET = True
        if path is None or path[0] == "/path/to/items":
            return False
        else:
            return True

    @staticmethod
    def configure(path):
        config_setup(create_md=False)
        Config.set('items.path', [path])
        return True

    @staticmethod
    def save():
        with open(Config.config_file, "w", encoding="utf-8") as f:
            json_style = json.dumps(Config.config, indent=4)
            compact_json = re.sub(
                    r'\[(?![^\]]*\{)\s+([^\]]+?)\s+\]',
                    lambda m: "[" + re.sub(r'\s+', ' ', m.group(1)).strip() + "]",
                    json_style
                )
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


def analyze_config_calls(file_path, key_default, full_call):
    with open(file_path, 'rb') as f:
        source = f.read().decode('utf-8')

    # We use AST to find the calls because it's cleaner for high-level searching
    tree = ast.parse(source)

    for node in ast.walk(tree):
        # We look for: Call nodes -> Attribute (Config.get)
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Attribute) and
                node.func.attr == 'get' and
                getattr(node.func.value, 'id', None) == 'Config'):

                # Extracting details
                call_snippet = ast.unparse(node)
                line_no = node.lineno

                # Extract args
                pos_args = [ast.unparse(a) for a in node.args]
                kw_args = {kw.arg: ast.unparse(kw.value) for kw in node.keywords}

                if call_snippet not in full_call:
                    full_call.append(call_snippet)
                    key_default.append({
                        "line": line_no,
                        "full_call": call_snippet,
                        "key": pos_args[0] if pos_args else "Unknown",
                        "default": pos_args[1] if pos_args else "Unknown",
                    })

def list_files(path, key_default, full_call):
    for entry in os.scandir(path):
        if entry.is_file():
            if entry.name != "config.py" and entry.name.endswith(".py"):
                analyze_config_calls(entry.path, key_default, full_call)
        else:
            list_files(entry.path, key_default, full_call)

def config_setup(create_md=False):
    logger = logging.getLogger(__name__)
    key_default = []
    full_call = []
    list_files(os.path.join(Config.WORK_PATH, "src"), key_default, full_call)

    #full_call = sorted(full_call)
    #key_default = sorted(key_default, key=lambda x: x['key'].lower())

    make_config = "\nimport os, logging\nscale=1.0\n"
    for item in full_call:
        if 'self.' not in item:
            make_config += item + "\n"
    make_config += "\nConfig.save()"

    try:
        exec(make_config)
        plugins_config = os.path.join(Config.WORK_PATH, "src/resources/plug_config.json")
        if os.path.exists(plugins_config):
            with open(plugins_config, "r", encoding="utf-8") as f: pc = json.load(f)
            Config.set('plugins', pc)
            Config.save()
        cloud_config = os.path.join(Config.WORK_PATH, "src/resources/cloud_config.json")
        if os.path.exists(cloud_config):
            with open(cloud_config, "r", encoding="utf-8") as f: cc = json.load(f)
            Config.set('cloud', cc)
            Config.save()

        logger.info(f"{Config.config_file} created successfully ({len(full_call)} entries).")
    except Exception as e:
        logger.error(f"{make_config}\nExecution failed: {e}")

    # Write to Markdown file
    if create_md:
        output_file = Path(Config.config_file).stem + ".md"
        with open(output_file, "w") as md:
            md.write("# Configuration Inventory\n\n")
            md.write("| Key | Default Value | Description |\n")
            md.write("| :--- | :--- | :--- |\n")

            for key, item in Config.config.items():
                out_item(md, key, key, item)

        logger.info(f"Successfully generated {output_file}")

def out_item(md, fullkey, key, item):
    if isinstance(item, dict):
        for k, i in item.items():
            out_item(md, f"{fullkey}.{k}", k, i)
    else:
        md.write(f"| {fullkey} | `{item}` | {key} |\n")
