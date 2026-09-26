import os, logging, shutil
import json, re
import ast
from pathlib import Path

class RunMode:
    DESKTOP = "desktop"     # Standard desktop session (X11/Wayland)
    XINIT = "xinit"         # xinit / bare X server
    DRM = "drm"             # Headless KMS/DRM (no X server)

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
        Config.RESOURCES_PIPER = os.path.join(Config.RESOURCES, 'piper')

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

    @staticmethod
    def get_key_tree() -> dict[str, list[str]]:
        """
        Extracts a dictionary where each top-level key maps to a list
        of all its nested sub-keys in dot-notation.
        """
        tree = {}

        def _extract_subkeys(prefix, current_dict):
            keys = []
            for k, v in current_dict.items():
                full_path = f"{prefix}.{k}" if prefix else k
                keys.append(full_path)
                if isinstance(v, dict):
                    keys.extend(_extract_subkeys(full_path, v))
            return keys

        for root_key, val in Config.config.items():
            if isinstance(val, dict):
                tree[root_key] = _extract_subkeys("", val)
            else:
                tree[root_key] = []

        return tree

    @staticmethod
    def backup(max_backups: int = 10) -> str | None:
        """
        Creates a rolling backup of the current config_file up to max_backups.
        Re-indexes existing backups and deletes the oldest if total exceeds max_backups.
        """
        if not Config.config_file or not os.path.exists(Config.config_file):
            return None

        file_path = Path(Config.config_file)
        stem = file_path.stem  # e.g., "config"
        ext = file_path.suffix  # e.g., ".json"
        parent = file_path.parent

        # Find existing backup files matching stem_X.ext
        pattern = re.compile(rf"^{re.escape(stem)}_(\d+){re.escape(ext)}$")
        existing_backups = []

        for p in parent.iterdir():
            if p.is_file():
                match = pattern.match(p.name)
                if match:
                    existing_backups.append((int(match.group(1)), p))

        # Sort backups by index in ascending order (1, 2, 3...)
        existing_backups.sort(key=lambda x: x[0])

        # Shift indices if max limit reached
        if len(existing_backups) >= max_backups:
            # Delete the oldest backup (the lowest index)
            oldest_idx, oldest_path = existing_backups.pop(0)
            if oldest_path.exists():
                oldest_path.unlink()

            # Shift remaining files (e.g. config_2 -> config_1, config_3 -> config_2)
            for new_idx, (_, path) in enumerate(existing_backups, start=1):
                new_name = parent / f"{stem}_{new_idx}{ext}"
                path.rename(new_name)

            next_index = max_backups
        else:
            next_index = len(existing_backups) + 1

        # Create the new backup file
        backup_path = parent / f"{stem}_{next_index}{ext}"
        shutil.copy2(Config.config_file, backup_path)
        return str(backup_path)
    
    @staticmethod
    def restore(backup_file: str) -> bool:
        """
        Restores the active config.json from a backup file path (e.g. output of Config.backup()).
        Reloads Config.config dictionary into memory.
        """
        if not backup_file or not os.path.exists(backup_file):
            print(f"Restore failed: Backup file '{backup_file}' does not exist.")
            return False

        try:
            # Copy backup back to active config file destination
            target_file = Config.config_file or 'config.json'
            shutil.copy2(backup_file, target_file)
            Config.config_file = target_file

            # Reload internal config dict state from restored file
            with open(target_file, "r", encoding="utf-8") as f:
                Config.config = json.load(f)
            return True
        except Exception as e:
            print(f"Error restoring from {backup_file}: {e}")
            return False
    
    @staticmethod
    def delete(backup_first: bool = True) -> bool:
        """
        Deletes config_file and resets internal config state.
        Optionally creates a backup before deletion.
        """
        if Config.config_file and os.path.exists(Config.config_file):
            if backup_first:
                Config.backup()
            try:
                os.remove(Config.config_file)
                Config.config = {}
                return True
            except Exception as e:
                print(f"Error deleting {Config.config_file}: {e}")
                return False
        return False
    
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

    full_call = sorted(full_call)
    #key_default = sorted(key_default, key=lambda x: x['key'].lower())

    make_config = "\nimport os, logging\nscale=1.0\n"
    for item in full_call:
        if 'self.' not in item:
            make_config += item + "\n"
    make_config += "\nConfig.save()"

    backup_file = None
    try:
        backup_file = Config.backup()
        Config.delete(backup_first=False)
        exec(make_config)
        plugins_config = os.path.join(Config.RESOURCES_CONFIG, "plug_config.json")
        if os.path.exists(plugins_config):
            with open(plugins_config, "r", encoding="utf-8") as f: pc = json.load(f)
            Config.set('plugins', pc)
            Config.save()
        cloud_config = os.path.join(Config.RESOURCES_CONFIG, "cloud_config.json")
        if os.path.exists(cloud_config):
            with open(cloud_config, "r", encoding="utf-8") as f: cc = json.load(f)
            Config.set('cloud', cc)
            Config.save()

        logger.info(f"{Config.config_file} created successfully ({len(full_call)} entries).")
    except Exception as e:
        Config.restore(backup_file)
        logger.error(f"{make_config}\nExecution failed: {e}")
        return f"{e}. see log for more info"

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
    return "done"

def out_item(md, fullkey, key, item):
    if isinstance(item, dict):
        for k, i in item.items():
            out_item(md, f"{fullkey}.{k}", k, i)
    else:
        md.write(f"| {fullkey} | `{item}` | {key} |\n")
