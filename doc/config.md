# Configuration Inventory

| Key | Default Value | Description |
| :--- | :--- | :--- |
| bh1750.addr | `35` | Sets the I2C hardware address for the BH1750 light sensor |
| bh1750.enabled | `False` | Enables support for the BH1750 I2C ambient light sensor hardware |
| bh1750.lux_min | `1.0` | Minimum allowed lux reading threshold for the BH1750 sensor |
| bh1750.smbus | `1` | Sets the Linux SMBus/I2C bus ID assigned to the BH1750 sensor |
| bh1750.wait_time | `16` | Sampling interval (in seconds) between BH1750 ambient light level readings |
| bluedot.enabled | `False` | Enables remote control interaction using the BlueDot Bluetooth app |
| boxput.enabled | `False` | enabled |
| boxput.help | `boxput.png` | Remote control key help |
| boxput.wait_time | `10` | wait_time |
| cron.enabled | `True` | enabled |
| fan.pin | `14` | GPIO pin assigned to control the cooling fan relay/transistor |
| fan.sleep | `60` | Delay in seconds between CPU temperature checks for fan control |
| fan.trigger | `50` | CPU temperature threshold in Celsius (°C) that turns on the cooling fan |
| indexer.enabled | `False` | enabled |
| indexer.end | `23:59` | end |
| indexer.labels | `` | labels |
| indexer.max_results | `0` | max_results |
| indexer.recent_labels | `[]` | recent_labels |
| indexer.start | `00:00` | start |
| indexer.threshold | `22` | threshold |
| items.filter | `` | filter |
| items.path | `['/path/to/items']` | Directory paths where media files (images/videos) are indexed and retrieved |
| items.recent_filter | `[]` | recent_filter |
| items.shuffle | `False` | Enables or disables random playback order for slideshow items |
| items.sort | `False` | sort |
| items.types.image.border.file | `emboss-shadow.png` | file |
| items.types.image.borders | `[]` | borders |
| items.types.image.ext | `['.jpg', '.jpeg', '.heic', '.heif', '.tif', '.tiff']` | ext |
| items.types.image.fade | `False` | fade |
| items.types.image.fade_speed | `2.0` | fade_speed |
| items.types.image.histogram.enabled | `False` | enabled |
| items.types.image.matte.channel_mask | `[240, 240, 240]` | channel_mask |
| items.types.image.matte.color | `(200, 200, 200, 255)` | color |
| items.types.image.matte.color_filter | `[0, 255, 0, 255, 0, 255]` | color_filter |
| items.types.image.matte.complement | `False` | complement |
| items.types.image.matte.complementary | `False` | complementary |
| items.types.image.matte.direction | `90` | direction |
| items.types.image.matte.dominant_color | `True` | dominant_color |
| items.types.image.matte.dominant_filter | `[15, 240, 20]` | dominant_filter |
| items.types.image.matte.enabled | `True` | enabled |
| items.types.image.matte.end_color | `(250, 243, 221, 255)` | end_color |
| items.types.image.matte.gradient_factor | `0.1` | gradient_factor |
| items.types.image.matte.help | `Coloring texture 'type' values:
 0=image dominant color,
 1=fixed color (color),
 2=perlin noise using dominat color,
 3=gradient (from start_color to end_color),
 4=gradient of dominat color,
 9=texture original color` | help |
| items.types.image.matte.kiter | `5` | kiter |
| items.types.image.matte.kmeans | `False` | kmeans |
| items.types.image.matte.knum | `2` | knum |
| items.types.image.matte.krnd | `False` | krnd |
| items.types.image.matte.left_margin | `5` | left_margin |
| items.types.image.matte.offset_x | `0` | offset_x |
| items.types.image.matte.offset_y | `0` | offset_y |
| items.types.image.matte.opacity | `16` | opacity |
| items.types.image.matte.scale | `0.5` | scale |
| items.types.image.matte.sfactor | `-0.3` | sfactor |
| items.types.image.matte.shade | `False` | shade |
| items.types.image.matte.start_color | `(247, 226, 162, 255)` | start_color |
| items.types.image.matte.texture | `canvas.jpg` | texture |
| items.types.image.matte.top_margin | `5` | top_margin |
| items.types.image.matte.type | `0` | type: 0: automatic color from image, 1: fixed color specified in "color" key, 2: perlin noise, 3: gradient (start_color, end_color, 4: gradient from "color" key ) |
| items.types.image.mattes | `[]` | mattes |
| items.types.image.metadata | `None` | metadata |
| items.types.image.metadata_format | `` | EXIF show format |
| items.types.image.show_times | `[(60.0, 30.0), (10.0, 60.0), (60.0, 60.0), (15.0, 5.0), (60.0, 10.0)]` | show_times |
| items.types.image.ttl | `60` | ttl |
| items.types.model.angle | `0.0` | angle |
| items.types.model.axes | `[0.0, 1.0, 0.0]` | axes |
| items.types.model.billboard | `False` | billboard |
| items.types.model.billboard_pos | `[0.0, 0.0, -40.0]` | billboard_pos |
| items.types.model.billboard_pro | `False` | billboard_pro |
| items.types.model.billboard_size | `100.0` | billboard_size |
| items.types.model.cam_enabled | `True` | cam_enabled |
| items.types.model.camera.fovy | `50.0` | fovy |
| items.types.model.camera.position | `[0.0, 0.0, 30.0]` | position |
| items.types.model.camera.target | `[0.0, 0.0, 0.0]` | target |
| items.types.model.camera.up | `[0.0, 1.0, 0.0]` | up |
| items.types.model.ext | `['.glb', '.obj', '.gltf']` | ext |
| items.types.model.fps | `24` | fps |
| items.types.model.grid | `False` | grid |
| items.types.model.grid_axis_height | `69.0` | grid_axis_height |
| items.types.model.grid_slices | `1.0` | grid_slices |
| items.types.model.motion_expr | `t * s` | motion_expr |
| items.types.model.pos | `[0.0, 0.0, 0.0]` | pos |
| items.types.model.scale | `1.0` | scale |
| items.types.model.scale_v3 | `[1.0, 1.0, 1.0]` | scale_v3 |
| items.types.model.speed | `1.0` | speed |
| items.types.model.texture | `True` | texture |
| items.types.model.tint | `(255, 255, 255, 255)` | tint |
| items.types.model.ttl | `60` | ttl |
| items.types.model.use_gltf | `False` | use_gltf |
| items.types.video.ext | `['.mp4', '.mpg', '.avi', '.mov']` | ext |
| items.types.video.skip_frames | `False` | skip_frames |
| items.types.video.sound | `False` | sound |
| items.types.video.ttl | `60` | ttl |
| items.types.video.volume | `5` | volume |
| mqtt.client_id | `digitalframe` | client_id |
| mqtt.device_id | `digitalframe` | Unique entity and topic namespace identifier used across MQTT messages |
| mqtt.enabled | `False` | Enables MQTT client integration for Home Assistant integration and remote control |
| mqtt.login | `user` | login |
| mqtt.password | `password` | Authentication password for the MQTT broker connection |
| mqtt.port | `1883` | Network port number used to connect to the MQTT broker |
| mqtt.server | `server` | server |
| mqtt.tls | `` | tls |
| pir.enabled | `False` | Enables passive infrared (PIR) motion sensor hardware integration |
| pir.pin | `18` | GPIO pin number connected to the PIR motion sensor |
| pir.queue_len | `10` | Buffer queue length for smoothing PIR motion sensor state events |
| pir.threshold | `0.5` | Sensitivity threshold for detecting motion via the PIR sensor |
| pir.wait_time | `5` | Polling check interval (in seconds) for motion sensor event evaluation |
| plugins | `[{'enabled': False, 'name': 'HelloWorld', 'module': 'plugins.hello', 'class': 'HelloWorldPlugin', 'menu': [{'g': "f'Toggle HelloWorld ({self.on_off(@active)})'", 'f': '@toggle_active()'}], 'settings': {'start_y': 0, 'increment': -1}}, {'enabled': False, 'name': 'Weather', 'module': 'plugins.weather2', 'class': 'WeatherPlugin', 'menu': [{'g': "f'Toggle Weather ({self.on_off(@active)})'", 'f': '@toggle_active()'}, {'e': "f'Weather Mode < ({@mode}) >'", 'fl': '@get_next_mode(-1)', 'fr': '@get_next_mode(1)'}], 'settings': {'authorize': 'test', 'device_id': 'test', 'mode': 'month', 'dashboard': 'src/resources/weather_dashboard.png'}}, {'enabled': False, 'name': 'Teletext', 'module': 'plugins.teletext', 'class': 'TeletextPlugin', 'keyboard': True, 'menu': [{'g': "f'Toggle Teletext ({self.on_off(@active)})'", 'f': '@toggle_active()'}], 'settings': {'url': 'https://www.televideo.rai.it/televideo/pub/tt4web/Nazionale/', 'cache_expire': 60, 'cache_file': '~/teletext/teletext.json', 'cache_path': '~/teletext', 'zoom': 60}}, {'enabled': False, 'name': 'TextEditor', 'module': 'plugins.text_editor', 'class': 'TextEditor', 'keyboard': True, 'menu': [{'g': "f'Config Editor ({self.on_off(@active)})'", 'f': '@toggle_active()'}], 'settings': {'file_path': 'config.json'}}]` | List of modular application plugins, configurations, and state toggles |
| raylib.log_level | `4` | log_level |
| shader.name | `None` | name |
| timer.enabled | `False` | enabled |
| timer.format | `%H:%M:%S` | format |
| timer.pos | `[1, -2]` | pos |
| timer.size | `36` | size |
| voice.alexa.enabled | `False` | enabled |
| voice.alexa.host | `0.0.0.0` | host |
| voice.alexa.port | `5000` | port |
| voice.alexa.verify_signature | `False` | verify_signature |
| voice.esp32s3.enabled | `False` | enabled |
| voice.esp32s3.esp32_ip | `192.168.1.2` | esp32_ip |
| voice.esp32s3.esp32_port | `5005` | esp32_port |
| voice.esp32s3.host | `0.0.0.0` | host |
| voice.esp32s3.model_path | `vosk-model-small-en-us-0.15` | model_path |
| voice.esp32s3.port | `5005` | port |
| voice.esp32s3.vocabulary | `True` | vocabulary |
| voice.fauxmo.enabled | `False` | enabled |
| voice.lang | `en` | lang |
| voice.piper.enabled | `False` | enabled |
| voice.piper.model_path | `en_US-amy-medium.onnx` | model_path |
| voice.threshold | `90` | threshold |
| window.col_height | `16` | col_height |
| window.col_width | `16` | col_width |
| window.debug_color | `(255, 255, 255, 255)` | debug_color |
| window.error_color | `(255, 0, 0, 255)` | error_color |
| window.font | `LiberationMono-Regular.ttf` | font |
| window.fps | `1` | fps |
| window.fullscreen | `True` | Enables or disables full-screen display mode on startup |
| window.hdmi_off_timeout | `0` | Inactivity timeout (in minutes) before powering off the HDMI output |
| window.hdmi_power | `0` | mode to control hdmi_power: 2: linux/raspberry, 3: windows |
| window.height | `576` | height |
| window.help_color | `(255, 255, 255, 255)` | help_color |
| window.hide_taskbar | `True` | hide_taskbar |
| window.info_color | `(255, 255, 255, 255)` | info_color |
| window.light_average.12 | `200` | dictionary for light_average by month |
| window.light_average.1 | `220` | 1 |
| window.light_average.2 | `240` | 2 |
| window.light_average.3 | `280` | 3 |
| window.light_average.4 | `320` | 4 |
| window.light_average.5 | `360` | 5 |
| window.light_average.6 | `390` | 6 |
| window.light_average.7 | `380` | 7 |
| window.light_average.8 | `360` | 8 |
| window.light_average.9 | `320` | 9 |
| window.light_average.10 | `280` | 10 |
| window.light_average.11 | `240` | 11 |
| window.log_level | `20` | log_level: 10: DEBUG, 20: INFO, 30: WARNING |
| window.lux_adjustment | `40` | adjust number to be added to the sensor value |
| window.max_height | `2160` | max screen height resolution |
| window.max_width | `3840` | max screen width resolution |
| window.menu.max_visible | `24` | max_visible |
| window.menu.menus | `menus_en.json` | menus |
| window.menu.osk_max_visible | `6` | osk_max_visible |
| window.menu.osk_full | `osk_en_layout.json` | osk_full |
| window.menu.osk_numpad | `osk_num_layout.json` | osk_numpad |
| window.menu_key | `KEY_KB_MENU` | Configures the keyboard shortcut key used to invoke the on-screen menu |
| window.metrics_color | `(255, 255, 255, 255)` | metrics_color |
| window.overlay_color | `(255, 255, 255, 192)` | overlay_color |
| window.run_mode | `desktop` | "desktop", "xinit" |
| window.scale_ref_width | `1920` | scale_ref_width |
| window.show_fps | `False` | show_fps |
| window.tags_color | `(200, 200, 200, 255)` | tags_color |
| window.width | `1024` | width |
| window.x | `69` | x |
| window.y | `96` | y |
| cloud.enabled | `False` | Enables background cloud storage folder synchronization via Rclone |
| cloud.sync_jobs | `[{'enabled': False, 'name': 'Google Drive DigitalFrame', 'provider_remote': 'gdrive_df', 'remote_folder': 'DigitalFrame', 'local_path': '/home/pi/Pictures', 'delete_extra_local_files': False}, {'enabled': False, 'name': 'OneDrive DigitalFrame', 'provider_remote': 'onedrive_df', 'remote_folder': 'DigitalFrame', 'local_path': '/home/pi/Pictures', 'delete_extra_local_files': False}, {'enabled': False, 'name': 'Dropbox DigitalFrame', 'provider_remote': 'dropbox_df', 'remote_folder': 'DigitalFrame', 'local_path': '/home/pi/Pictures', 'delete_extra_local_files': False}]` | List of cloud sync job configurations defining remote providers, paths, and options |
