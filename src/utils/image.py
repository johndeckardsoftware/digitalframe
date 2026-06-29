import io
import exifread
from pyray import load_image, image_resize, image_copy, ffi, Image
from PIL import Image as PILImage
import pillow_heif
pillow_heif.register_heif_opener()

def fast_image_info(file_path, logger):
    width = height = -1
    tags = {}

    try:
        # Open the image lazily (Pillow reads headers, but does NOT decode pixels yet)
        with PILImage.open(file_path) as img:
            width, height = img.size

            # Extract raw EXIF bytes if they exist
            # Pillow stores this in img.info for HEIF and img.getexif() normally
            exif_bytes = img.info.get("exif")

            if exif_bytes:
                # If the bytes contain the "Exif\x00\x00" header prefix, strip it for exifread
                if exif_bytes.startswith(b"Exif\x00\x00"):
                    exif_bytes = exif_bytes[6:]

                # Wrap bytes in a stream so exifread can process it like a file
                exif_stream = io.BytesIO(exif_bytes)
                tags = exifread.process_file(
                    exif_stream,
                    details=False,
                    builtin_types=True,
                    extract_thumbnail=False
                )

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

def df_load_image(file, logger):
    if file.lower().endswith((".heif", ".heic", ".tif", ".tiff")):
        try:
            # Open the image with Pillow
            with PILImage.open(file) as pil_img:
                # Ensure the image is in RGBA format for Raylib compatibility
                if pil_img.mode != "RGBA":
                    pil_img = pil_img.convert("RGBA")

                width, height = pil_img.size

                # Extract raw image bytes
                raw_bytes = pil_img.tobytes("raw", "RGBA")

                # Create temporary views of the memory
                pixels_raw = ffi.from_buffer("unsigned char *", raw_bytes)
                pixels_ptr = ffi.cast("void *", pixels_raw)

                # Create a temporary local image structure pointing to Python's buffer
                # Format 7 corresponds to PIXELFORMAT_UNCOMPRESSED_R8G8B8A8
                temp_image = Image(pixels_ptr, width, height, 1, 7)

                # ImageCopy deep-copies the pixel data onto Raylib's C-heap.
                # Now Raylib completely owns this memory, and Python's buffer can safely die.
                return image_copy(temp_image)

        except Exception as e:
            logger.error(f"Error loading HEIF image '{file}': {e}")
            return None
    else:
        return load_image(file)
