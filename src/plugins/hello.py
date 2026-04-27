
from plugin import PluginWrapper
from dftext import dftext, col_max

class HelloWorldPlugin(PluginWrapper):
    def __init__(self, pm, config):
        super().__init__(pm, config)
        self.y = self.config.get('start_y', 0)
        self.increment = self.config.get('increment', -1)

    def update(self):
        if not self.active: return
        try:
            if not self.df.paused:
                self.y = (self.y + self.increment) % col_max
        except Exception as e:
            self.logger.error(f"{self.name}: {e}")

    def draw(self):
        if not self.active: return
        try:
            dftext(f"Hello it's me: {self.name}", -4, self.y, fs=28, tint=(255,0,0,192), shadow=0)
        except Exception as e:
            self.logger.error(f"{self.name}: {e}")
