from array import array
import random, math
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
        self.matte_enabled = Config.get('items.types.image.matte.enabled', True)
        self.k_means = Config.get('items.types.image.matte.kmeans', False)
        self.k_num = Config.get('items.types.image.matte.knum', 2)
        self.k_iter = Config.get('items.types.image.matte.kiter', 5)
        self.k_rnd = Config.get('items.types.image.matte.krnd', True)
        self.k_col = [Color(0,0,0,255), Color(255,255,255,255), Color(128,128,128,255)]
        self.process(image)

    def process(self, image):
        image2: Image = image_copy(image)
        image_resize(image2, image.width // self.scale, image.height // self.scale)
        #export_image(image2, "histogram_image.jpg")

        if Config.get('items.types.image.histogram.enabled', False):
            self.create_histogram(image2)

        if self.matte_enabled:
            if self.k_means:
                self.k_col = self.get_k_means(image2, k=self.k_num, iterations=self.k_iter)
            else:
                self.k_col = self.get_df_means(image2)

        image2 = unload_image(image2)

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

        pixels = unload_image_colors(pixels)

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

    def get_df_means(self, image):

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

        ls = sorted(count.items(), reverse=True, key=lambda x: x[1])
        return [self.split_rbg(ls[i][0]) for i in range(self.k_num)]

    def get_k_means(self, img, k=3, iterations=9):
        # 1. Load the image
        image_format(img, PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8A8)

        # Get the colors (pixels) as an array of Color structures
        pixels = load_image_colors(img)
        pixel_count = img.width * img.height

        # Initialization: Choose K random centroids from existing pixels
        centroids = []
        for _ in range(k):
            p = pixels[random.randint(0, pixel_count - 1)]
            centroids.append([float(p.r), float(p.g), float(p.b)])

        for _ in range(iterations):
            # Lists to accumulate the colors assigned to each centroid
            clusters = [[] for _ in range(k)]

            # Assignment: Each pixel goes to the closest centroid
            # (To optimize, we sample 1 in 10 pixels for large images.)
            for i in range(0, pixel_count, 1):
                p = pixels[i]
                best_dist = float('inf')
                best_idx = 0

                for idx, c in enumerate(centroids):
                    # RGB Euclidean distance
                    dist = math.sqrt((p.r - c[0])**2 + (p.g - c[1])**2 + (p.b - c[2])**2)
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = idx

                clusters[best_idx].append([p.r, p.g, p.b])

            # Update: Recalculate the centroids as the average of the colors in the cluster
            for i in range(k):
                if not clusters[i]: continue

                avg_r = sum(p[0] for p in clusters[i]) / len(clusters[i])
                avg_g = sum(p[1] for p in clusters[i]) / len(clusters[i])
                avg_b = sum(p[2] for p in clusters[i]) / len(clusters[i])
                centroids[i] = [avg_r, avg_g, avg_b]

        # Memory cleaning
        pixels = unload_image_colors(pixels)

        # Return dominant colors as Raylib Color objects
        return [Color(int(c[0]), int(c[1]), int(c[2]), 255) for c in centroids]

    def split_rbg(self, rgb):
        if Config.get('items.types.image.matte.complement', False):
            return Color(255 - (rgb >> 16), 255 - (rgb >> 8 & 0xff), 255 - (rgb & 0xff), 255)
        else:
            return Color(rgb >> 16, rgb >> 8 & 0xff, rgb & 0xff, 255)

    def get_mat_color(self):
        i = random.randint(0, self.k_num-1) if self.k_rnd else 0
        return (self.k_col[i].r, self.k_col[i].g, self.k_col[i].b, self.k_col[i].a)

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

    def get_complementary_color(color):
        return Color(
            255 - color.r,
            255 - color.g,
            255 - color.b,
            color.a
        )

    def draw_(self):
        for i in range(self.k_num):
            draw_rectangle(10+(i*50), 10, 40, 40, (self.k_col[i].r, self.k_col[i].g, self.k_col[i].b, self.k_col[i].a))

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
