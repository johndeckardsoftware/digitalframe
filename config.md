
### 🖼️ Media & Items (`items`)
This section controls how the software finds, filters, and displays your media files.

| Key | Example / Default | Description |
| :--- | :--- | :--- |
| `items.path` | `["/home/pi/photos"]` | A list of directories to scan for media files. |
| `items.filter` | `""` | A string used to filter filenames (case-insensitive). |
| `items.types.image.ext` | `[".jpg", ".jpeg", ".png"]` | Supported image file extensions. |
| `items.types.image.metadata_format` | `"{DateTimeDigitized}..."` | f-string format for displaying EXIF data (see `dfimage.py`). |
| `items.types.image.histogram.enabled` | `false` | Enables real-time RGB histogram calculation. |
| `items.types.image.matte.enabled` | `true` | Enables adaptive background coloring based on the image. |
| `items.types.image.borders` | `[...]` | A list of overlay border objects (file, opacity, etc.). |
| `items.types.video.ext` | `[".mp4", ".avi", ".mpg"]` | Supported video file extensions. |
| `items.types.video.ttl` | `10` | Maximum playback time (Time To Live) in seconds for videos. |
| `items.types.model.ext` | `[".glb", ".obj"]` | Supported 3D model file extensions. |
| `items.types.model.ttl` | `10` | Display duration for 3D models. |
| `items.types.model.scale` | `0.3` | Default scaling factor for 3D objects. |

### 🖥️ System & Window (`window`)
Configuration for the graphical interface and monitor management.

| Key | Value | Description |
| :--- | :--- | :--- |
| `window.fullscreen` | `true` | Whether to start the app in fullscreen mode. |
| `window.max_width` | `3840` | Maximum horizontal resolution (e.g., for 4K). |
| `window.max_height` | `2160` | Maximum vertical resolution. |
| `window.hdmi_power` | `2` | Power control method (0: vcgencmd, 1: xset, 2: wlr-randr). |
| `window.hdmi_off_timeout` | `5` | Seconds to wait before turning off the HDMI signal. |
| `window.resources` | `"/path/to/res"` | Absolute path to the `resources` folder (fonts, icons). |
| `window.log_level` | `20` | Logging verbosity (20 = INFO, 10 = DEBUG). |
| `window.info_color` | `[255, 255, 255, 255]` | RGBA color for the main On-Screen Display (OSD). |
| `window.light_average` | `{ "1": 150, ... }` | Monthly average Lux mapping for adaptive brightness. |

### 🔌 Hardware & Input (`pir`, `remote`)
Configuration for Raspberry Pi GPIOs and external input devices.

| Key | Value | Description |
| :--- | :--- | :--- |
| `pir.enabled` | `false` | Enables/disables the PIR motion sensor logic. |
| `bluedot.enabled` | `false` | Enables support for the BlueDot Bluetooth remote app. |
| `boxput.enabled` | `true` | Enables support for HID remotes (like BoxPut). |
| `boxput.wait_time` | `0.1` | The polling interval for remote button presses. |

### 🕒 Widgets & Overlay (`timer`)
| Key | Value | Description |
| :--- | :--- | :--- |
| `timer.enabled` | `false` | Toggles the on-screen clock display. |
| `timer.format` | `"%H:%M:%S"` | The strftime format for the clock. |
| `timer.rgba` | `[255, 255, 255, 200]` | Color and opacity of the clock text. |

---

### Note:
By means of `Config.AUTO_SET = True`, any time the code call `Config.get('key', default)` and the key is missing, the application will **automatically add** that key with the default value to the `config.json` upon exit. This makes it very easy to generate a "master" config file simply by running the app once.
