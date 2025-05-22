import os
import pickle
import random
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

# Paths to your pickle folders and images folder
EDGE_PICKLE_DIR = './pickles_edges_by_style/'
CANNY_PICKLE_DIR = './pickles_by_style/'
IMAGE_ROOT = './wikiart/'

# Steps in the pipeline in order:
PROCESSING_STEPS = [
    'original',
    'grayscale',
    'gradient_magnitude',
    'nonmaxima',
    'hysteresis',
    'canny'  # Add canny as last step
]

def load_all_pickles_from_dir(pickle_dir):
    all_data = {}
    pickle_files = [f for f in os.listdir(pickle_dir) if f.endswith('.pkl')]
    for pf in pickle_files:
        path = os.path.join(pickle_dir, pf)
        with open(path, 'rb') as f:
            data = pickle.load(f)
            all_data.update(data)
    return all_data

class EdgeProcessViewer:
    def __init__(self, edge_pickle_dir, canny_pickle_dir, image_root):
        self.image_root = image_root

        print("Loading edge process pickles...")
        self.edge_data = load_all_pickles_from_dir(edge_pickle_dir)
        print(f"Loaded edge data for {len(self.edge_data)} images.")

        print("Loading canny pickles...")
        self.canny_data = load_all_pickles_from_dir(canny_pickle_dir)
        print(f"Loaded canny data for {len(self.canny_data)} images.")

        # Only keep keys that are common to both datasets to avoid key errors
        self.common_keys = list(set(self.edge_data.keys()) & set(self.canny_data.keys()))
        if not self.common_keys:
            raise RuntimeError("No common keys found between edge and canny pickle datasets.")

        # Setup matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(10, 10))
        plt.subplots_adjust(bottom=0.25)

        self.img_display = None
        self.title_text = self.ax.set_title("")

        # Slider for processing steps
        ax_slider = plt.axes([0.2, 0.1, 0.6, 0.03], facecolor='lightgoldenrodyellow')
        self.slider = Slider(ax_slider, 'Step', 0, len(PROCESSING_STEPS) - 1, valinit=0, valstep=1)
        self.slider.on_changed(self.update_image)

        # Button to load new random image
        ax_button = plt.axes([0.8, 0.02, 0.1, 0.05])
        self.button = Button(ax_button, 'Random Image')
        self.button.on_clicked(self.load_random_image)

        # Initialize with a random image
        self.current_key = None
        self.load_random_image(None)

        plt.axis('off')
        plt.show()

    def load_random_image(self, event):
        self.current_key = random.choice(self.common_keys)
        self.current_edge = self.edge_data[self.current_key]
        self.current_canny = self.canny_data[self.current_key]

        # Load original image
        img_path = self.current_edge['path']
        original = cv2.imread(img_path)
        if original is None:
            print(f"Warning: Could not load original image at {img_path}")
            self.original = np.zeros((512, 512, 3), dtype=np.uint8)
        else:
            self.original = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)

        # Compute grayscale live
        self.gray = cv2.cvtColor(self.original, cv2.COLOR_RGB2GRAY)

        # Helper upscale function for smaller saved arrays
        def upscale(arr):
            return cv2.resize(arr, (self.gray.shape[1], self.gray.shape[0]), interpolation=cv2.INTER_LINEAR)

        # Upscale saved arrays to original size
        self.gradient_magnitude = upscale(self.current_edge['gradient_magnitude'])
        self.nonmaxima = upscale(self.current_edge['nonmaxima'])

        hyst_up = upscale(self.current_edge['hysteresis'])
        self.hysteresis = (hyst_up > 128).astype(np.uint8) * 255

        # Use precomputed canny edges from separate pickle, upscale as well
        self.canny = upscale(self.current_canny['edges'])
        # If canny is boolean or 0/1, scale to 0-255 uint8
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
            img_to_show = self.gray
            img_to_show = cv2.cvtColor(img_to_show, cv2.COLOR_GRAY2RGB)
        elif step == 'gradient_magnitude':
            img_to_show = self.normalize_img_for_display(self.gradient_magnitude)
            img_to_show = cv2.cvtColor(img_to_show, cv2.COLOR_GRAY2RGB)
        elif step == 'nonmaxima':
            img_to_show = self.normalize_img_for_display(self.nonmaxima)
            img_to_show = cv2.cvtColor(img_to_show, cv2.COLOR_GRAY2RGB)
        elif step == 'hysteresis':
            img_to_show = self.hysteresis
            img_to_show = cv2.cvtColor(img_to_show, cv2.COLOR_GRAY2RGB)
        elif step == 'canny':
            img_to_show = self.canny
            img_to_show = cv2.cvtColor(img_to_show, cv2.COLOR_GRAY2RGB)
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
    viewer = EdgeProcessViewer(EDGE_PICKLE_DIR, CANNY_PICKLE_DIR, IMAGE_ROOT)
