import os, random, time, re
import ast
from config import Config, ItemType

from dfimage import DFItemImage
from dfvideo import DFItemVideo
from dfmodel import DFItemModel

class DFItemList:
    def __init__(self, digitalframe, paths):
        self.df = digitalframe
        self.paths = paths
        self.folders = []
        self.folder = ""
        self.subfolder = ""
        self.items = []
        self.indexes = None
        self.index = 0
        self.last_index = 0
        self.type_ext = Config.get('items.types.image.ext', ['.jpg', '.jpeg', '.heic', '.heif', '.tif', '.tiff'])   # just for autocreating config file
        self.type_ext = Config.get('items.types.video.ext', ['.mp4', '.mpg', ".avi", ".mov"])   # just for autocreating config file
        self.type_ext = Config.get('items.types.model.ext', ['.glb', '.obj', '.gltf'])  # just for autocreating config file
        self.type_ext = Config.get('items.types', {})
        self.all_ext = self.get_all_ext()
        self.filter = Config.get('items.filter', "")
        self.filter_prev = None
        self.filter_error = None
        self.sort = Config.get('items.sort', False)
        self.shuffle = Config.get('items.shuffle', False)
        self.private = False
        self.direction = 1
        self.show_text = False
        self.meta_config = self.get_meta_config()
        self.meta_show = self.set_meta_show()
        self.last_load = time.monotonic()
        self.load_items()

    def load_items(self):
        if self.last_load > time.monotonic() + 1.0:
            self.df.logger.info(f"load_items skipped")
            return

        self.df.paused = True
        self.folders.clear()
        self.items.clear()
        for path in self.paths:
            path = os.path.normpath(path)
            if os.path.exists(path):
                self.list_files(path)
            else:
                self.df.logger.error(f"{path} not found")

        if self.sort: self.folders.sort()

        self.df.logger.info(f"load_items: {len(self.items)=}")

        if len(self.items) == 0:
            self.df.error = f"No items to show. Please check configuration file ({Config.config_file})"
            self.df.logger.error(self.df.error)
            return

        # set vertical pair
        for i in self.items:
            x = i.name.find('+')
            if x >= 0:
                if i.type == ItemType.IMAGE:
                    pair_name = i.name[x+1:]
                    for j in self.items:
                        if j != i and j.name == pair_name and not j.paired:
                            i.pair = j
                            j.paired = True
                            break
                elif i.type == ItemType.VIDEO:
                    head, _ = os.path.split(i.file)
                    i.filemp3 = os.path.join(head, i.name[0:x])
                    i.has_sound = True

        # set indexes
        self.indexes = list(range(0, len(self.items)))
        if self.shuffle:
            random.shuffle(self.indexes)

        self.last_load = time.monotonic()
        self.df.paused = False

    def list_files(self, path):
        _, folder = os.path.split(path)
        if folder not in self.folders:
            self.folders.append(folder)
        for entry in os.scandir(path):
            if not entry.name.startswith("."):
                if entry.is_file():
                    _, ext = os.path.splitext(entry.name)
                    ext = ext.lower()
                    for k, v in self.type_ext.items():
                        if ext in v.get('ext'):
                            if k == 'image':
                                self.items.append(DFItemImage(self, folder, entry))
                                break
                            elif k == 'video':
                                self.items.append(DFItemVideo(self, folder, entry))
                                break
                            elif k == 'model':
                                self.items.append(DFItemModel(self, folder, entry))
                                break
                            else:
                                self.df.logger.info(f"{ext} ignored")
                else:
                    self.list_files(entry.path)

    def get_all_ext(self):
        e = {}
        for k, v in self.type_ext.items():
            e[k] = v.get('ext')
        return e

    def count(self):
        return len(self.items)

    def get(self):
        i = self.index
        while True:
            i = i + self.direction
            if i > len(self.indexes) - 1: i = 0
            if i < 0: i = len(self.indexes) - 1
            ii = self.indexes[i]
            if self.check(ii):
                self.items[ii].ftt = 0
                self.index = i
                self.direction = 1
                self.folder = self.items[ii].folder
                return self.items[ii]
            else:
                if i == self.index:
                    self.direction = 1
                    return None

    def matches_search_tag_parser(self, item, filter_str):
        """
        Parses tokenized search queries:
          - 'Canon' -> Substring search across file path, name, or any EXIF tag value
          - 'make:Canon' or 'artist=John Doe' -> Key/value EXIF search
        """
        tokens = filter_str.strip().split()
        tags = getattr(item, 'tags', {}) or {}

        for token in tokens:
            if ":" in token or "=" in token:
                key, val = re.split(r'[:=]', token, 1)
                key_lower, val_lower = key.lower(), val.lower()

                matched = any(
                    key_lower in k.lower() and val_lower in str(v).lower()
                    for k, v in tags.items()
                )
                if not matched:
                    return False
            else:
                term = token.lower()
                in_name = term in item.name.lower()
                in_file = term in item.file.lower()
                in_tags = any(term in str(v).lower() for v in tags.values())
                if not (in_name or in_file or in_tags):
                    return False
        return True

    def get_filter_namespace(self, item):
        """
        Exposes item metadata shortcuts as well as all tag keys formatted
        into valid python variable identifiers.
        """
        tags = getattr(item, 'tags', {}) or {}

        # Base namespace attributes
        ns = {
            "file": item.file,
            "name": item.name,
            "tags": tags,
            # Common explicit shortcuts
            "make": tags.get("Image Make", ""),
            "model": tags.get("Image Model", ""),
            "artist": tags.get("Image Artist", "") or tags.get("EXIF CameraOwnerName", ""),
            "date": tags.get("EXIF DateTimeOriginal", "") or tags.get("Image DateTime", ""),
            "hue": tags.get("Hue", ""),
        }

        # Dynamically inject ALL tags converted to snake_case identifier keys
        # e.g., "EXIF ExposureTime" -> "exposuretime", "Image Model" -> "model"
        for k, v in tags.items():
            # Remove the first word (e.g., "EXIF", "Image", "GPS")
            parts = k.strip().split(maxsplit=1)
            remaining_key = parts[1] if len(parts) > 1 else parts[0]
            
            # Format to snake_case
            clean_key = re.sub(r'\W+', '_', remaining_key).lower().strip('_')
            
            # Only add if valid and not already in ns
            if clean_key and clean_key not in ns:
                ns[clean_key] = v

        return ns

    def check(self, i):
        item = self.items[i]
        if item.paired:
            return False

        if item.private and not self.private:
            return False

        if self.df.indexer and self.df.indexer.selected:
            ret = next((sel for sel in self.df.indexer.selected if sel.get("file") == item.file), None)
            if not ret: return False

        if self.subfolder != "" and not self.subfolder in item.file:
            return False

        if self.filter != "":
            ret = False
            try:
                # Mode switch based on first character:
                if self.filter.startswith('='):
                    # Original evaluation: Direct access to item attributes/methods
                    ret = eval(self.filter[1:], vars(item))

                elif self.filter.startswith('?'):
                    # Context Shortcuts mode: Evaluates inside namespace containing tag variables
                    ns = self.get_filter_namespace(item)
                    ret = eval(self.filter[1:], ns)

                else:
                    # Search Tag Parser mode: Lightweight tokenized string matching
                    ret = self.matches_search_tag_parser(item, self.filter)

            except Exception as e:
                if self.filter != self.filter_prev:
                    self.filter_prev = self.filter
                    self.filter_error = str(e)
                    self.df.logger.warning(f"filter: {self.filter}\n{e}")
            finally:
                if not ret: return False

        return True

    def set_next(self):
        self.direction = 1

    def set_prev(self):
        self.direction = -1

    def get_folders(self):
        return self.folder, self.folders

    def get_subfolder(self):
        return self.subfolder

    def set_subfolder(self, value):
        if value in self.folders:
            self.subfolder = value
        else:
            self.subfolder = ""

    def get_filter(self):
        return self.filter

    def set_filter(self, filter):
        try:
            if filter == "":
                self.filter = filter
            elif filter.startswith('='):
                ast.parse(filter[1:], mode='eval')
                self.filter = filter
            elif filter.startswith('?'):
                ast.parse(filter[1:], mode='eval')
                self.filter = filter
            else:
                # Simple search tag parser mode requires no AST validation
                self.filter = filter
            # save filter
            recent = Config.get('items.recent_filter', [])
            if not filter in recent:
                recent.append(filter)
                Config.set('items.recent_filter', recent)

            return True
        except SyntaxError as e:
            self.df.logger.warning(f"filter: {filter}::{e}")
            return False

    def get_shuffle(self):
        return self.shuffle

    def set_shuffle(self, value):
        self.shuffle = value
        Config.set('items.shuffle', value)
        if value:
            random.shuffle(self.indexes)
        else:
            self.indexes.sort()
        pass

    def set_meta_show(self):
        if not self.meta_config:
            return 0

        enabled = 0
        for _, v in self.meta_config.items():
            if v.get('enabled', False):
                enabled += 1
        return enabled

    def set_show_text(self, key, value):
        if value.upper() == "ON":
            self.meta_config[key]['enabled'] = True
            self.meta_show += 1
        else:
            self.meta_config[key]['enabled'] = False
            self.meta_show -= 1

    def get_show_text(self, key):
        return "on" if self.text_is_on(key) else "off"

    def not_show_text(self, key):
        self.set_show_text(key, ("OFF" if self.text_is_on(key) else "ON"))

    def text_is_on(self, key):
        if key in self.meta_config:
            return self.meta_config[key]['enabled']
        else:
            return False

    def get_meta_config(self):
        meta = Config.get('items.types.image.metadata', None)
        if not meta:
            meta = {
                "title": {
                    "enabled": False,
                    "tag": "Image ImageDescription"
                },
                "caption": {
                    "enabled": False,
                    "tag": "Image ImageDescription"
                },
                "name": {
                    "enabled": False,
                    "tag": "=self.name"
                },
                "date": {
                    "enabled": False,
                    "tag": "EXIF DateTimeOriginal|Image OriTimeDigitized"
                },
                "location": {
                    "enabled": False,
                    "tag": "GPS GPSLatitude&GPS GPSLongitude"
                },
                "directory": {
                    "enabled": False,
                    "tag": "=self.folder"
                }
            }

            Config.set('items.types.image.metadata', meta)
            Config.set('items.types.image.metadata_format', "{name} {title} {caption} {date[:10]} {location} {directory}")
        return meta
