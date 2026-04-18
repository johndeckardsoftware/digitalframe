import time, threading, logging
from config import Config

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

class FanController():
    def __init__(self, controller):
        self.df = controller
        self.fan_thread = threading.Thread(target=self.handle_fan)
        self.fan_thread.start()
        self.fan_device = None
        self.status = ""
        self.count = 0

    def handle_fan(self):
        from utils.metrics import get_cpu_temp
        try:
            from gpiozero import OutputDevice
            pin = Config.get('fan.pin', 14)
            trigger = Config.get('fan.trigger', 50)
            sleep = Config.get('fan.sleep', 60)
            self.fan_device = OutputDevice(pin=pin)
            self.status = "running"
            logger.info(f"Fan controller started")

            while self.status == "running":
                temp = get_cpu_temp()
                if temp > trigger:
                    self.fan_device.on()
                else:
                    self.fan_device.off()
                time.sleep(sleep)

            if self.fan_device:
                self.fan_device.close()
            self.status = "stopped"
            logger.info(f"Fan controller {self.status}")
        except Exception as e:
            logger.error(e)

    def stop(self):
        try:
            self.status = "stopping"
            logger.info(f"Fan controller {self.status}")
            self.fan_thread.join()
        except Exception as e:
            logger.error(e)
