
import logging
from monitorcontrol import get_monitors

BRIGHTNESS = "10"
CONTRAST   = "12"

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
vcp_get_error = False
vcp_set_error = False

def get_vcp_value(code):
    global vcp_get_error
    try:
        if code == BRIGHTNESS:
            for monitor in get_monitors():
                with monitor:
                    # monitor.luminance is a built-in helper for VCP code 0x10
                    ret = monitor.get_luminance()
                    return ret
        elif code == CONTRAST:
            for monitor in get_monitors():
                with monitor:
                    # monitor.luminance is a built-in helper for VCP code 0x10
                    ret = monitor.get_contrast()
                    return ret
        else:
            return None
    except Exception as e:
        if not vcp_get_error:
            logger.error(f"Error getting VCP code {code}: {e}")
        vcp_get_error = True
        return None

def set_vcp_value(code, value):
    global vcp_set_error
    try:
        ret = True
        for monitor in get_monitors():
            with monitor:
                # Setup level
                sign = False
                if type(value) == str:
                    level = int(value)
                    if value[0:1] == "+" or value[0:1] == "-":
                        sign = True
                else:
                    level = value

                if code == BRIGHTNESS:
                    # Setup abs/rel level
                    if sign:
                        cur_level = monitor.get_luminance()
                        level = cur_level + level
                    # Ensure the level is within standard VCP bounds
                    level = max(0, min(100, level))
                    # Set
                    monitor.set_luminance(level)

                elif code == CONTRAST:
                    # Set abs/rel level
                    if sign:
                        cur_level = monitor.get_contrast()
                        level = cur_level + level
                    # Ensure the level is within standard VCP bounds
                    level = max(0, min(100, level))

                    monitor.set_contrast(level)
                else:
                    ret = False
            return ret
    except Exception as e:
        if not vcp_set_error:
            logger.error(f"Error setting VCP code {code}: {e}")
        vcp_set_error = True
        return False
