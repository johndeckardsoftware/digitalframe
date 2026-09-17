

> 📌 **Note on `{device_id}`:**
> The placeholder `{device_id}` used in the topics below is fully configurable via the application's configuration file (`mqtt.device_id`). If it is not explicitly set, it defaults to **`"digitalframe"`**.

---

## 1. Subscribed Topics (Inbound Commands)

These are the topics the script listens to for incoming commands from Home Assistant or another MQTT client to control the digital frame.

| Topic | Description |
| --- | --- |
| `homeassistant/switch/{device_id}/#` | General Home Assistant discovery and control subscription path. |
| `homeassistant/switch/{device_id}_{switch_name}/set` | Receives toggles (`ON`/`OFF`) for various switches: `display`, `clock`, `shuffle`, `paused`, and several text overlays (`title_toggle`, `caption_toggle`, `name_toggle`, `date_toggle`, `location_toggle`, `directory_toggle`, `text_off`). |
| `homeassistant/button/{device_id}_{button_name}/set` | Listens for a payload of `ON` to trigger button press simulations for navigating images: `_back/set` and `_next/set`. |
| `{device_id}/directory` | Receives a string parameter to dynamically change the active folder/subdirectory of images. |
| `{device_id}/time_delay` | Receives a value to change the image transition duration (`image_ttl`). |
| `{device_id}/brightness` | Receives a value to adjust the display brightness. |
| `{device_id}/location_filter` | Receives text input to filter images based on geographic location. |
| `{device_id}/tags_filter` | Receives text input to filter images based on specific tags. |
| `{device_id}/motion` | Receives data to manage motion-sensor behavior or levels. |
| `{device_id}/autosleep` | Receives timeout configurations (in seconds) for turning off the display automatically. |
| `{device_id}/extra` | Receives a boolean value (`on`/`true`/`1`) to toggle the inclusion of private/hidden files. |
| `{device_id}/stop` | Shuts down the application logic gracefully. |
| `{device_id}/reboot` | Triggers a hardware system reboot. |
| `{device_id}/power_down` | Triggers a hardware system shutdown. |
| `{device_id}/keyboard` | Receives key strokes to simulate a virtual keyboard interface. |
| `{device_id}/image_counter` | Subscribes to its own metric (likely registered during configuration setups). |
| `{device_id}/image` | Subscribes to its own metric (registered during configuration setups). |
| `{device_id}/temperature` | Subscribes to its own metric (registered during configuration setups). |

---

## 2. Published Topics (Outbound Discovery & State)

These are the topics where the script pushes configuration setups for Home Assistant MQTT Discovery, telemetry data, and device status updates.

### Home Assistant Auto-Discovery Configurations

These payloads are published with `retain=True` on startup to automatically expose entities inside Home Assistant.

| Topic | Description |
| --- | --- |
| `homeassistant/sensor/{device_id}_{sensor_name}/config` | Registers entities for telemetry data: `image_counter` and `image`. |
| `homeassistant/text/{device_id}_{text_name}/config` | Registers input text filters: `location_filter` and `tags_filter`. |
| `homeassistant/number/{device_id}_{number_name}/config` | Registers configuration adjustments: `brightness`, `time_delay`, `motion`, and `autosleep`. |
| `homeassistant/select/{device_id}_directory/config` | Registers a dropdown selection entity containing the available image directory list. |
| `homeassistant/switch/{device_id}_{switch_name}/config` | Registers all binary switches (`display`, `paused`, text toggles, etc.). |
| `homeassistant/button/{device_id}_{button_name}/config` | Registers interaction buttons (`back`, `next`). |

### Status, Telemetry, and State Changes

These topics handle the actual runtime values of the frame's states and diagnostic metrics.

| Topic | Description |
| --- | --- |
| `homeassistant/switch/{device_id}/available` | **Availability Topic / Last Will:** Broadcasts `"online"` on connect, and `"offline"` on app disconnect to monitor frame connection status. |
| `homeassistant/sensor/{device_id}_image/state` | Sends a JSON payload representing the filename of the currently rendered image. |
| `homeassistant/sensor/{device_id}_image/attributes` | Transmits custom metadata properties belonging to the current active image. |
| `homeassistant/sensor/{device_id}/state` | A unified JSON payload packing concurrent values for: `directory`, `image_counter`, `location_filter`, `tags_filter`, `time_delay`, `motion`, `brightness`, `temperature`, and `autosleep`. |
| `homeassistant/switch/{device_id}_{switch_name}/state` | Publishes regular states (`ON`/`OFF`) whenever switches like `paused`, `shuffle`, `display`, or the configuration display toggles are switched manually or updated programmatically. |