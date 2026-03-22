
**Digitalframe (DF)**

An advanced, modular digital photo frame system developed in Python using **pyray** (Raylib). This project is designed to run on **Raspberry Pi4** homemade digitalframe [www.thedigitalpictureframe.com](https://www.thedigitalpictureframe.com/) but run seamlessly on both **Windows** and **Linux**, offering fluid rendering of images, videos, and 3D models with deep hardware integration for home automation.

## **🚀 Key Features**

* **Multi-format Support:** Native rendering of images (JPG), videos (MP4, AVI) via OpenCV, and 3D models (GLB, OBJ).  
* **Visual Enhancements:**
  * Automatic "matte" background and borders coloring
  * Matte texture and borders customizable
  * Pairing of vertical images
  * Filter by folder and metadata
* **Direct hardware integration (Raspberry only):**
  * **PIR Sensor:** For automatic screen power management based on human presence.
* **Remote Control Support:**
  * Provides an automatic integration into [Home Assistant](https://www.home-assistant.io/) via MQTT discovery.
  * Dynamic key mapping for external HID devices like the BoxPut Remote or BlueDot.  
  * Light and Motion sensor via MQTT for Automatic screen power management based on human presence and ambient light photo blend.
* **Live Folder Monitoring:** Real-time library updates using watchdog. Perfect for syncing files via **SFTP** or network shares without restarting.

## **📂 Project Structure**

| File | Description |
| :---- | :---- |
| df.py | Core engine and main application loop. |
| config.py | Centralized JSON configuration manager. |
| dfitems.py | Media indexing and scanning logic. |
| devices.py | Interface for PIR sensors, fans, and remote inputs. |
| dfimage.py / dfvideo.py | Dedicated rendering modules for photos and video streams. |
| display.py / ddcutil.py | Utilities for monitor power and brightness control. |
| metrics.py | System resource monitoring (CPU, RAM, Temp). |

## **🛠️ Requirements**

### **Software**

* Python 3.9+  
* Dependencies: raylib, opencv-python, numpy, exifread, psutil, watchdog.

## **🔧 Installation & Setup**

1. **Clone the repository:**  
   ```Bash  
   git clone https://github.com/johndeckardsoftware/digitalframe.git  
   cd digitalframe
   ```
2. **Create virtual env (if requested by teh system):**  
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
5. **First Run:**  
   On the initial launch, if configuration file is not found, the program will prompt you to enter the path for your media folder and will create a default configuration file.

## **⚙️ Media file updates**

The FolderWatch module will detect new files and add them to the slideshow instantly.

## **📝 License**

This project is licensed under the MIT License. See the LICENSE file for details.  
---

## Acknowledgements

This software is inspired, or derive parts of the code from the following open source projects:

* [www.thedigitalpictureframe.com](https://www.thedigitalpictureframe.com/)
* https://github.com/helgeerbe/picframe
