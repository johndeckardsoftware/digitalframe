import threading, logging
from config import Config
from pyray import KeyboardKey

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

class BlueDotRemote():
    def __init__(self, controller, devices):
        self.df = controller
        self.devices = devices
        self.bluedot_thread = threading.Thread(target=self.handle_bluedot)
        self.bluedot_thread.start()
        self.bluedot = None
        self.status = ""
        self.count = 0

    def btn_up(self):
        self.devices.keyboard(vkey=KeyboardKey.KEY_UP)

    def btn_down(self):
        self.devices.keyboard(vkey=KeyboardKey.KEY_DOWN)

    def btn_left(self):
        self.devices.keyboard(vkey=KeyboardKey.KEY_LEFT)

    def btn_right(self):
        self.devices.keyboard(vkey=KeyboardKey.KEY_RIGHT)

    def btn_select(self):
        self.devices.keyboard(vkey=KeyboardKey.KEY_ENTER)

    def btn_menu(self):
        self.devices.keyboard(vkey=KeyboardKey.KEY_KB_MENU)

    def btn_end(self):
        self.devices.keyboard(vkey=KeyboardKey.KEY_END)

    def on_client_connects(self):
        logger.info(f"BlueDot client connected. {self.bluedot.paired_devices}")

    def on_client_disconnects(self):
        logger.info(f"BlueDot client disconnected.")

    def handle_bluedot(self):
        try:
            from bluedot import BlueDot
            self.bluedot = BlueDot(cols=3, rows=4, print_messages=False)

            # configure dot matrix (cols, rows)                
            self.bluedot[0, 0].border = True
            self.bluedot[0, 0].square = True
            self.bluedot[0, 0].color = (0, 0, 255)
            self.bluedot[0, 0].when_pressed = self.btn_menu
            self.bluedot[1, 0].visible = False
            self.bluedot[2, 0].border = True
            self.bluedot[2, 0].square = True
            self.bluedot[2, 0].color = (0, 255, 255)
            self.bluedot[2, 0].when_pressed = self.btn_end

            self.bluedot[0, 1].visible = False
            self.bluedot[1, 1].border = True
            self.bluedot[1, 1].color = (255, 0, 0)
            self.bluedot[1, 1].when_pressed = self.btn_up
            self.bluedot[2, 1].visible = False

            self.bluedot[0, 2].border = True
            self.bluedot[0, 2].color = (255, 0, 0)
            self.bluedot[0, 2].when_pressed = self.btn_left
            self.bluedot[1, 2].border = True
            self.bluedot[1, 2].color = (0, 255, 0)
            self.bluedot[1, 2].when_pressed = self.btn_select
            self.bluedot[2, 2].border = True
            self.bluedot[2, 2].color = (255, 0, 0)
            self.bluedot[2, 2].when_pressed = self.btn_right

            self.bluedot[0, 3].visible = False
            self.bluedot[1, 3].border = True
            self.bluedot[1, 3].color = (255, 0, 0)
            self.bluedot[1, 3].when_pressed = self.btn_down
            self.bluedot[2, 3].visible = False

            self.bluedot.when_client_connects = self.on_client_connects
            self.bluedot.when_client_disconnects = self.on_client_disconnects

            self.status = "running"
            logger.info(f"BlueDot server started")

            while self.status == "running":
                if self.bluedot.wait_for_press(5):
                    pass

            if self.bluedot:
                self.bluedot.stop()
            self.status = "stopped"
            logger.info(f"BlueDot {self.status}")
        except Exception as e:
            logger.error(e)

    def stop(self):
        try:
            self.status = "stopping"
            logger.info(f"BlueDot {self.status}")
            self.bluedot_thread.join()
        except Exception as e:
            logger.error(e)

