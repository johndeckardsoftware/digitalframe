
# https://datasheet.octopart.com/BH1750FVI-TR-Rohm-datasheet-25365051.pdf
# https://github.com/kplindegaard/smbus2/blob/master/smbus2/smbus2.py

import time, logging, threading
import smbus
from config import Config

logger = logging.getLogger(__name__)

class BH1750():
    """ BH1750 ambient light sensor driver."""
    PWR_OFF = 0x00
    PWR_ON = 0x01
    RESET = 0x07

    # modes
    CONT_LOWRES = 0x13
    CONT_HIRES_1 = 0x10
    CONT_HIRES_2 = 0x11
    ONCE_HIRES_1 = 0x20
    ONCE_HIRES_2 = 0x21
    ONCE_LOWRES = 0x23

    # default addr=0x23 if addr pin floating or pulled to ground
    # addr=0x5c if addr pin pulled high
    #def __init__(self, bus, addr=0x23):
    def __init__(self, controller):
        logger.setLevel(Config.get("window.log_level", logging.INFO))
        #log.setLevel(logging.DEBUG)
        self.df = controller
        self.addr = Config.get('bh1750.addr', 0x23)
        self.bus = smbus.SMBus(Config.get('bh1750.smbus', 1))
        self.wait_time = Config.get('bh1750.wait_time', 0x10)
        self.lux_min = Config.get('bh1750.lux_min', 1.0)
        self.lux = -1
        self.bh1750_thread = threading.Thread(target=self.handle_bh1750, daemon=True)
        self.bh1750_thread.start()
        self.mode = None
        self.status = ""

    def off(self):
        """Turn sensor off."""
        self.set_mode(self.PWR_OFF)

    def on(self):
        """Turn sensor on."""
        self.set_mode(self.PWR_ON)

    def reset(self):
        """Reset sensor, turn on first if required."""
        self.on()
        self.set_mode(self.RESET)

    def set_mode(self, mode):
        """Set sensor mode."""
        self.mode = mode
        self.bus.write_byte(self.addr, mode)

    def luminance(self, mode):
        """Sample luminance (in lux), using specified sensor mode."""
        # continuous modes
        if mode & 0x10 and mode != self.mode:
            self.set_mode(mode)
        # one shot modes
        if mode & 0x20:
            self.set_mode(mode)
        # earlier measurements return previous reading
        time.sleep(0.024 if mode in (0x13, 0x23) else 0.180)
        data = self.bus.read_i2c_block_data(self.addr, mode, 2)
        factor = 2.0 if mode in (0x11, 0x21) else 1.0
        lux = int((data[0]<<8 | data[1]) * (1.28 * factor))
        if lux < self.lux_min: lux = self.lux_min
        return lux

    def handle_bh1750(self):
        try:
            time.sleep(30)
            self.off()
            self.reset()
            logger.info(f"Created BH1750 Sensor thread")
            while True:
                lux = self.luminance(BH1750.ONCE_HIRES_1)
                logger.debug(f"Luminance: {lux}")
                if lux != self.lux:
                    self.lux = lux
                    self.df.set_brightness(lux)
                time.sleep(self.wait_time)

        except Exception as e:
            logger.error(f"{e}")

if __name__ == "__main__":
    config = {}
    light_sensor = BH1750(config, None)
    try:
        while True:
            lux = light_sensor.luminance(BH1750.ONCE_HIRES_1)
            print(f"Luminance: {lux}")
            time.sleep(10)
    except Exception as e:
        print(f"An error occurred: {e}")

