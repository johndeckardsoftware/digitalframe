import os, random, time
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
        self.type_ext = Config.get('items.types.image.ext', ['.jpg', '.jpeg'])          # just for autocreating config file
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

        # set vertical pair (image items)
        for i in self.items:
            x = i.name.find('+')
            if x >= 0:
                if i.type == ItemType.IMAGE:
                    pair = i.name[x+1:]
                    for j in self.items:
                        if j != i and j.name == pair:
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

    def check(self, i):     # and version
        item = self.items[i]
        if item.paired:
            return False

        if item.private and not self.private:
            return False

        if self.subfolder != "" and not self.subfolder in item.file:
            return False

        if self.filter != "":
            ret = False
            try:
                ret = eval(self.filter, vars(item))
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
        self.filter = filter

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
        if value == "ON":
            self.meta_config[key]['enabled'] = True
            self.meta_show += 1
        else:
            self.meta_config[key]['enabled'] = False
            self.meta_show -= 1

    def get_show_text(self, key):
        return "ON" if self.text_is_on(key) else "OFF"

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
"""
Exif example
{
    "Image ExifOffset": 241,
    "GPS GPSVersionID": "2.2.0.0",
    "GPS GPSLatitudeRef": "N",
    "GPS GPSLatitude": [51, 30, 14.78],
    "GPS GPSLongitudeRef": "W",
    "GPS GPSLongitude": [0, 4, 28.47],
    "GPS GPSAltitudeRef": 0,
    "GPS GPSAltitude": 77.88,
    "GPS GPSTimeStamp": [12, 13, 40],
    "GPS GPSDOP": 11.965,
    "GPS GPSProcessingMethod": "ASCII\x00\x00\x00fused",
    "GPS GPSDate": "2018-08-22",
    "Image GPSInfo": "20464",
    "Image ImageWidth": 4032,
    "Image ImageLength": 3024,
    "Image Make": "Google",
    "Image Model": "Pixel 2",
    "Image Orientation": "Horizontal (normal)",
    "Image XResolution": 72,
    "Image YResolution": 72,
    "Image ResolutionUnit": "Pixels/Inch",
    "Image Software": "HDR+ 1.0.199571065z",
    "Image DateTime": "2018-08-22 13:13:41",
    "Image YCbCrPositioning": "Centered",
	"Image ImageDescription": "description here",
	"Image Artist": "Artist",
    "Image Copyright": "Copyright",
    "EXIF ExposureTime": 0.000299,
    "EXIF FNumber": 1.8,
    "EXIF ExposureProgram": "Program Normal",
    "EXIF ISOSpeedRatings": 75,
    "EXIF ExifVersion": "0220",
    "EXIF DateTimeOriginal": "2018-08-22 13:13:41",
    "EXIF DateTimeDigitized": "2018-08-22 13:13:41",
    "EXIF ComponentsConfiguration": "YCbCr",
    "EXIF ShutterSpeedValue": 11.71,
    "EXIF ApertureValue": 1.7,
    "EXIF BrightnessValue": 8.82,
    "EXIF ExposureBiasValue": 0,
    "EXIF MaxApertureValue": 1.7,
    "EXIF SubjectDistance": 1.835,
    "EXIF MeteringMode": "CenterWeightedAverage",
    "EXIF Flash": "Flash did not fire, compulsory flash mode",
    "EXIF FocalLength": 4.442,
    "EXIF SubSecTime": "594779",
    "EXIF SubSecTimeOriginal": "594779",
    "EXIF SubSecTimeDigitized": "594779",
    "EXIF FlashPixVersion": "0100",
    "EXIF ColorSpace": "sRGB",
    "EXIF ExifImageWidth": 4032,
    "EXIF ExifImageLength": 3024,
    "Interoperability InteroperabilityIndex": "R98",
    "Interoperability InteroperabilityVersion": "0100",
    "EXIF InteroperabilityOffset": "20434",
    "EXIF SensingMethod": "One-chip color area",
    "EXIF SceneType": "Directly Photographed",
    "EXIF CustomRendered": "Custom",
    "EXIF ExposureMode": "Auto Exposure",
    "EXIF WhiteBalance": "Auto",
    "EXIF DigitalZoomRatio": 0,
    "EXIF FocalLengthIn35mmFilm": 27,
    "EXIF SceneCaptureType": "Standard",
    "EXIF Contrast": "Normal",
    "EXIF Saturation": "Normal",
    "EXIF Sharpness": "Normal",
    "EXIF SubjectDistanceRange": 2,
	"EXIF CameraOwnerName": "owner name",
}
"""