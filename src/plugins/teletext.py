
import os, time, threading, requests, json
from pathlib import Path
from plugin import PluginWrapper
from pyray import KeyboardKey
from pyray import get_time, load_image, unload_texture, load_texture_from_image, unload_image, draw_texture
from dftext import dftext, col_max
from utils.image import resize_to_percentage
from osk import OnScreenKeyboard
import clock

class TeletextPlugin(PluginWrapper):
    def __init__(self, digitalframe, config):
        super().__init__(digitalframe, config)
        self.base_url = self.config.get('url', "https://www.televideo.rai.it/televideo/pub/tt4web/Nazionale/")
        self.cache = None  # {page: True/False}
        self.cache_expire = self.config.get('cache_expire', 120)
        self.cache_file = self.config.get('cache_file', os.path.expanduser("~/teletext/teletext.json"))
        self.cache_path = self.config.get('cache_path', os.path.expanduser("~/teletext"))
        self.cache_index = 2
        self.home_page = self.config.get('page', "100")
        self.page = self.home_page
        self.subpage = 0
        self.pagefile = ""
        self.zoom = self.config.get('zoom', 60)
        self.is_running = False
        self.ttl = 10
        self.ftt = 9999
        self.in_osk = False
        self.osk = OnScreenKeyboard(self, layout="osk_teletext.json")
        self.page_texture = None

        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

        self.load_cache()

    def keyboard(self, key):
        if self.in_osk:
            self.in_osk = self.osk.update(key)
            if not self.in_osk: # input ended
                self.get_page(self.osk.typed_text, 0)
        elif key == KeyboardKey.KEY_ENTER:
            self.in_osk = True
        elif key == KeyboardKey.KEY_UP:
            self.get_page(-1, 1)
        elif key == KeyboardKey.KEY_DOWN:
            self.get_page(1, 1)
        elif key == KeyboardKey.KEY_LEFT:
            self.get_page(-10, 1)
        elif key == KeyboardKey.KEY_RIGHT:
            self.get_page(10, 1)

    def update(self):
        if not self.active: return
        if self.is_running: return
        try:
            self.start_download_thread(100, 899)
        except Exception as e:
            self.logger.error(f"{self.name}: {e}")

    def draw(self):
        if not self.active: return
        try:
            self.osk.draw()
            if self.ftt > self.ttl:
                page_file = self.get_page(0, 1)
                if not page_file: return

                self.ftt = 0
                page = load_image(page_file)
                resize_to_percentage(page, self.df.width, self.df.height, self.zoom)
                if self.page_texture: unload_texture(self.page_texture)
                self.page_texture = load_texture_from_image(page)
                page = unload_image(page)
            else:
                self.ftt += clock.rft

            draw_texture(self.page_texture, (self.df.width - self.page_texture.width) // 2, (self.df.height - self.page_texture.height) // 5, (255,255,255,192))
        except Exception as e:
            self.logger.error(f"{self.name}: {e}")

    def load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r", encoding="utf-8") as f:
                self.cache = json.load(f)
        else:
            self.cache = {"000": 100, "001": 0}

    def save_cache(self):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json_cache = json.dumps(self.cache, indent=4)
            f.write(json_cache)

    def get_page(self, page, mode=0):
        cl = list(self.cache.keys())
        if len(cl) > 2:
            if mode == 0: # absolute
                try:
                    self.cache_index = cl.index(page, 2)
                except Exception:
                    self.cache_index = 2
            else: # relative
                self.cache_index = (self.cache_index + page) % len(cl)
            self.ftt = 9999 # load new page
            return os.path.join(self.cache_path, f"16_9_page-{cl[self.cache_index]}.png")
        else:
            return None

    def is_file_older_than(self, file_path, offset_minutes):
        path = Path(file_path)

        if not path.exists():
            return True

        # Get creation time (st_ctime)
        # On Windows, this is creation; on Unix, it's often the last metadata change
        #creation_time = path.stat().st_birthtime # dont'work in raspberry
        creation_time = path.stat().st_ctime

        # Calculate the threshold
        # time.time() returns seconds, so we multiply minutes by 60
        current_time = time.time()
        offset_seconds = offset_minutes * 60

        return (current_time - creation_time) > offset_seconds

    def start_download_thread(self, start, end):
        self.is_running = True
        self.thread = threading.Thread(target=self.page_downloader, args=(start, end))
        self.thread.daemon = True
        self.thread.start()
        self.logger.info(f"Thread started for pages: {start}-{end}...")

    def page_downloader(self, start, end):
        if "000" in self.cache:
            last_page = self.cache["000"]
            if int(last_page) != end:
                start = last_page

        for p in range(start, end + 1):
            for sp in ["", ".2", ".3", ".4", ".5", ".6", ".7", ".8", ".9", ".10"]:
                page = f"{p}{sp}"
                filename = f"16_9_page-{page}.png"
                url = f"{self.base_url}{filename}"
                path = os.path.join(self.cache_path, filename)
                exists = True
                if self.is_file_older_than(path, self.cache_expire):
                    try:
                        response = requests.get(url, timeout=5)
                        if response.status_code == 200:
                            with open(path, 'wb') as f:
                                f.write(response.content)
                        else:
                            exists = False
                        time.sleep(1.0)
                    except Exception as e:
                        exists = False
                        self.logger.error(f"page {page}: {e}")

                if not exists: break

                self.cache[page] = exists
                self.cache["000"] = p
                self.save_cache()

            #if not self.active:
            #    break

        self.save_cache()
        self.is_running = False
        self.logger.info(f"Thread ended")
