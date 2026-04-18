import time, threading, logging
from config import Config

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

class PIRSensor():
    def __init__(self, controller):
        self.df = controller
        self.pir_thread = threading.Thread(target=self.handle_pir_sensor)
        self.pir_thread.start()
        self.pir = None
        self.status = ""

    def handle_pir_sensor(self):
        from gpiozero import MotionSensor
        pin = Config.get('pir.pin', 18)
        queue_len = Config.get('pir.queue_len', 10)
        threshold = Config.get('pir.threshold', 0.5)
        wait_time = Config.get('pir.wait_time', 5)
        hdmi_off_timeout = Config.get('window.hdmi_off_timeout', 5)
        self.pir = MotionSensor(pin=pin, queue_len=queue_len, threshold=threshold)
        self.status = "running"
        logger.debug(f"Created MotionSensor: {self.pir.pin=} {self.pir.queue_len=} {self.pir.threshold=}")

        switch_off_time = time.time() + (hdmi_off_timeout * 60)

        while self.status == "running":
            if self.pir.wait_for_motion(wait_time):
                logger.debug(f"motion detected {self.pir.value}")
                if not self.df.display_on():
                    self.df.display_set_on()
                    logger.debug("hdmi on")
                switch_off_time = time.time() + (hdmi_off_timeout * 60)

            if self.pir.wait_for_no_motion(wait_time):
                logger.debug(f"no motion detected {self.pir.value}")
                if self.df.display_on():
                    if time.time() > switch_off_time:
                        self.df.display_set_off()
                        logger.debug("hdmi off")

        self.pir.close()
        self.status = "stopped"

    def stop(self):
        self.status = "stopping"
        self.pir_thread.join()

