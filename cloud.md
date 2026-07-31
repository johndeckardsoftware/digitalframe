
### Step 1: Install Dependencies

You will need the `rclone` system binary installed on your machine, plus the Python wrapper.

```bash
# Install system binary (macOS / Linux / WSL)
curl https://rclone.org/install.sh | sudo bash

# On Windows (via Winget)
# winget install Rclone.Rclone

# Install Python wrapper
pip install rclone-python

```

---

### Step 2: The JSON Configuration.

Consumer services require an initial authorization step to link your account (creating a "remote" name in Rclone). Your JSON script then references those named remotes and specifies which folders to sync. Every value in sync_job dictionary can be modified.

The following is an example of the "cloud" key in default configuration file 'config.json'

```json
    "cloud": {
        "enabled": false,
        "sync_jobs": [
            {
                "enabled": false,
                "name": "Google Drive DigitalFrame",
                "provider_remote": "gdrive_df",
                "remote_folder": "DigitalFrame",
                "local_path": "/home/pi/Pictures",
                "delete_extra_local_files": false
            },
            {
                "enabled": false,
                "name": "OneDrive DigitalFrame",
                "provider_remote": "onedrive_df",
                "remote_folder": "DigitalFrame",
                "local_path": "/home/pi/Pictures",
                "delete_extra_local_files": false
            },
            {
                "enabled": false,
                "name": "Dropbox DigitalFrame",
                "provider_remote": "dropbox_df",
                "remote_folder": "DigitalFrame",
                "local_path": "/home/pi/Pictures",
                "delete_extra_local_files": false
            }
        ]
    }
```

---

### Step 3: Authorize Your Providers (One-Time Setup)

Before running the Python script, run this command in your terminal **once per cloud provider** to log in via browser:

```bash
rclone config

```

* Press `n` (New remote)
* Name it (e.g., `gdrive_df`, `onedrive_df`, or `dropbox_df` to match your JSON)
* Follow the browser prompt to log into your Google, Microsoft, or Dropbox account.



---

The rclone job is configured to start every hour

```python
schedule.every(1).hours.do(self.cloud_sync)
```

