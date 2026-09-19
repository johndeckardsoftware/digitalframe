import os
import glob
import time
import subprocess
import logging
from abc import ABC, abstractmethod
from typing import Optional

from monitorcontrol import get_monitors, PowerMode
from config import RunMode

logger = logging.getLogger(__name__)

# ============================================================================
# Driver Interface
# ============================================================================

class BaseDisplayDriver(ABC):
    """Abstract base class for environment-specific display power controls."""

    @abstractmethod
    def set_power(self, on: bool) -> bool:
        """Sets display power state (True=On, False=Standby/Off)."""
        pass

    @abstractmethod
    def get_power(self) -> Optional[bool]:
        """Queries display power state. Returns True if on, False if off/standby, None if unknown."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Checks whether a physical HDMI display is connected."""
        pass


# ============================================================================
# Environment Implementations
# ============================================================================

class X11DisplayDriver(BaseDisplayDriver):
    """Handles Linux X11 display management using xset and sysfs."""

    def set_power(self, on: bool) -> bool:
        try:
            cmd = ["xset", "dpms", "force", "on" if on else "off"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"X11 set_power failed: {e}")
            return False

    def get_power(self) -> Optional[bool]:
        try:
            res = subprocess.run(["xset", "q"], capture_output=True, text=True, timeout=2)
            if "Monitor is On" in res.stdout:
                return True
            elif "Monitor is in Standby" in res.stdout or "Monitor is Off" in res.stdout:
                return False
        except Exception as e:
            logger.error(f"X11 get_power failed: {e}")
        return None

    def is_connected(self) -> bool:
        return _check_sysfs_hdmi()


class WaylandDisplayDriver(BaseDisplayDriver):
    """Handles Wayland compositors via wlr-randr or wlr-output-power-management."""

    def set_power(self, on: bool) -> bool:
        try:
            state = "on" if on else "off"
            # Attempt wlr-randr control
            res = subprocess.run(["wlr-randr", "--output", "HDMI-A-1", f"--{state}"], capture_output=True, text=True, timeout=2)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Wayland set_power failed: {e}")
            return False

    def get_power(self) -> Optional[bool]:
        try:
            res = subprocess.run(["wlr-randr"], capture_output=True, text=True, timeout=2)
            if "HDMI-A-1" in res.stdout:
                return "Enabled" in res.stdout
        except Exception as e:
            logger.error(f"Wayland get_power failed: {e}")
        return None

    def is_connected(self) -> bool:
        try:
            res = subprocess.run(["wlr-randr"], capture_output=True, text=True, timeout=2)
            return "HDMI-A-1" in res.stdout
        except Exception:
            return _check_sysfs_hdmi()


class KmsDrmDisplayDriver(BaseDisplayDriver):
    """Handles direct Linux KMS/DRM / Headless environment via sysfs."""

    def set_power(self, on: bool) -> bool:
        try:
            dpms_files = glob.glob('/sys/class/drm/card*-HDMI-*/dpms')
            val = "On" if on else "Off"
            for fpath in dpms_files:
                with open(fpath, 'w') as f:
                    f.write(val)
            return True
        except Exception as e:
            logger.error(f"KMS/DRM set_power failed: {e}")
            return False

    def get_power(self) -> Optional[bool]:
        try:
            dpms_files = glob.glob('/sys/class/drm/card*-HDMI-*/dpms')
            for fpath in dpms_files:
                with open(fpath, 'r') as f:
                    if f.read().strip() == "On":
                        return True
            return False
        except Exception as e:
            logger.error(f"KMS/DRM get_power failed: {e}")
            return None

    def is_connected(self) -> bool:
        return _check_sysfs_hdmi()


class WindowsDisplayDriver(BaseDisplayDriver):
    """Handles Windows display power states using Win32 API calls."""

    def set_power(self, on: bool) -> bool:
        try:
            import ctypes
            # SC_MONITORPOWER = 0xF170; -1 = On, 2 = Power-off
            power_val = -1 if on else 2
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, power_val)
            return True
        except Exception as e:
            logger.error(f"Windows set_power failed: {e}")
            return False

    def get_power(self) -> Optional[bool]:
        # Windows API does not provide a lightweight query for monitor sleep state
        return None

    def is_connected(self) -> bool:
        return True


class MacOSDisplayDriver(BaseDisplayDriver):
    """Handles macOS display power states using pmset / caffeinate."""

    def set_power(self, on: bool) -> bool:
        try:
            if on:
                subprocess.run(["caffeinate", "-u", "-t", "1"], check=True)
            else:
                subprocess.run(["pmset", "displaysleepnow"], check=True)
            return True
        except Exception as e:
            logger.error(f"macOS set_power failed: {e}")
            return False

    def get_power(self) -> Optional[bool]:
        return None

    def is_connected(self) -> bool:
        return True


class DdcCiDisplayDriver(BaseDisplayDriver):
    """Hardware-level control via monitorcontrol / DDC/CI over I2C."""

    def __init__(self):
        self._vcp_error = False

    def set_power(self, on: bool) -> bool:
        try:
            for monitor in get_monitors():
                with monitor:
                    target_mode = PowerMode.on if on else PowerMode.standby
                    monitor.set_power_mode(target_mode)
                    time.sleep(0.15)  # Delay between I2C writes
                    return True
            return False
        except Exception as e:
            if not self._vcp_error:
                logger.error(f"DDC/CI set_power error: {e}")
                self._vcp_error = True
            return False

    def get_power(self) -> Optional[bool]:
        try:
            for monitor in get_monitors():
                with monitor:
                    status = monitor.get_power_mode()
                    return status == PowerMode.on
            return False
        except Exception as e:
            if not self._vcp_error:
                logger.error(f"DDC/CI get_power error: {e}")
                self._vcp_error = True
            return None

    def is_connected(self) -> bool:
        return _check_sysfs_hdmi()


# ============================================================================
# Helpers & Factory
# ============================================================================

def _check_sysfs_hdmi() -> bool:
    """Helper to query Linux sysfs for connected HDMI ports."""
    try:
        status_files = glob.glob('/sys/class/drm/card*-HDMI-*/status')
        for fpath in status_files:
            with open(fpath, 'r') as f:
                if f.read().strip() == 'connected':
                    return True
        return len(status_files) == 0  # Fallback to True if no files match
    except Exception:
        return True


def get_display_driver(self) -> BaseDisplayDriver:
    """Factory selecting the proper driver based on platform and run mode."""
    # If explicitly configured to use DDC/CI (hdmi_power == 2)
    if getattr(self, 'hdmi_power', None) == 2:
        return DdcCiDisplayDriver()

    platform = getattr(self, 'platform', '').lower()
    run_mode = getattr(self, 'run_mode', None)

    if platform == "windows":
        return WindowsDisplayDriver()
    elif platform == "darwin":
        return MacOSDisplayDriver()
    elif run_mode == RunMode.DESKTOP:
        if os.environ.get("WAYLAND_DISPLAY"):
            return WaylandDisplayDriver()
        return X11DisplayDriver()
    elif run_mode in (RunMode.XINIT, RunMode.DRM):
        if os.environ.get("DISPLAY"):
            return X11DisplayDriver()
        return KmsDrmDisplayDriver()

    return X11DisplayDriver()


# ============================================================================
# Exported Public API (Compatible with DigitalFrame context)
# ============================================================================

def hdmi_is_on(self) -> Optional[bool]:
    driver = get_display_driver(self)
    return driver.get_power()

def hdmi_set(self, on_off: bool) -> Optional[bool]:
    driver = get_display_driver(self)
    success = driver.set_power(on_off)
    if success:
        return driver.get_power()
    return None

def hdmi_set_on(self):
    hdmi_set(self, True)
    self.logger.info("hdmi on")

def hdmi_set_off(self):
    hdmi_set(self, False)
    self.logger.info("hdmi off")

def is_hdmi_connected(self) -> bool:
    driver = get_display_driver(self)
    return driver.is_connected()

def hdmi_toggle(self):
    if hdmi_is_on(self):
        hdmi_set_off(self)
    else:
        hdmi_set_on(self)