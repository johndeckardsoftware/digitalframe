import os, struct
import exifread
from pyray import image_resize

def fast_image_info(file_path, logger):
    height = width = -1
    tags = None
    try:
        size = os.path.getsize(file_path)

        with open(file_path, mode="rb") as input:
            data = input.read(25)

            if size >= 10 and data[:6] in ('GIF87a', 'GIF89a'):
                # GIFs
                w, h = struct.unpack("<HH", data[6:10])
                width = int(w)
                height = int(h)
            elif (size >= 24 and data.startswith(b'\211PNG\r\n\032\n')
                and data[12:16] == b'IHDR'):
                # PNGs
                w, h = struct.unpack(">LL", data[16:24])
                width = int(w)
                height = int(h)
            elif size >= 16 and data.startswith(b'\211PNG\r\n\032\n'):
                # older PNGs?
                w, h = struct.unpack(">LL", data[8:16])
                width = int(w)
                height = int(h)
            elif (size >= 2) and data.startswith(b'\377\330'):
                # JPEG
                input.seek(0)
                input.read(2)
                b = input.read(1)
                while (b and ord(b) != 0xDA):
                    while (ord(b) != 0xFF): b = input.read(1)
                    while (ord(b) == 0xFF): b = input.read(1)
                    if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                        input.read(3)
                        h, w = struct.unpack(">HH", input.read(4))
                        break
                    else:
                        input.read(int(struct.unpack(">H", input.read(2))[0])-2)
                    b = input.read(1)
                width = int(w)
                height = int(h)

                # get metadata
                input.seek(0)
                tags = exifread.process_file(input, details=False, builtin_types=True, extract_thumbnail=False)

    except Exception as e:
        logger.error(f"fast_image_info: ({file_path}) {e}")

    return width, height, tags

def resize_to_percentage(image, screen_width, screen_height, percentage):
    orig_w = image.width
    orig_h = image.height

    if percentage == 100 and orig_w == screen_width: return

    # Calculate target constraints
    target_w = screen_width * (percentage / 100)
    target_h = screen_height * (percentage / 100)

    # Determine the scaling factor (the "limiting" side)
    # This formula ensures the image stays within bounds while keeping ratio
    ratio = min(target_w / orig_w, target_h / orig_h)

    # Calculate new dimensions
    new_w = int(orig_w * ratio)
    new_h = int(orig_h * ratio)

    # Resize and return
    image_resize(image, new_w, new_h)