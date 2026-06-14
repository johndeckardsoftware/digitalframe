import logging
import importlib
from config import Config
from pyray import KeyboardKey

logger = logging.getLogger(__name__)

class PluginManager:
    def __init__(self, digitalframe, config):
        logger.setLevel(Config.get("window.log_level", logging.INFO))
        #logger.setLevel(logging.DEBUG)
        self.df = digitalframe
        self.devices = digitalframe.devices
        self.config = config
        self.active = None
        self.use_keyboard = False
        self.plugins = []
        self.load_plugins()

    def load_plugins(self):
        for item in self.config:
            name = item['name']
            if not item.get('enabled', False): continue
            try:
                module = importlib.import_module(item['module'])
                plugin_class = getattr(module, item['class'])
                instance = plugin_class(self, item)
                self.plugins.append(instance)
                if item.get('keyboard', False): self.use_keyboard = True

                # add plugin menu to global plugin menu
                if plugins_menu := self.devices.menu.menus.get('plugins', None):
                    if plugin_menu := item.get('menu', None):
                        for p in plugin_menu:
                            np = {}
                            for k, v in p.items():
                                if k in ['f', 'g', 'e', 'fr', 'fl']:
                                    if '@' in v:
                                        np[k] = v.replace('@', f"self.df.plugins.get_instance(\"{name}\").")
                                    else:
                                        np[k] = v
                                else:
                                    np[k] = v
                            plugins_menu.insert(-1, np)

                logger.info(f"Successfully loaded: {name}")
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to load plugin {name}: {e}")

    def get_instance(self, name):
        for plugin in self.plugins:
            if plugin.name == name:
                self.active = plugin
                return plugin

    def keyboard(self, key):
        for plugin in self.plugins:
            if plugin.use_keyboard:
                plugin.keyboard(key)

    def update_all(self):
        for plugin in self.plugins:
            plugin.update()

    def draw_all(self):
        for plugin in self.plugins:
            plugin.draw()
