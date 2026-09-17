
---

# Alexa skill backend endpoint

This document outlines how to create a local endpoint to manage skill backend.

---

## **Step 0: Install and Configure Ngrok**

Before creating the background service, install `ngrok` on your Raspberry Pi and link it to your ngrok account.

### **1. Install Ngrok**

Run the following commands in your terminal to download and install the official ngrok package:

```bash
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo eval $(dpkg --print-architecture | grep -q arm64 && echo "gpg --dearmor -o /etc/apt/keyrings/ngrok.gpg" || echo "gpg --dearmor -o /usr/share/keyrings/ngrok.gpg")

echo "deb [signed-by=/etc/apt/keyrings/ngrok.gpg] https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list

sudo apt update && sudo apt install ngrok

```

*(Alternatively, download the appropriate binary directly from the [ngrok Download Page](https://ngrok.com/download)).*

### **2. Add Your Authtoken**

To authenticate your installation with your ngrok account:

1. Log in to your [ngrok Dashboard](https://dashboard.ngrok.com/).
2. Retrieve your auth token from the [Your Authtoken](https://dashboard.ngrok.com/get-started/your-authtoken) page.
3. Authenticate the CLI by running:
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN

```



### **3. Claim a Free Static Domain (Optional but Recommended)**

To prevent your endpoint URL from changing every time the Pi reboots:

1. Go to the [ngrok Domains Dashboard](https://www.google.com/search?q=https://dashboard.ngrok.com/cloud-edge/domains).
2. Claim your 1 free static domain (e.g., `your-domain.ngrok-free.app`).

---

## **Step 1: Create a Systemd Service File**

Create a new service definition file using nano:

```bash
sudo nano /etc/systemd/system/ngrok.service

```

Paste the following configuration (replace `pi` with your actual Linux username if different):

```ini
[Unit]
Description=Ngrok Tunnel Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
# Replace 80 with your local port or tunnel configuration name
ExecStart=/usr/local/bin/ngrok http 80
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target

```

**Note:** Make sure the path to `ngrok` is correct. You can check where ngrok is installed on your Pi by running `which ngrok` in your terminal.

---

## **Step 2: Enable and Start the Service**

Reload systemd to pick up the new service file, enable it to launch on boot, and start it immediately:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ngrok.service
sudo systemctl start ngrok.service

```

---

## **Step 3: Verify Service Status**

Check if ngrok is running properly:

```bash
sudo systemctl status ngrok.service

```

To view the live logs or inspect issues:

```bash
journalctl -u ngrok.service -f

```

---

## **Pro-Tip: Fixed URLs vs. Dynamic URLs**

If you are on ngrok's **Free Tier**, a standard command like `ngrok http 80` will generate a random URL every time the Raspberry Pi reboots.

### **Option A: Using a Static Domain (Free Tier includes 1 free static domain)**

If you claimed your free static domain in the [ngrok Domains Dashboard](https://www.google.com/search?q=https://dashboard.ngrok.com/cloud-edge/domains), update `ExecStart` in `/etc/systemd/system/ngrok.service`:

```ini
ExecStart=/usr/local/bin/ngrok http --url=your-domain.ngrok-free.app 80

```

### **Option B: Using the Ngrok Config File**

Alternatively, define your tunnels inside `~/.config/ngrok/ngrok.yml` (for more details, refer to the [ngrok Configuration Documentation](https://ngrok.com/docs/agent/config/)):

```yaml
version: "2"
authtoken: YOUR_AUTHTOKEN
tunnels:
  web_app:
    proto: http
    addr: 80

```

Then update `ExecStart` in your service file to target the named tunnel:

```ini
ExecStart=/usr/local/bin/ngrok start --all

```

After modifying `/etc/systemd/system/ngrok.service`, always run:

```bash
sudo systemctl daemon-reload && sudo systemctl restart ngrok.service

```