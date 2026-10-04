

---

# MQTT Integration Documentation

> 📌 **Note on `{device_id}`:**
> The placeholder `{device_id}` used across topics is configurable in the application settings (`mqtt.device_id`). If not explicitly set, it defaults to **`"digitalframe"`**.
> 
> 

---

## 1. Subscribed Topics (Inbound Commands)

These are the topics the application listens to for incoming commands and external sensor updates.

| Topic | Expected Payload | Description |
| --- | --- | --- |
| `homeassistant/switch/{device_id}/#`<br> | — | General subscription for switch state discovery and command routing. |
| `homeassistant/switch/{device_id}/{switch_name}/set`<br> | `ON` / `OFF`<br> | Receives toggles for switches: `meta_name`, `meta_title`, `meta_caption`, `meta_date`, `meta_location`, `meta_directory`, `meta_off`, `clock`, `shuffle`, `paused`, `monitor`, and `standby`. |
| `homeassistant/button/{device_id}/{button_name}/set`<br> | `ON`<br> | Listens for button presses to control playback: `back` and `next`. |
| `{device_id}/directory`<br> | `string`<br> | Changes the active folder/directory for image rendering. |
| `{device_id}/time_delay`<br> | `float` / `int`<br> | Updates the image display interval duration (`image_ttl`). |
| `{device_id}/location_filter`<br> | `string`<br> | Sets a location query filter for images. |
| `{device_id}/tags_filter`<br> | `string`<br> | Sets image tag filtering constraints. |
| `{device_id}/autosleep`<br> | `float` / `int`<br> | Sets the HDMI display auto-off timeout in seconds. |
| `{device_id}/extra`<br> | `on` / `true` / `1` / `off` / `false` / `0`<br> | Toggles display of private/extra image sets. |
| `{device_id}/stop`<br> | Any | Safely stops the application loops and exits. |
| `{device_id}/reboot`<br> | Any | Reboots the host hardware system. |
| `{device_id}/power_down`<br> | Any | Gracefully shuts down the host hardware system. |
| `{device_id}/keyboard`<br> | `string`<br> | Injects synthetic key events into the input queue. |
| `{configured_state_topic}`<br> | `float` / `int`<br> | Subscribes to custom external devices configured under `mqtt.devices` (e.g., motion or ambient illumination/lux sensors). |

---

## 2. Published Topics (Outbound Discovery & Telemetry)

### Home Assistant Auto-Discovery Configurations (`retain=True`, `qos=0`)



These topics automatically register components in Home Assistant upon client startup.

| Topic | Domain | Registered Entity Name(s) |
| --- | --- | --- |
| `homeassistant/sensor/{device_id}/{topic}/config`<br> | `sensor`<br> | `location_filter`, `tags_filter`, `image_counter`, `image`, `temperature`<br> |
| `homeassistant/text/{device_id}/{topic}/config`<br> | `text`<br> | `location_filter`, `tags_filter`<br> |
| `homeassistant/number/{device_id}/{topic}/config`<br> | `number`<br> | `brightness` (-128 to 128), `time_delay` (1 to 3600), `motion` (0.0 to 100.0), `autosleep` (0.0 to 3600.0) |
| `homeassistant/select/{device_id}/{topic}/config`<br> | `select`<br> | `directory` (populated with available folder options) |
| `homeassistant/switch/{device_id}/{topic}/config`<br> | `switch`<br> | `meta_name`, `meta_title`, `meta_caption`, `meta_date`, `meta_location`, `meta_directory`, `meta_off`, `clock`, `shuffle`, `paused`, `monitor`, `standby`<br> |
| `homeassistant/button/{device_id}/{topic}/config`<br> | `button`<br> | `back`, `next`<br> |

---

### Status, Telemetry, and State Updates

| Topic | Payload Format | Description |
| --- | --- | --- |
| `homeassistant/switch/{device_id}/available`<br> | `online` / `offline`<br> | **Last Will & Testament (LWT):** Broadcasts application availability state. |
| `homeassistant/sensor/{device_id}/state`<br> | `JSON`<br> | Combined telemetry payload published on state update. Key properties include: `directory`, `image_counter`, `location_filter`, `tags_filter`, `time_delay`, `motion`, `brightness`, `lux`, `temperature`, and `autosleep`. |
| `homeassistant/sensor/{device_id}/image/state`<br> | `JSON` (`{"image": "filename.jpg"}`)
 | Publishes the filename of the currently displayed image entity. |
| `homeassistant/sensor/{device_id}/image/attributes`<br> | `JSON`<br> | Transmits EXIF metadata attributes for the current active image. |
| `homeassistant/switch/{device_id}/{switch_name}/state`<br> | `ON` / `OFF`<br> | Reflects binary switch state changes (`paused`, `shuffle`, `monitor`, `standby`, `clock`, `meta_*`). |