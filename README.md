
**Digitalframe**

Simple digital frame application developed in Python using [raylib](https://electronstudio.github.io/raylib-python-cffi/README.html#quickstart). This project is designed to run on homemade digitalframe built around a **Raspberry Pi4** and 4k Monitor. Here a good starting point if you want to build your digitalframe [www.thedigitalpictureframe.com](https://www.thedigitalpictureframe.com/category/build-your-own/). The application works on both **Windows** and **Linux** as well, obviously apart from the specificities of Raspberry. The application can be controlled with a simple wireless keyboard, a Bluetooth remote control, or with home automation systems such as 'Home Assistant'. The focus is on the photographic component, the video and 3D parts are just my attempt to delve deeper into the 3D features of the raylib library. 

## **🚀 Key Features**

* **Multi-format Support:** Native rendering of images (JPG, HEIC, HEIF, TIF), videos (MP4, AVI, MOV, WAV) with the support of OpenCV and ffmpeg, and 3D models (GLB, OBJ).  
* **Visual Enhancements:**
  * Automatic "matte" background and borders depending on image size
  * Matte texture and borders customizable
  * Pairing of vertical images
  * Filter by folder and metadata
* **Direct hardware integration (Raspberry only):**
  * **PIR Sensor:** For automatic screen power management based on human presence.
  * **BH1750 Light Sensor:** For automatic set image brightness to the room lux.
* **Remote Control Support:**
  * Provides an automatic integration into [Home Assistant](https://www.home-assistant.io/) via MQTT discovery.
  * Dynamic key mapping for external HID devices like the BoxPut Remote or Bluedot.  
  * Light and Motion sensor via MQTT for Automatic screen power management based on human presence and ambient light photo blend.
* **Live Folder Monitoring:** Real-time library updates using watchdog. Perfect for syncing files via **SFTP** or network shares without restarting.

## **📂 Project Structure**

| File | Description |
| :---- | :---- |
| df.py | Core engine and main application loop. |
| dfitems.py | Media indexing and scanning logic. |
| dfimage.py | Image handler |
| dfvideo.py | Video handler |
| dfmodel.py | 3D model in .GLB format handler |
| dfshader.py | Shader code wrapper to easily manage shader |
| menu.py | On Screen Menu |
| mqtt.py | Integration with Home Assitant. |
| devices.py | Keyboard and Remote device handler. |
| rpi_bluedot.py | Use Library and App [Bluedot](https://bluedot.readthedocs.io/en/latest/) as a Remote device |
| rpi_pir.py | Manage PIR Sensor directly connected to Raspberry |
| rpi_bh1750.py | Manage BH1750 Light Sensor directly connected to Raspberry |
| config.py | Centralized JSON configuration manager |


## **🛠️ Requirements**

### **Software**

* Python 3.9+  
* Dependencies: raylib, watchdog, psutil, paho-mqtt, exifread, bluedot, evdev, opencv-python, pygltflib, schedule, ffmpeg-python (required ffmpeg install)

## **🔧 Installation & Setup**

1. **Clone the repository:**  
   ```Bash  
   git clone https://github.com/johndeckardsoftware/digitalframe.git  
   cd digitalframe
   ```
2. **Create virtual env (if requested by the system):**  
   ```Bash  
   python -m venv venv/
   source venv/bin/activate
   ```
3. **Install requirements:**  
   ```Bash  
   pip install -r requirements.txt
   ```
4. **Run the application:**
   ```bash
   python ./src/df.py
   ```
   or for fullscreen
   ```
   python ./src/df.py --fullscreen
   ```

5. **First Run:**  
   * On the initial launch, if configuration file is not found, the program will prompt you to enter the path for your media folder and will create a default configuration file.
   * Key ESC to exit and Key F1 for others shortcuts

## **⚙️ Media file updates**

The FolderWatch module will detect new files and add them to the slideshow instantly.

## **🤝 Contributing & Bug Reports**

Contributions, bug reports, and feature requests are always welcome! Whether it is a small typo fix, a new feature, or reporting an issue, your help is appreciated. Please feel free to open an issue or submit a pull request on the GitHub repository.

## **📝 License**

This project is licensed under the MIT License. See the LICENSE file for details.  
---

## Acknowledgements

This software is inspired, or derive parts of the code from the following open source projects:

* [www.thedigitalpictureframe.com](https://www.thedigitalpictureframe.com/)
* https://github.com/helgeerbe/picframe
