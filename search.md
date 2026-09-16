

### **1. Metadata & Tag-Based Search**

Search against EXIF tags, image properties, dates, and file details.

* **Search Tag Parser** (No prefix)
* `Hasselblad` $\rightarrow$ Matches `Hasselblad` anywhere in filename, path, or EXIF values.


* `make:Hasselblad artist:Helmut` $\rightarrow$ Checks if `Image Make` contains `Hasselblad` AND `artist` contains `Helmut`.




* **Context Shortcuts** (`?` prefix)
* `?make == 'Hasselblad' and '2026' in date` $\rightarrow$ Uses explicit shortcuts.


* `?exif_fnumber <= 4 and hue == 'Cool Blue'` $\rightarrow$ Uses dynamically converted tag names (`EXIF FNumber` $\rightarrow$ `exif_fnumber`, `Hue` $\rightarrow$ `hue`).




* **Full Expression** (`=` prefix)
* `=self.width > 2000 and self.ratio > 1.5` $\rightarrow$ Raw Python expression evaluated with full `item` scope.





---

### **2. Content & Visual Search**

Search photos based on visual characteristics and semantic content processed by the background CLIP engine.

* **Natural Language Queries**
* `motorcycle` $\rightarrow$ Matches images containing motorcycles.


* `portrait, beach, sunset` $\rightarrow$ Evaluates semantic similarity across multiple visual concepts.




* **Voice Assistant Commands**
* Direct natural language voice search using Vosk or Alexa integration (e.g., searching for visual concepts via voice prompt).


* Require install of *requirements_torch.txt*
 



---

### EXIF Full / Shortcut Mapping

| EXIF Full Tag | Shortcut Key | Example Value |
| --- | --- | --- |
| **Hue** | `hue` | `"Cool Blue"`<br> |
| **Image Make** | `make` | `"Canon"`<br> |
| **Image Model** | `model` | `"Canon EOS 5D Mark III"`<br> |
| **Image Orientation** | `orientation` | `"Horizontal (normal)"`<br> |
| **Image Software** | `software` | `"Adobe Photoshop CS6 (Windows)"`<br> |
| **Image DateTime** | `datetime` | `"2026-04-23 22:17:12"`<br> |
| **Image Artist** | `artist` | `"Helmut"`<br> |
| **Image Copyright** | `copyright` | `"Helmut Newton"`<br> |
| **EXIF ExposureTime** | `exposuretime` | `0.008`<br> |
| **EXIF FNumber** | `fnumber` | `4`<br> |
| **EXIF ExposureProgram** | `exposureprogram` | `"Aperture Priority"`<br> |
| **EXIF ISOSpeedRatings** | `isospeedratings` | `500`<br> |
| **EXIF RecommendedExposureIndex** | `recommendedexposureindex` | `500`<br> |
| **EXIF ExifVersion** | `exifversion` | `"0230"`<br> |
| **EXIF DateTimeOriginal** | `datetimeoriginal` | `"2013-06-20 14:06:12"`<br> |
| **EXIF DateTimeDigitized** | `datetimedigitized` | `"2013-06-20 14:06:12"`<br> |
| **EXIF ShutterSpeedValue** | `shutterspeedvalue` | `6.965784`<br> |
| **EXIF ApertureValue** | `aperturevalue` | `4`<br> |
| **EXIF ExposureBiasValue** | `exposurebiasvalue` | `0`<br> |
| **EXIF MaxApertureValue** | `maxaperturevalue` | `3`<br> |
| **EXIF MeteringMode** | `meteringmode` | `"Pattern"`<br> |
| **EXIF Flash** | `flash` | `"Flash did not fire, compulsory flash mode"`<br> |
| **EXIF FocalLength** | `focallength` | `67`<br> |
| **EXIF CameraOwnerName** | `cameraownername` | `"Helmut Newton"`<br> |
| **EXIF LensModel** | `lensmodel` | `"EF24-70mm f/2.8L II USM"`<br> |