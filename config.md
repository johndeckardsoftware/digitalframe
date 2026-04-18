# Configuration Inventory

| Key | Default Value | Description |
| :--- | :--- | :--- |
| window.fps | `1` | fps |
| window.show_fps | `false` | show_fps |
| window.hdmi_power | `3` | mode to control hdmi_power: 2: linux/raspberry, 3: windows |
| window.hdmi_off_timeout | `5` | hdmi_off_timeout in minutes |
| window.lux_adjustment | `50` | adjust number to be added to the sensor value |
| window.debug_color | `(255, 255, 255, 255)` | debug_color |
| window.error_color | `(255, 0, 0, 255)` | error_color |
| window.fullscreen | `true` | start app in fullscreen |
| window.max_width | `3840` | max screen width resolution|
| window.max_height | `2160` | max screen height resolution |
| window.width | `1024` | width |
| window.height | `576` | height |
| window.log_level | `20` | log_level: 10: DEBUG, 20: INFO |
| window.x | `69` | startup x window position|
| window.y | `96` | startup y window position|
| window.font | `LiberationMono-Regular.ttf` | font |
| window.info_color | `(255, 255, 255, 255)` | info_color |
| window.tags_color | `(200, 200, 200, 255)` | tags_color |
| window.help_color | `(255, 255, 255, 255)` | help_color |
| window.overlay_color | `(255, 255, 255, 192)` | overlay_color |
| window.metrics_color | `(255, 255, 255, 255)` | metrics_color |
| window.col_height | `16` | col_height |
| window.col_width | `16` | col_width |
| window.menu.scale | `1.6` | scale |
| window.menu.osk_layout | `osk_en_layout.json` | osk_layout |
| window.menu_key | `348` | set to 342 for left alt key |
| window.light_average.12 | `150` | dictionary for light_average by month |
| window.light_average.1 | `150` | 1 |
| window.light_average.2 | `200` | 2 |
| window.light_average.3 | `300` | 3 |
| window.light_average.4 | `400` | 4 |
| window.light_average.5 | `450` | 5 |
| window.light_average.6 | `500` | 6 |
| window.light_average.7 | `500` | 7 |
| window.light_average.8 | `500` | 8 |
| window.light_average.9 | `400` | 9 |
| window.light_average.10 | `300` | 10 |
| window.light_average.11 | `200` | 11 |
| items.types.image.fade | `False` | fade |
| items.types.image.fade_speed | `2.0` | fade_speed |
| items.types.image.borders | `[{"file": "border01t.png", "opacity": 200, "thick": 6}, {"file": "border02t.png", "opacity": 200, "thick": 6}, {"file": "border03t.png", "opacity": 255, "thick": 16}]` | array of predefined borders selectable with key "B". add here your own borders |
| items.types.image.mattes | `[{"texture": "mat_texture1i.jpg", "opacity": 16, "type": 0}, {"texture": "mat_texture3i.jpg", "opacity": 16, "type": 1}, {"texture": "mat_texture4i.jpg", "opacity": 16, "type": 2}, {"texture": "mat_texture5i.jpg", "opacity": 16, "type": 3}, {"texture": "mat_texture6i.jpg", "opacity": 16, "type": 4}, {"texture": "mat_texture7.jpg", "opacity": 16, "type": 9}]` | array of predefined mattes selectable with key "M". add here your own matte |
| items.types.image.show_times | `[(60.0, 30.0), (10.0, 60.0), (60.0, 60.0), (15.0, 5.0), (60.0, 10.0)]` | array show_times tuples (image.ttl, window.hdmi_off_timeout) |
| items.types.image.ttl | `10` | show time of image in seconds |
| items.types.image.border.file | `border02t.png` | border file |
| items.types.image.border.thick | `8` | border thick |
| items.types.image.border.opacity | `200` | border opacity |
| items.types.image.matte.enabled | `true` | enabled |
| items.types.image.matte.type | `0` | type: 0: automatic color from image, 1: fixed color specified in "color" key, 2: perlin noise, 3: gradient (start_color, end_color, 4: gradient from "color" key ) |
| items.types.image.matte.texture | `mat_texture2i.jpg` | texture file|
| items.types.image.matte.opacity | `16` | opacity |
| items.types.image.matte.offset_x | `0` | offset_x |
| items.types.image.matte.offset_y | `0` | offset_y |
| items.types.image.matte.scale | `0.5` | scale |
| items.types.image.matte.direction | `90` | gradient direction (type = 4) |
| items.types.image.matte.color | `(200, 200, 200, 255)` | color |
| items.types.image.matte.start_color | `(247, 226, 162, 255)` | start_color |
| items.types.image.matte.end_color | `(250, 243, 221, 255)` | end_color |
| items.types.image.matte.top_margin | `5` | top_margin |
| items.types.image.matte.left_margin | `5` | left_margin |
| items.types.image.matte.gradient_factor | `0.1` | gradient factor (type = 4) |
| items.types.image.matte.dominant_color | `false` | dominant_color: false: use color_filter and channel_mask, true: use dom_color_filter and dom_color_filter|
| items.types.image.matte.dom_color_filter | `[0, 255, 0, 255, 0, 255]` | dom_color_filter |
| items.types.image.matte.dom_channel_mask | `[255, 255, 255]` | dom_channel_mask |
| items.types.image.matte.color_filter | `[0, 255, 0, 255, 0, 255]` | color_filter |
| items.types.image.matte.channel_mask | `[240, 240, 240]` | channel_mask |
| items.types.image.matte.kmeans | `False` | kmeans |
| items.types.image.matte.knum | `3` | knum |
| items.types.image.matte.complement | `false` | complement: true: complement the color auomatically calculated |
| items.types.image.metadata_format | `` | metadata_format |
| items.types.image.ext | `[".jpg", ".jpeg"]` | ext |
| items.types.image.metadata.title.enabled | false | enable |
| items.types.image.metadata.title.tag | `"Image ImageDescription"` | EXIF tag |
| items.types.image.metadata.caption.enabled | false | enable |
| items.types.image.metadata.caption.tag | `"Image ImageDescription"` | EXIF tag |
| items.types.image.metadata.name.enabled | false | enable |
| items.types.image.metadata.name.enabled | `"=self.name"` | ref to file name |
| items.types.image.metadata.date.enabled | false | enable |
| items.types.image.metadata.date.tag | `EXIF DateTimeOriginal\|Image OriTimeDigitized` | EXIF tag |
| items.types.image.metadata.location.enabled | false | enable |
| items.types.image.metadata.locationtag | `"GPS GPSLatitude&GPS GPSLongitude"` | EXIF tag |
| items.types.image.metadata.directory.enabled | false | enable |
| items.types.image.metadata.directorytag | `"=self.folder"` | ref to file folder |
| items.types.image.metadata_format | `"{name} {title} {caption} {date[:10]} {location} {directory}"` | EXIF show format || items.types.image.histogram.enabled | `false` | enabled |
| items.types.video.ext | `[".mp4", ".mpg", ".avi"]` | ext |
| items.types.video.ttl | `60` | ttl |
| items.types.model.ext | `['.glb', '.obj', '.gltf']` | ext |
| items.types.model.fps | `24` | fps |
| items.types.model.ttl | `60` | ttl |
| items.types.model.use_gltf | `False` | use_gltf |
| items.types.model.angle | `0.0` | angle |
| items.types.model.motion_expr | `t * s` | motion_expr |
| items.types.model.speed | `1.0` | speed |
| items.types.model.scale | `1.0` | scale |
| items.types.model.tint | `(255, 255, 255, 255)` | tint |
| items.types.model.grid | `False` | grid |
| items.types.model.grid_slices | `70` | grid_slices |
| items.types.model.grid_axis_height | `69.0` | grid_axis_height |
| items.types.model.cam_enabled | `True` | cam_enabled |
| items.types.model.camera.fovy | `50.0` | fovy |
| items.types.model.camera.position | `[0.0, 0.0, 30.0]` | position |
| items.types.model.camera.target | `[0.0, 0.0, 0.0]` | target |
| items.types.model.camera.up | `[0.0, 1.0, 0.0]` | up |
| items.types.model.billboard | `False` | billboard |
| items.types.model.billboard_pro | `False` | billboard_pro |
| items.types.model.billboard_size | `100.0` | billboard_size |
| items.types.model.texture | `True` | texture |
| items.types.model.pos | `[0.0, 0.0, 0.0]` | pos |
| items.types.model.axes | `[0.0, 1.0, 0.0]` | axes |
| items.types.model.scale_v3 | `[1.0, 1.0, 1.0]` | scale_v3 |
| items.types.model.billboard_pos | `[0.0, 0.0, -40.0]` | billboard_pos |
| items.path | `["/path/to/items"]` | path of media |
| shader.name | `lightness` | name |
| shader.name.light_gradient.uLightColor| [1.0, 0.9, 0.6] |
| shader.name.light_gradient.uShadowColor | [0.2, 0.2, 0.5] |
| shader.name.light_gradient.uIntensity | 0.0 |
| shader.name.light_gradient.uDirection | 280 |
| shader.name.light_gradient.uSoftness | 3.0 |
| shader.name.fireplace.uIntensity | 0.3 |
| shader.name.fireplace.fps | 12 |
| shader.name.colorwave.uTolerance | 0.5 |
| shader.name.colorwave.fps | 12 |
| items.filter | `` | filter: python expression to filter items |
| timer.enabled | `false` | enable clock show |
| timer.format | `%H:%M:%S` | format |
| timer.size | `-30` | size |
| boxput.enabled | `false` | enable boxput wifi remote. F2 for help |
| boxput.wait_time | `10` | wait_time |
| boxput.help | `boxput.png` | help |
| pir.enabled | `false` | enabled |
| pir.pin | `18` | pin |
| pir.queue_len | `10` | queue_len |
| pir.threshold | `0.5` | threshold |
| pir.wait_time | `5` | wait_time |
| bluedot.enabled | `false` | enabled |
| mqtt.enabled | `false` | enable mqtt for Home Assistant integration or direct sensor connection |
| mqtt.device_id | `digitalframe` | device_id for HA |
| mqtt.server | `server` | server |
| mqtt.port | `1883` | port |
| mqtt.login | `user` | login |
| mqtt.password | `password` | password |
| mqtt.tls | `` | tls |
| mqtt.client_id | `digitalframe` | unique mqtt client id |
