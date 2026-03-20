
**Digitalframe (DF)**

An advanced, modular digital photo frame system developed in Python using **pyray** (Raylib). This project is designed to run seamlessly on both **Windows**, **Linux** and **Raspberry Pi4**, offering fluid rendering of images, videos, and 3D models with deep hardware integration for home automation.

## **🚀 Key Features**

* **Multi-format Support:** Native rendering of images (JPG, PNG, GIF), videos (MP4, AVI) via OpenCV, and 3D models (GLB, OBJ).  
* **Live Folder Monitoring:** Real-time library updates using watchdog. Perfect for syncing files via **SFTP** or network shares without restarting.  
* **Adaptive Brightness:** Automatic monitor brightness adjustment based on ambient light.  
* **Direct hardware integration (Raspberry):**  
  * **PIR Sensor:** Automatic screen power management based on human presence.  
* **Software Integration:**  
  * **HomeAssistant**
	* **Light as Motion sensor** thru MQTT for Automatic screen power management based on human presence and ambient light photo blend 
* **Remote Control Support:** Dynamic key mapping for external HID devices like the BoxPut Remote or BlueDot.  
* **Visual Enhancements:** Automatic "matte" background and borders coloring for a curated aesthetic.

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
   Bash  
   git clone https://github.com/johndeckardsoftware/digitalframe.git  
   cd digitalframe

2. **Install Python dependencies:**  
   Bash  
   pip install \-r requirements.txt

3. **First Run:**  
   On the initial launch, if config.json is missing, the program will prompt you to enter the path for your media folder.

## **⚙️ Media file updates**

The FolderWatch module will detect new files and add them to the slideshow instantly.

## **📝 License**

This project is licensed under the MIT License. See the LICENSE file for details.  
---
