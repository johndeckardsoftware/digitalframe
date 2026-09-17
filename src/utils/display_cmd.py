import subprocess, time

def hdmi_is_on(self):
    #
    # https://linuxcommandlibrary.com/man/vcgencmd
    #
    # raspberry vcgencmd
    if self.hdmi_power == 0:
        try:  # vcgencmd only applies to raspberry pi
            state = str(subprocess.check_output(["vcgencmd", "display_power"]))
            if (state.find("display_power=1") != -1):
                return True
            else:
                return False
        except (FileNotFoundError, ValueError, OSError) as e:
            self.logger.error(f"Display ON/OFF is vcgencmd, but an error occurred. {e}")
        return True
    # linux X11 xset
    elif self.hdmi_power == 1:
        try:  # try xset on linux, DPMS has to be enabled
            output = subprocess.check_output(["xset", "-display", ":0", "-q"])
            if output.find(b'Monitor is On') != -1:
                return True
            else:
                return False
        except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError) as e:
            self.logger.error(f"Display ON/OFF is X with dpms enabled, but an error occurred. {e}")
        return True
    # raspberry wlr-randr
    elif self.hdmi_power == 2:
        try:
            output = subprocess.check_output(["wlr-randr"])
            i = output.find(b'HDMI-A-1')
            if i != -1 and output.find(b'Enabled: yes', i) != -1:
                return True
            else:
                return False
        except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError) as e:
            self.logger.error(f"Display ON/OFF is wlr-randr, but an error occurred. {e}")
        return True
    # windows 
    elif self.hdmi_power == 3:
        try:
            return self.display 
        except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError) as e:
            self.logger.error(f"Display ON/OFF windows error: {e}")
        return True
    # linux X11 xrandr
    elif self.hdmi_power == 4:
        try:
            output = subprocess.check_output(["xrandr"])
            i = output.find(b'connected primary')
            if i != -1:
                return True
            else:
                return False
        except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError) as e:
            self.logger.error(f"Display ON/OFF is xrandr, but an error occurred. {e}")
        return True
    else:
        self.logger.warning(f"hdmi_is_on: unsupported {self.hdmi_power=}")
        return True

def hdmi_set(self, on_off):
    # raspberry vcgencmd    
    if self.hdmi_power == 0:
        try:  # vcgencmd only applies to raspberry pi
            if on_off is True:
                subprocess.call(["vcgencmd", "display_power", "1"])
            else:
                subprocess.call(["vcgencmd", "display_power", "0"])
        except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError) as e:
            self.logger.error(f"Display ON/OFF is vcgencmd, but an error occured. {e}")
    # linux X11 xset
    elif self.hdmi_power == 1:
        try:  # try xset on linux, DPMS has to be enabled
            if on_off is True:
                subprocess.call(["xset", "-display", ":0", "dpms", "force", "on"])
            else:
                subprocess.call(["xset", "-display", ":0", "dpms", "force", "off"])
        except (ValueError, TypeError) as e:
            self.logger.error(f"Display ON/OFF is xset via dpms, but an error occured. {e}")
    # raspberry wlr-randr
    elif self.hdmi_power == 2:
        try:  # try wlr-randr for RPi4-5 with wayland desktop
            # check if hdmi is connected
            output = subprocess.check_output(["wlr-randr"])
            i = output.find(b'HDMI-A-1')
            if i != -1:
                if output.find(b'Enabled: yes', i) != -1 and on_off == False:
                    wlr_randr_cmd = ["wlr-randr", "--output", "HDMI-A-1", "--off"]
                    subprocess.call(wlr_randr_cmd)
                elif output.find(b'Enabled: no', i) != -1 and on_off == True:
                    wlr_randr_cmd = ["wlr-randr", "--output", "HDMI-A-1", "--on"]
                    subprocess.call(wlr_randr_cmd)
        except (ValueError, TypeError) as e:
            self.logger.error(f"Display ON/OFF is wlr-randr, but an error occured. {e}")
    # windows
    elif self.hdmi_power == 3:  # windows
        try:
            import ctypes
            WM_SYSCOMMAND = 0x0112
            SC_MONITORPOWER = 0xF170
            # Parametri di stato: 2 = spento, 1 = standby (risparmio), -1 = acceso
            MONITOR_ON = -1
            MONITOR_OFF = 2

            if on_off:
                #ctypes.windll.user32.SendMessageW(-1, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_ON)
                ps_script = """
                $signature = '[DllImport("user32.dll")] public static extern int SendMessage(int hWnd, int hMsg, int wParam, int lParam);'
                $type = Add-Type -MemberDefinition $signature -Name "Win32SendMessage" -Namespace "Win32" -PassThru
                $type::SendMessage(-1, 0x0112, 0xF170, -1)
                """
                proc = subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(2)
                proc.terminate()
                ctypes.windll.user32.mouse_event(0x0001, 1, 1, 0, 0)
                ctypes.windll.user32.mouse_event(0x0001, -1, -1, 0, 0)
            else:
                #ctypes.windll.user32.SendMessageW(-1, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_OFF)
                ps_script = """
                $signature = '[DllImport("user32.dll")] public static extern int SendMessage(int hWnd, int hMsg, int wParam, int lParam);'
                $type = Add-Type -MemberDefinition $signature -Name "Win32SendMessage" -Namespace "Win32" -PassThru
                $type::SendMessage(-1, 0x0112, 0xF170, 2)
                """
                proc = subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(2)
                proc.terminate()
        except Exception as e:
            self.logger.error(f"Display ON/OFF using sendmessage: {e}")
        return True
    # linux X11 xrandr
    elif self.hdmi_power == 4:
        try:
            # check if hdmi is connected
            output = subprocess.check_output(["xrandr", "--listactivemonitors"])
            name = output.decode("utf-8").split(" ")[-1]
            if on_off:
                wlr_randr_cmd = ["xrandr", "--output", name, "--auto"]
                subprocess.call(wlr_randr_cmd)
            else:
                wlr_randr_cmd = ["xrandr", "--output", name, "--off"]
                subprocess.call(wlr_randr_cmd)
        except (ValueError, TypeError) as e:
            self.logger.error(f"Display ON/OFF is xrandr, but an error occured. {e}")
    else:
        self.logger.warning(f"hdmi_set({on_off}: unsupported {self.hdmi_power=}")

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
