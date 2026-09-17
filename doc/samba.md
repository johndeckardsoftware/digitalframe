# How to Share the Digitalframe Folder to be Updated Remotely

Setting up Samba on Linux or Raspberry Pi OS turns your machine into a network file server accessible by Windows, macOS, Linux, and Android clients.

**1. Install Samba**
Update package lists and install Samba along with required utilities:

```bash
sudo apt update
sudo apt install samba samba-common-bin -y

```

**2. Create a Shared Directory**
If the app is not installed (and the directory does not exist yet), create the folder you want to share and adjust permissions so local users can read and write to it:

```bash
sudo mkdir -p /home/pi/Pictures
sudo chmod 777 /home/pi/Pictures

```

*(Note: `/home/pi/Pictures` corresponds to the path configured in the `items.path` key inside `config.json`).*

**3. Configure the Samba Share**
Back up the original configuration file and open it for editing:

```bash
sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.bak
sudo nano /etc/samba/smb.conf

```

Scroll to the very bottom of the file and add your share block using `digitalframe` as the share name:

```ini
[digitalframe]
   path = /home/pi/Pictures
   browseable = yes
   writable = yes
   only guest = no
   create mask = 0777
   directory mask = 0777
   public = no

```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X` in `nano`).

**4. Set a Samba Password**
Samba manages its credentials separately from standard Linux logins. Set a Samba password for your system user (e.g., `pi` or your active username):

```bash
sudo smbpasswd -a pi

```

**5. Start and Enable the Services**
Restart the Samba service to load the changes and enable it to run automatically on boot:

```bash
sudo systemctl restart smbd
sudo systemctl enable smbd

```

**6. Access Your Share**

* **Windows:** Open File Explorer and enter `\\<YOUR_PI_IP>\digitalframe` in the path bar (e.g., `\\192.168.1.50\digitalframe`).
* **macOS:** Open Finder, press `Cmd + K`, and enter `smb://<YOUR_PI_IP>/digitalframe`.
* **Android (Cx File Explorer):**
1. Open Cx File Explorer and go to the **Network** tab.
2. Tap **+ (Add)** and select **Remote** > **Local Network** (or **LAN** / **SMB**).
3. Enter your Raspberry Pi's IP address in the **Host** field (e.g., `192.168.1.50`).
4. Select **Username and Password**, enter `pi` and your Samba password from Step 4, then tap **OK**.
5. Select the `digitalframe` folder to browse and update your media remotely.