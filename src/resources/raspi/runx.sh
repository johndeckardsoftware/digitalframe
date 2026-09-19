#!/bin/bash

# Define X11 and runtime environment for Raylib
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# Create runtime dir if missing in non-login shells
if [ ! -d "$XDG_RUNTIME_DIR" ]; then
    mkdir -p "$XDG_RUNTIME_DIR"
    chmod 700 "$XDG_RUNTIME_DIR"
fi

ssid=$(iwgetid -r)
echo "SSID: '$ssid'"

if [ "$ssid" != "FRITZ!Box 7530 FY" ]; then
    echo "Wi-Fi '$ssid' not matching target network."
    # Only execute read if running inside an interactive terminal session
    if [ -t 0 ]; then
        read -p "wifi not available, press ctrl C to exit" -t 120
    else
        echo "Non-interactive shell detected. Continuing startup..."
        sleep 5
    fi
fi

# Set power save off (ignore errors if interface isn't up)
sudo iw dev wlan0 set power_save off 2>/dev/null || true

cd /home/pi/digitalframe || exit 1

LOG="digitalframe.log"
RUN_LOG="runx.log"

# Start xinit loop
while true; do
    # Execute xinit including xset configuration directly in the command
    xinit /bin/sh -c "xset s off; xset s noblank; xset -dpms; /home/pi/digitalframe/venv/bin/python /home/pi/digitalframe/src/df.py --fullscreen" -- :0 vt1 >> "$LOG" 2>&1
 
    if [ -f "$RUN_LOG" ]; then
        ret=$(cat "$RUN_LOG" | tr -d '[:space:]')
    else
        ret=128
    fi
 
    if [ "$ret" -eq 0 ]; then
        echo "ok"
        break
    elif [ "$ret" -eq 1 ]; then
        echo "ERROR"
        tail -n 20 "$LOG"
        break
    elif [ "$ret" -eq 100 ]; then
        sudo poweroff --reboot -f
        break
    elif [ "$ret" -eq 101 ]; then
        sudo poweroff --poweroff -f
        break
    elif [ "$ret" -eq 102 ]; then
        echo "Reloading application..."
        sleep 3
    elif [ "$ret" -gt 127 ]; then
        echo "Fatal error:"
        tail -n 20 "$LOG"
        break
    else
        break
    fi
done