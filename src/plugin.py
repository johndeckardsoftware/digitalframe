from abc import ABC, abstractmethod
import logging

class PluginWrapper(ABC):
    def __init__(self, pm, config):
        self.pm = pm
        self.df = pm.df
        self.name = config.get('name')
        self.use_keyboard = config.get('keyboard', False)
        self.config = config.get('settings', {})
        self.active = False
        self.logger = logging.getLogger(__name__)

    def toogle_active(self):
        self.active = not self.active

    def keyboard(self, key):
        pass

    @abstractmethod
    def update(self):
        """Each plugin must implement this method."""
        pass

    @abstractmethod
    def draw(self):
        """Each plugin must implement this method."""
        pass
