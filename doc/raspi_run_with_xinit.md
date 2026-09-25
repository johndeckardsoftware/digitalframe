
---

# Technical Guide: `digitalframe` Setup & Configuration in `xinit` Mode

This guide documents the full system configuration required to run the `digitalframe` application in a lightweight, headless `xinit` environment on Raspberry Pi OS, including video/render permissions and ALSA audio routing.

---

## 1. System Permissions & Dependencies

### Install System Packages

Ensure `xorg`, `xinit`, ALSA utilities, and system packages are installed:

```bash
sudo apt update
sudo apt install -y xserver-xorg xinit x11-xserver-utils wireless-tools alsa-utils

```

### Ensure Correct Permissions & Ownership

Add the `pi` user to hardware access groups (video, input, rendering, console tty, and audio) and ensure workspace ownership:

```bash
sudo usermod -aG video,input,render,tty,sound,audio pi
sudo chown -R pi:pi /home/pi/digitalframe

```

---

## 2. ALSA Audio Configuration (3.5mm Headphone Jack)

To prevent audio device locking between video rendering and voice/sound playback, configure ALSA to route output through `dmix` to the 3.5mm headphone jack (`bcm2835 Headphones`, **Card 2**).

### Configure `~/.asoundrc`

Create or replace `/home/pi/.asoundrc`:

```ini
pcm.!default {
    type plug
    slave.pcm "hw:CARD=Headphones,DEV=0"
}

ctl.!default {
    type hw
    card Headphones
}

```

### Configure Analog Routing & Volume Levels

Set the initial volume for Card Headphones:

```bash
# Set 3.5mm Headphone analog volume level to 100%
amixer -C Headphones sset Headphone 100% 2>/dev/null || amixer -C Headphones sset PCM 100%

# Save volume states permanently across reboots
sudo alsactl store

```

### Verify Sound Output

Test sound playback through the 3.5mm audio jack:

```bash
speaker-test -D plughw:CARD=Headphones,DEV=0 -c 2 -t sine -f 440

```

---

## 3. Startup Script (`run.sh`)

Create `/home/pi/digitalframe/run.sh` to manage environment variables, network readiness checks, screen saver suppression, and process exit code capturing:

```bash
#!/bin/bash

# 1. Define X11 and runtime environment for Raylib
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# Create runtime directory if missing in non-login systemd shells
if [ ! -d "$XDG_RUNTIME_DIR" ]; then
    mkdir -p "$XDG_RUNTIME_DIR"
    chmod 700 "$XDG_RUNTIME_DIR"
fi

# 2. Wi-Fi Verification (Non-blocking)
ssid=$(iwgetid -r)
echo "SSID detected: '$ssid'"

if [ "$ssid" != "FRITZ!Box 7530 FY" ]; then
    echo "Wi-Fi '$ssid' does not match target network."
    # Prevent systemd lockups by checking if shell is interactive[cite: 3]
    if [ -t 0 ]; then
        read -p "Wi-Fi unavailable. Press Ctrl+C to exit..." -t 120
    else
        echo "Non-interactive boot shell detected. Proceeding..."
        sleep 5
    fi
fi

# Disable Wi-Fi power saving
sudo iw dev wlan0 set power_save off 2>/dev/null || true

cd /home/pi/digitalframe || exit 1

LOG="digitalframe.log"
RUN_LOG="runx.log"

# 3. Main xinit Execution Loop
while true; do
    # Launch xinit, disable X11 DPMS/ScreenSaver inside the session, and launch Python[cite: 3]
    xinit /bin/sh -c "xset s off; xset s noblank; xset -dpms; /home/pi/digitalframe/venv/bin/python /home/pi/digitalframe/src/df.py --fullscreen" -- :0 vt1 >> "$LOG" 2>&1
 
    # Read the exit code saved by Python into $ret[cite: 3]
    if [ -f "$RUN_LOG" ]; then
        ret=$(cat "$RUN_LOG" | tr -d '[:space:]')
    else
        ret=128
    fi
 
    # Handle application exit codes[cite: 3]
    if [ "$ret" -eq 0 ]; then
        echo "Exited cleanly."
        break

    elif [ "$ret" -eq 1 ]; then
        echo "Application Error:"
        tail -n 20 "$LOG"
        break

    elif [ "$ret" -eq 100 ]; then
        echo "Rebooting system..."
        sudo poweroff --reboot -f
        break

    elif [ "$ret" -eq 101 ]; then
        echo "Powering down system..."
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

```

Make the script executable:

```bash
chmod +x /home/pi/digitalframe/run.sh

```

---

## 4. Systemd Service Setup

Create the systemd service file to manage startup on Virtual Terminal 1 (`vt1`):

```bash
sudo nano /etc/systemd/system/digitalframe.service

```

Paste the following configuration:

```ini
[Unit]
Description=Digital Photo Frame Application (xinit mode)
After=network-online.target sound.target
Wants=network-online.target sound.target
Conflicts=getty@tty1.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/digitalframe
ExecStart=/bin/bash /home/pi/digitalframe/run.sh
StandardInput=tty
StandardOutput=journal+console
StandardError=journal+console
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target

```

---

## 5. Enable and Start the Service

Reload systemd configurations and enable the boot service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service at boot
sudo systemctl enable digitalframe.service

# Start service immediately
sudo systemctl start digitalframe.service

```

---

## 6. Service Management Commands (via SSH)

Manage or inspect the running `digitalframe` process over SSH:

* **Stop application:** `sudo systemctl stop digitalframe.service`
* **Start application:** `sudo systemctl start digitalframe.service`
* **Restart application:** `sudo systemctl restart digitalframe.service`
* **Check systemd status:** `sudo systemctl status digitalframe.service`
* **Inspect log output:** `tail -n 50 /home/pi/digitalframe/digitalframe.log`