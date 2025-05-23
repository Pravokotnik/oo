import os
import json
import random
import cv2
import numpy as np
import gzip
import io
import base64
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

# Paths
INPUT_FOLDER = './wikiart/'
JSON_OUTPUT_DIR = './json_minimal_edges_base64/'  # your base64+gzip json dir

PROCESSING_STEPS = [
    'original',
    'grayscale',
    'gradient_magnitude',
    'nonmaxima',
    'hysteresis',
    'canny_downscaled'
]

def load_all_json(json_dir):
    all_data = {}
    for jf in os.listdir(json_dir):
        if jf.endswith('.json'):
            path = os.path.join(json_dir, jf)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_data.update(data)
    return all_data

def decode_array(encoded_dict):
    """
    Decode base64+gzip compressed numpy array dict back to numpy array.
    """
    b64_data = encoded_dict['data']
    compressed_bytes = base64.b64decode(b64_data)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed_bytes), mode='rb') as f:
        decompressed_bytes = f.read()
    arr = np.frombuffer(decompressed_bytes, dtype=encoded_dict['dtype'])
    arr = arr.reshape(encoded_dict['shape'])
    return arr

def compute_derivatives_opencv(I):
    Ix = cv2.Sobel(I, cv2.CV_64F, 1, 0, ksize=3)
    Iy = cv2.Sobel(I, cv2.CV_64F, 0, 1, ksize=3)
    return Ix, Iy

def gradient_magnitude(I):
    Ix, Iy = compute_derivatives_opencv(I)
    Im = np.hypot(Ix, Iy)
    Iphi = np.arctan2(Iy, Ix)
    return Im, Iphi

def non_maxima_suppression_vectorized(Im, Iphi):
    angle = np.rad2deg(Iphi) % 180
    h, w = Im.shape

    def shift(arr, dx, dy):
        shifted = np.roll(arr, shift=dy, axis=0)
        shifted = np.roll(shifted, shift=dx, axis=1)
        if dy > 0:
            shifted[:dy, :] = 0
        elif dy < 0:
            shifted[dy:, :] = 0
        if dx > 0:
            shifted[:, :dx] = 0
        elif dx < 0:
            shifted[:, dx:] = 0
        return shifted

    mask_0 = ((angle >= 0) & (angle < 22.5)) | ((angle >= 157.5) & (angle <= 180))
    mask_45 = (angle >= 22.5) & (angle < 67.5)
    mask_90 = (angle >= 67.5) & (angle < 112.5)
    mask_135 = (angle >= 112.5) & (angle < 157.5)

    left = shift(Im, -1, 0)
    right = shift(Im, 1, 0)
    cond_0 = (Im >= left) & (Im >= right)

    up_right = shift(Im, 1, -1)
    down_left = shift(Im, -1, 1)
    cond_45 = (Im >= up_right) & (Im >= down_left)

    up = shift(Im, 0, -1)
    down = shift(Im, 0, 1)
    cond_90 = (Im >= up) & (Im >= down)

    up_left = shift(Im, -1, -1)
    down_right = shift(Im, 1, 1)
    cond_135 = (Im >= up_left) & (Im >= down_right)

    nms_mask = (
        (mask_0 & cond_0) |
        (mask_45 & cond_45) |
        (mask_90 & cond_90) |
        (mask_135 & cond_135)
    )

    Z = np.where(nms_mask, Im, 0)
    return Z

def hysteresis_threshold(img, tlow=0.04, thigh=0.16):
    img_8u = np.uint8(np.clip(img / img.max() * 255, 0, 255))
    edges = cv2.Canny(img_8u, int(tlow * 255), int(thigh * 255))
    return edges

class EdgeProcessViewer:
    def __init__(self, json_dir, image_root):
        self.image_root = image_root
        print("Loading downscaled canny JSON data...")
        self.edge_data = load_all_json(json_dir)
        print(f"Loaded data for {len(self.edge_data)} images.")

        self.keys = list(self.edge_data.keys())
        self.fig, self.ax = plt.subplots(figsize=(10,10))
        plt.subplots_adjust(bottom=0.25)

        self.img_display = None
        self.title_text = self.ax.set_title("")

        ax_slider = plt.axes([0.2, 0.1, 0.6, 0.03], facecolor='lightgoldenrodyellow')
        self.slider = Slider(ax_slider, 'Step', 0, len(PROCESSING_STEPS) - 1, valinit=0, valstep=1)
        self.slider.on_changed(self.update_image)

        ax_button = plt.axes([0.8, 0.02, 0.1, 0.05])
        self.button = Button(ax_button, 'Random Image')
        self.button.on_clicked(self.load_random_image)

        self.current_key = None
        self.load_random_image(None)

        plt.axis('off')
        plt.show()

    def load_random_image(self, event):
        self.current_key = random.choice(self.keys)
        self.current_data = self.edge_data[self.current_key]

        img_path = self.current_data['path']
        original = cv2.imread(img_path)
        if original is None:
            print(f"Warning: Could not load original image at {img_path}")
            self.original = np.zeros((512,512,3), dtype=np.uint8)
        else:
            self.original = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)

        self.gray = cv2.cvtColor(self.original, cv2.COLOR_RGB2GRAY)

        # Compute gradient magnitude and angle live
        self.Im, self.Iphi = gradient_magnitude(self.gray)
        self.nonmaxima = non_maxima_suppression_vectorized(self.Im, self.Iphi)
        self.hysteresis = hysteresis_threshold(self.nonmaxima, tlow=0.04, thigh=0.16)

        # Decode and upscale canny edges from base64+gzip
        canny_encoded = self.current_data['edges_downscaled']
        canny_small = decode_array(canny_encoded)
        self.canny = cv2.resize(canny_small, (self.gray.shape[1], self.gray.shape[0]), interpolation=cv2.INTER_NEAREST)

        if self.canny.max() <= 1:
            self.canny = (self.canny * 255).astype(np.uint8)

        self.slider.set_val(0)
        self.update_image(0)

    def update_image(self, val):
        step_idx = int(val)
        step = PROCESSING_STEPS[step_idx]

        if self.img_display:
            self.img_display.remove()

        if step == 'original':
            img_to_show = self.original
        elif step == 'grayscale':
            img_to_show = cv2.cvtColor(self.gray, cv2.COLOR_GRAY2RGB)
        elif step == 'gradient_magnitude':
            norm = self.normalize_img_for_display(self.Im)
            img_to_show = cv2.cvtColor(norm, cv2.COLOR_GRAY2RGB)
        elif step == 'nonmaxima':
            norm = self.normalize_img_for_display(self.nonmaxima)
            img_to_show = cv2.cvtColor(norm, cv2.COLOR_GRAY2RGB)
        elif step == 'hysteresis':
            img_to_show = cv2.cvtColor(self.hysteresis, cv2.COLOR_GRAY2RGB)
        elif step == 'canny_downscaled':
            img_to_show = cv2.cvtColor(self.canny, cv2.COLOR_GRAY2RGB)
        else:
            img_to_show = np.zeros_like(self.original)

        self.img_display = self.ax.imshow(img_to_show)
        self.title_text.set_text(f"{step.capitalize()} - {self.current_key}")
        self.fig.canvas.draw_idle()

    def normalize_img_for_display(self, img):
        img = img.astype(np.float32)
        img -= img.min()
        if img.max() > 0:
            img = img / img.max()
        img = (img * 255).astype(np.uint8)
        return img

if __name__ == "__main__":
    viewer = EdgeProcessViewer(JSON_OUTPUT_DIR, INPUT_FOLDER)
