import pickle
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import os
import glob

DATASET_FOLDER = './pickles_by_style/'

class FullDatasetHoughViewer:
    def __init__(self, dataset_folder):
        self.data = {}
        self.keys = []
        self.styles = []

        pkl_files = glob.glob(os.path.join(dataset_folder, '*.pkl'))
        print(f"Loading {len(pkl_files)} pickle files from {dataset_folder} ...")

        for pkl_file in pkl_files:
            style_name = os.path.splitext(os.path.basename(pkl_file))[0].replace('hough_data_', '')
            print(f"Loading style '{style_name}' ...")
            with open(pkl_file, 'rb') as f:
                style_data = pickle.load(f)

            # Debug print first few keys and sample data type
            print(f"Keys in pickle '{style_name}': {list(style_data.keys())[:5]}")
            sample = next(iter(style_data.values()))
            print(f"Sample value type: {type(sample)}")

            for k, v in style_data.items():
                if not isinstance(v, dict):
                    print(f"Warning: skipping key {k} because its data is not a dict (type={type(v)})")
                    continue
                v = self.upgrade_data_resolution(v)
                global_key = f"{style_name}::{k}"
                self.keys.append(global_key)
                self.data[global_key] = v
                self.styles.append(style_name)

        print(f"Loaded total {len(self.keys)} images across styles.")

        self.fig, axs = plt.subplots(2, 2, figsize=(12, 10))
        self.ax_img, self.ax_edges, self.ax_acc, self.ax_sin = axs.flatten()
        self.fig.subplots_adjust(left=0.25, bottom=0.25)

        axcolor = 'lightgoldenrodyellow'
        self.ax_slider = plt.axes([0.25, 0.1, 0.5, 0.03], facecolor=axcolor)
        self.slider = Slider(self.ax_slider, 'Image Index', 0, len(self.keys)-1, valinit=0, valstep=1)
        self.slider.on_changed(self.update)

        ax_button = plt.axes([0.8, 0.025, 0.1, 0.04])
        self.btn_random = Button(ax_button, 'Random')
        self.btn_random.on_clicked(self.random_image)

        self.update(0)
        plt.show()

    def upgrade_data_resolution(self, data):
        """If accumulator or sinusoids_vis are smaller resolution, 
        resize them to 360x360 for smoother visualization and blur sinusoid"""
        import cv2

        TARGET_SIZE = (360, 360)
        # Resize accumulator
        acc = data['accumulator']
        if acc.shape != TARGET_SIZE:
            acc_resized = cv2.resize(acc, TARGET_SIZE, interpolation=cv2.INTER_LINEAR)
            data['accumulator'] = acc_resized.astype(np.float32)
        # Resize sinusoid visualization and smooth
        sin_vis = data['sinusoids_vis']
        if sin_vis.shape != TARGET_SIZE:
            sin_resized = cv2.resize(sin_vis, TARGET_SIZE, interpolation=cv2.INTER_LINEAR)
            sin_blurred = cv2.GaussianBlur(sin_resized, (7,7), sigmaX=2)
            data['sinusoids_vis'] = sin_blurred.astype(np.uint8)
        else:
            # Still smooth if already correct size
            sin_blurred = cv2.GaussianBlur(sin_vis, (7,7), sigmaX=2)
            data['sinusoids_vis'] = sin_blurred.astype(np.uint8)

        return data

    def update(self, val):
        idx = int(val)
        key = self.keys[idx]
        data = self.data[key]
        style_name = self.styles[idx]

        img = cv2.imread(data['path'])
        if img is None:
            print(f"Failed to load image: {data['path']}")
            return
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        self.ax_img.clear()
        self.ax_img.imshow(img_rgb)
        self.ax_img.set_title(f"[{style_name}] Original Image\n{key.split('::')[1]}")
        self.ax_img.axis('off')

        self.ax_edges.clear()
        self.ax_edges.imshow(data['edges'], cmap='gray')
        self.ax_edges.set_title('Edges (Canny)')
        self.ax_edges.axis('off')

        self.ax_acc.clear()
        self.ax_acc.imshow(data['accumulator'], cmap='hot', aspect='auto')
        self.ax_acc.set_title('Hough Accumulator (Heatmap)')
        self.ax_acc.axis('on')

        self.ax_sin.clear()
        self.ax_sin.imshow(
            data['sinusoids_vis'],
            cmap='inferno',
            origin='lower',  # proper wave orientation
            aspect='auto'
        )
        self.ax_sin.set_title('Smoothed Hough Sinusoidal Curves Visualization')
        self.ax_sin.axis('on')

        self.fig.canvas.draw_idle()

    def random_image(self, event):
        import random
        idx = random.randint(0, len(self.keys)-1)
        self.slider.set_val(idx)

if __name__ == "__main__":
    viewer = FullDatasetHoughViewer(DATASET_FOLDER)
