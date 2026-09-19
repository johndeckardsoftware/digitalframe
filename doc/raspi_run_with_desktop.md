# Digitalframe Application - Raspberry Pi autorun guide

## 1. Application autorun Script Example

```bash
#!/bin/bash

ssid=$(iwgetid -r)
echo "'$ssid'"

if [ "$ssid" != "YOUR WIFI SSID" ]; then
    read -p "wifi not available, press ctrl C to exit" -t 120
fi

sudo iw dev wlan0 set power_save off

cd /home/pi/digitalframe

LOG="digitalframe.log"

if grep -q "ERROR" $LOG; then
    echo "errors from last run:"
    tail -40 digitalframe.log
    read -p "Press key to continue.. " -n1 -s
    cp $LOG $LOG.old
    rm $LOG
else
    # Start a loop that runs indefinitely until an explicit exit or reboot occurs
    while true; do
        /home/pi/digitalframe/venv/bin/python /home/pi/digitalframe/src/df.py --fullscreen >> $LOG 2>&1
        ret=$?
        echo $ret > run.log

        if [ $ret -eq 0 ]; then
            echo "ok"
            break  # Exit the loop and finish the script

        elif [ $ret -eq 1 ]; then
            echo "ERROR"
            tail -n 20 $LOG
            break  # Exit the loop on standard error

        elif [ $ret -eq 100 ]; then
            sudo poweroff --reboot -f
            break

        elif [ $ret -eq 101 ]; then
            sudo poweroff --poweroff -f
            break

        elif [ $ret -eq 102 ]; then
            echo "Reloading application..."
            # Do NOT break. The loop will naturally cycle back to the top
            # and re-execute the python command.
            sleep 3  # Optional: short delay to prevent aggressive looping if something goes wrong

        elif [ $ret -gt 127 ]; then
            echo "Fatal error:"
            tail -n 20 $LOG
            break  # Exit the loop on fatal errors
        else
            # Fallback for any other unhandled exit codes so the script doesn't loop infinitely by mistake
            break
        fi
    done
fi

```

---

## 2. Shell Script Operational Architecture

The execution steps inside the lifecycle management script handle runtime configurations seamlessly:

* **Network Guardrails:** Verifies connectivity targeting your explicitly defined local hardware station (`YOUR WIFI SSID`). If a target base connection is missing, it creates a 120-second manual exit window before continuing.
* **Power Efficiency Management:** Disables background power-saving toggles via `iw dev wlan0 set power_save off` to eliminate interface latency drops while streaming or using network-dependent features like the *Weather* and *Teletext* plugins.
* **Fail-Safe Logs Inspection:** Inspects historical output arrays for trace string markers matching `"ERROR"`. If errors are discovered, it catches execution context, visually outputs the last 40 lines, flushes logs to a secondary cache file (`digitalframe.log.old`), and prompts for a manual bypass trigger.
* **Application Exit Code Mapping:** The underlying Python ecosystem (`df.py`) maps programmatic state transitions to platform exit signals:
* `0`: Application gracefully closed or suspended.
* `1`: Critical application logic error encountered.
* `100`: Hardware system reboot command triggered.
* `101`: Hardware system shutdown command triggered.
* `102`: Close and reload application.
* `> 127`: Fatal segmentation or process isolation faults.



---

## 3. Configuration & Permissions 

To configure this framework cleanly inside your target Linux operating environment, configure the directory mapping and executable tracking fields as follows:

```bash
# Ensure target paths match script environment setups
mkdir -p /home/pi/digitalframe

# Apply executable execution rights over script file
chmod +x /home/pi/digitalframe/run.sh

```

### Auto-Start via Desktop Autorun (.desktop entry)

To run the digital frame application automatically when the graphical desktop environment loads, create an autostart directory and desktop entry file:

```bash
# Create the user-level autostart directory if it doesn't exist
mkdir -p /home/pi/.config/autostart

# Create and edit the autostart entry file
nano /home/pi/.config/autostart/digitalframe.desktop

```

Paste the following configurations into the file:

```ini
[Desktop Entry]
Type=Application
Name=digitalframe
Exec=/home/pi/digitalframe/run.sh
Path=/home/pi/digitalframe
GenericName=digitalframe
StartupNotify=true
Terminal=true


```


## 4. Monitor utilities

```bash
# Set monitor to 1920x1080
wlr-randr --output HDMI-A-1 --mode 1920x1080
```

```bash
# Set monitor to 3840x2160
wlr-randr --output HDMI-A-1 --mode 3840x2160
```

```bash
# Set monitor on
wlr-randr --output HDMI-A-1 --on
```

```bash
# Set monitor off
wlr-randr --output HDMI-A-1 --off
```

