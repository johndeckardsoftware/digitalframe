
from pathlib import Path

def is_raspberry_pi():
    try:
        with open('/sys/firmware/devicetree/base/model', 'r') as f:
            model = f.read().lower()
            return 'raspberry pi' in model
    except FileNotFoundError:
        return False

def get_os_version():
    # This returns a string like '12.5' or '13.0'
    version = open('/etc/debian_version').read().strip()
    if version.startswith('12'):
        return "12" # Bookworm
    elif version.startswith('13'):
        return "13" # Trixie
    else:
        return version

# if enable: set autohide=true and notify_enable=false
# else:  set autohide=false and notify_enable=true
def set_autohide_and_notification(enable):
    if not is_raspberry_pi(): return
    version = get_os_version()
    if version == "12" or version == "13":
        
        if enable:
            old_autohide = f"autohide=false"
            old_notifiy_enable = f"notify_enable=true"
            new_autohide = f"autohide=true"
            new_notifiy_enable = f"notify_enable=false"
        else:
            old_autohide = f"autohide=true"
            old_notifiy_enable = f"notify_enable=false"
            new_autohide = f"autohide=false"
            new_notifiy_enable = f"notify_enable=true"

        home = Path.home()
        wf_panel_pi = home / ".config/wf-panel-pi/wf-panel-pi.ini"
        content = open(wf_panel_pi).read()
        i = content.find("autohide=")
        if i != -1:
            new_content = content.replace(old_autohide, new_autohide)
        else:
            new_content = content + new_autohide + "\n"

        i = content.find("notify_enable=")
        if i != -1:
            new_content = new_content.replace(old_notifiy_enable, new_notifiy_enable)
        else:
            new_content = new_content + new_notifiy_enable + "\n"

        if content != new_content:
            with open(wf_panel_pi, 'w') as f:
                f.write(new_content)

if __name__ == "__main__":
    set_autohide_and_notification(True)

"""
[panel]
position=bottom
icon_size=16
autohide=false
autohide_duration=500
edge_offset=200
window-list_max_width=150
monitor=NOOP-1
widgets_left=smenu spacing0 spacing4 launchers spacing8 window-list
widgets_right=tray power ejecter updater spacing2 connect spacing2 bluetooth spacing2 netman spacing2 volumepulse spacing2 clock spacing2 batt spacing2 squeek cputemp
notify_enable=false
notify_timeout=0
"""