
**Digital Frame (DF)**

An advanced, modular digital photo frame system developed in Python using **pyray** (Raylib). This project is designed to run seamlessly on both **Windows** and **Raspberry Pi**, offering fluid rendering of images, videos, and 3D models with deep hardware integration for home automation.

## **🚀 Key Features**

* **Multi-format Support:** Native rendering of images (JPG, PNG, GIF), videos (MP4, AVI) via OpenCV, and 3D models (GLB, OBJ).  
* **Intelligent Path Handling:** Automatic normalization of "Linux-style" paths even when running on Windows environments.  
* **Live Folder Monitoring:** Real-time library updates using watchdog. Perfect for syncing files via **SFTP** or network shares without restarting.  
* **Hardware Integration:**  
  * **PIR Sensor:** Automatic screen power management (HDMI CEC/DPMS) based on human presence.  
  * **Active Cooling:** Fan controller logic based on real-time CPU temperature.  
  * **Adaptive Brightness:** Automatic monitor adjustment (via DDC/CI on Windows/Linux) based on ambient light or seasonal lux averages.  
* **Remote Control Support:** Dynamic key mapping for external HID devices like the BoxPut Remote or BlueDot.  
* **Visual Enhancements:** Real-time histogram calculation and smart "matte" background coloring for a curated aesthetic.

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

### **Hardware (Optional)**

* **Raspberry Pi:** For GPIO-based features (PIR).  
* **DDC/CI Compatible Monitor:** Required for the auto-brightness features.

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

## **⚙️ SFTP Workflow (Windows)**

To remotely upload images to your Windows-based frame:

1. Enable **OpenSSH Server** via Windows Optional Features.  
2. Start the sshd service in services.msc.  
3. Connect using any SFTP client (like FileZilla or WinSCP).  
4. The FolderWatch module will detect new files and add them to the slideshow instantly, provided they exceed the minimum valid file size.

## **📝 License**

This project is licensed under the MIT License. See the LICENSE file for details.  
---
