from array import array
from config import Config
from pyray import *

class Histogram:
    def __init__(self, name, image):
        self.name = name
        self.image = image
        self.histogram_r = None
        self.histogram_r_max = 1
        self.histogram_g = None
        self.histogram_g_max = 1
        self.histogram_b = None
        self.histogram_b_max = 1
        self.scale = 10             # work on a scaled image
        self.mat_r = 0
        self.mat_g = 0
        self.mat_b = 0
        self.process(image)

    def process(self, image):
        image2: Image = image_copy(image)
        image_resize(image2, image.width // self.scale, image.height // self.scale)
        #export_image(image2, "histogram_image.jpg")

        if Config.get('items.types.image.histogram.enabled', False):
            self.create_histogram(image2)

        if Config.get('items.types.image.matte.enabled', True):
            self.calc_mat_color(image2)

        unload_image(image2)

    def create_histogram(self, image):
        # --- channels histogram calculation ---
        pixels = load_image_colors(image)
        self.histogram_r = array("I", [0] * 256) # 256 possible intensity levels (0-255)
        self.histogram_g = array("I", [0] * 256) # 256 possible intensity levels (0-255)
        self.histogram_b = array("I", [0] * 256) # 256 possible intensity levels (0-255)

        i = 0
        while i < image.width * image.height:
            self.histogram_r[pixels[i].r] += 1
            self.histogram_g[pixels[i].g] += 1
            self.histogram_b[pixels[i].b] += 1
            i += 1

        unload_image_colors(pixels)

    def get_histogram_dominat_color(self):
        r = g = b = 0
        r_max = g_max = b_max = 0
        for i in range(5, 250):
            if self.histogram_r[i] > r_max:
                r_max = self.histogram_r[i]
                r = i
            if self.histogram_g[i] > g_max:
                g_max = self.histogram_g[i]
                g = i
            if self.histogram_b[i] > b_max:
                b_max = self.histogram_b[i]
                b = i

        return (r, g, b, 255)

    def calc_mat_color(self, image):

        if Config.get('items.types.image.matte.dominant_color', False):
            color_filter = Config.get('items.types.image.matte.dom_color_filter', [0,255, 0,255, 0,255])
            channel_mask = Config.get('items.types.image.matte.dom_channel_mask', [0xff, 0xff, 0xff])
        else:
            #color_filter = Config.get('items.types.image.matte.color_filter_skin', [140,255, 0,172, 0,124]) #skin
            color_filter = Config.get('items.types.image.matte.color_filter', [0,255, 0,255, 0,255])
            channel_mask = Config.get('items.types.image.matte.channel_mask', [0xf0, 0xf0, 0xf0])

        flr = color_filter[0]
        fhr = color_filter[1]
        flg = color_filter[2]
        fhg = color_filter[3]
        flb = color_filter[4]
        fhb = color_filter[5]

        mr = channel_mask[0]
        mg = channel_mask[1]
        mb = channel_mask[2]

        rgb = 255 << 16
        count = {}
        for x in range(0, image.width):
            for y in range(0, image.height):
                c = get_image_color(image, x, y)
                if c.r >= flr and c.r <= fhr and c.g >= flg and c.g <= fhg and c.b >= flb and c.b <= fhb:
                    rgb = ((c.r & mr) << 16) | ((c.g & mg) << 8) | (c.b & mb)
                    if rgb in count:
                        count[rgb] += 1
                    else:
                        count[rgb] = 1

        vmax = 0
        for k, v in count.items():
            if v > vmax:
                vmax = v
                rgb = k

        if Config.get('items.types.image.matte.complement', False):
            self.mat_r = 255 - (rgb >> 16)
            self.mat_g = 255 - (rgb >> 8 & 0xff)
            self.mat_b = 255 - (rgb & 0xff)
        else:
            self.mat_r = rgb >> 16
            self.mat_g = rgb >> 8 & 0xff
            self.mat_b = rgb & 0xff

    def get_mat_color(self):

        return (self.mat_r, self.mat_g, self.mat_b, 255)

    def kernel_convolution(self, image, kernel_matrix=None):
        if not kernel_matrix:
            # 2. Definisci il kernel (matrice 3x3 appiattita)
            # Esempio: Sharpen (accentua i bordi)
            #  0 -1  0
            # -1  5 -1
            #  0 -1  0
            kernel_matrix = [
                0.0, -1.0,  0.0,
                -1.0,  5.0, -1.0,
                0.0, -1.0,  0.0
            ]

        # Converte la lista Python in un array di float C
        kernel = ffi.new("float[]", kernel_matrix)

        # 3. Applica la convoluzione
        # Nota: la funzione modifica direttamente l'oggetto 'image'
        image_kernel_convolution(image, ffi.cast("float *", kernel), len(kernel_matrix))

    def image_palette(self, image):
        color_count_ptr = ffi.new('int *')
        max_colors = 256
        palette = load_image_palette(image, max_colors, color_count_ptr)
        #color_count = color_count_ptr[0]
        #for i in range(color_count):
        #    color = palette[i]
        #    print(f"Colore {i}: R={color.r}, G={color.g}, B={color.b}, A={color.a}")
        color = palette[0]  # the most used ??
        self.R = color.r; self.G = color.g; self.B = color.b
        unload_image_palette(palette)
        return color.r, color.g, color.b

    def get_complementary_color(color):
        return Color(
            255 - color.r,
            255 - color.g,
            255 - color.b,
            color.a
        )

    def draw(self):
        hist_x = 80
        hist_y = 20
        hist_width = 256 * 3
        hist_height = 200

        draw_text(self.name, hist_x, 0, 20, WHITE)

        # --- find max value for scaling ---
        for i in range(0, 256):
            if self.histogram_r[i] > self.histogram_r_max:
                self.histogram_r_max = self.histogram_r[i]
            if self.histogram_g[i] > self.histogram_g_max:
                self.histogram_g_max = self.histogram_g[i]
            if self.histogram_b[i] > self.histogram_b_max:
                self.histogram_b_max = self.histogram_b[i]

        #draw_rectangle(hist_x, hist_y, hist_width, hist_height, LIGHTGRAY)

        x = 0
        for i in range(0, 256):
            # scale the height of the bar based on max count
            bar_height = (float(self.histogram_r[i]) / self.histogram_r_max) * hist_height
            draw_rectangle(hist_x + x, hist_y + hist_height - int(bar_height), 1, int(bar_height), RED)
            x += 1
            bar_height = (float(self.histogram_g[i]) / self.histogram_g_max) * hist_height
            draw_rectangle(hist_x + x, hist_y + hist_height - int(bar_height), 1, int(bar_height), GREEN)
            x += 1
            bar_height = (float(self.histogram_b[i]) / self.histogram_b_max) * hist_height
            draw_rectangle(hist_x + x, hist_y + hist_height - int(bar_height), 1, int(bar_height), BLUE)
            x += 1

        draw_text("histogram", hist_x, hist_y + hist_height + 5, 20, WHITE)

        return 0
