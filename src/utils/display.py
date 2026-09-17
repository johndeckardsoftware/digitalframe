import subprocess
from monitorcontrol import get_monitors, PowerMode

vcp_get_error = False
vcp_set_error = False

def hdmi_is_on(self):
    global vcp_get_error
    if self.hdmi_power >= 0:
        try:
            for monitor in get_monitors():
                with monitor:
                    status = monitor.get_power_mode()
                    return True if status == PowerMode.on else False
            return False
        except Exception as e:
            if not vcp_get_error:
                self.logger.error(f"Error getting VCP power mode: {e}")
            vcp_get_error = True
            return None
    else:
        return None

def hdmi_set(self, on_off):
    global vcp_set_error
    if self.hdmi_power >= 0:
        try:
            for monitor in get_monitors():
                with monitor:
                    status = monitor.get_power_mode()
                    self.logger.debug(f"{on_off=}, {status=}")
                    if on_off == True:
                        if status != PowerMode.on:
                            monitor.set_power_mode(PowerMode.on)
                    else:
                        if status == PowerMode.on:
                            monitor.set_power_mode(PowerMode.standby)
                    status = monitor.get_power_mode()
                    self.logger.debug(f"{status=}")
                    return status
            self.logger.debug(f"no monitor")
            return None
        except Exception as e:
            if not vcp_set_error:
                self.logger.error(f"Error setting VCP power mode: {e}")
            vcp_set_error = True
            return None
    else:
        return None

def hdmi_set_on(self):
    hdmi_set(self, True)
    self.logger.info("hdmi on")

def hdmi_set_off(self):
    hdmi_set(self, False)
    self.logger.info("hdmi off")

def hdmi_is_connected(self):
    try:
        if self.hdmi_power == 2:
            output = subprocess.check_output(["wlr-randr"])
            i = output.find(b'HDMI-A-1')
            if i != -1:
                return True
            else:
                return False
        else:
            return True
    except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError) as e:
        self.logger.info("Unable to check if hdmi port is connected")
        self.logger.info("Cause: %s", e)
        return True

def hdmi_toggle(self):
    if self.display_on():
        self.display_set_off()
    else:
        self.display_set_on()
