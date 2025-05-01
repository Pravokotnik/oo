import cv2
import pickle
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.patches import Circle
from collections import defaultdict
from pathlib import Path
import random
import math

# Config
PICKLE_PATH = "./pickles/emotion_cache_filtered.pkl"
IMAGE_DIR = "./wikiart/"
GRID_SIZE = 20  # 10x10 emotion grid
EMOTION_AXES = {
    'x': ('angry', 'happy'),  # Left-right axis
    'y': ('sad', 'fear')      # Bottom-top axis
}

def rotate_point(x, y, angle_degrees=45):
    theta = math.radians(angle_degrees)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    x_new = cos_t * x - sin_t * y
    y_new = sin_t * x + cos_t * y
    return x_new, y_new

class EmotionExplorer:
    def __init__(self):
        self.results = self.load_results()
        self.grid = self.create_emotion_grid()
        self.current_point = (GRID_SIZE//2, GRID_SIZE//2)  # Start at neutral center
        
        # Set up plot
        self.fig = plt.figure(figsize=(16, 10))
        self.ax_img = plt.subplot2grid((3, 3), (0, 0), colspan=2, rowspan=3)
        self.ax_map = plt.subplot2grid((3, 3), (0, 2))
        self.ax_slider_x = plt.subplot2grid((3, 3), (1, 2))
        self.ax_slider_y = plt.subplot2grid((3, 3), (2, 2))
        
        # Add controls
        self.slider_x = Slider(self.ax_slider_x, 'X (Angry ↔ Happy)', 0, GRID_SIZE-1, 
                              valinit=GRID_SIZE//2, valstep=1)
        self.slider_y = Slider(self.ax_slider_y, 'Y (Sad ↔ Fear)', 0, GRID_SIZE-1, 
                              valinit=GRID_SIZE//2, valstep=1)
        self.slider_x.on_changed(self.update_from_slider)
        self.slider_y.on_changed(self.update_from_slider)
        
        # Click interaction
        self.cursor = Circle((0, 0), 0.3, color='red', alpha=0.8)
        self.ax_map.add_patch(self.cursor)
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        
        self.setup_emotion_map()
        self.display_random_image()
        
    def load_results(self):
        with open(PICKLE_PATH, "rb") as f:
            return pickle.load(f)
        
    
    def emotion_to_coords(self, emotions):
        """Convert emotion percentages to evenly distributed grid coordinates"""
        # Normalize emotion values to [-1, 1] range
        x_val = (emotions[EMOTION_AXES['x'][1]] - emotions[EMOTION_AXES['x'][0]]) / 100.1
        y_val = (emotions[EMOTION_AXES['y'][1]] - emotions[EMOTION_AXES['y'][0]]) / 100.1
        
        # Map to [0, GRID_SIZE-1] with equal bucket sizes
        # x = int((x_val + 1) * (GRID_SIZE) / 2)
        # y = int((y_val + 1) * (GRID_SIZE) / 2)
        x, y = rotate_point(x_val, y_val, 45)  # Rotate the point by 45 degrees
        x = int((x + 1) * (GRID_SIZE) / 2)
        y = int((y + 1) * (GRID_SIZE) / 2)
        
        # Ensure we stay within grid bounds
        return (
            np.clip(x, 0, GRID_SIZE - 1),
            np.clip(y, 0, GRID_SIZE - 1)
        )
    
    def create_emotion_grid(self):
        """Bucket all images into emotion grid"""
        grid = defaultdict(list)
        for img_path, data in self.results.items():
            if data:
                x, y = self.emotion_to_coords(data['emotion'])
                grid[(x, y)].append(img_path)
        return grid
    
    def setup_emotion_map(self):
        """Create heatmap of available emotions"""
        heatmap = np.zeros((GRID_SIZE, GRID_SIZE))
        for (x, y), imgs in self.grid.items():
            heatmap[y, x] = math.log(len(imgs) + 1)  # Log scale for visibility
        
        self.ax_map.imshow(heatmap, cmap='viridis', extent=[0, GRID_SIZE, 0, GRID_SIZE],
                          origin='lower')  # Fix origin to match sliders
        self.ax_map.set_title(f"Click anywhere!\n{EMOTION_AXES['x'][0]} ↔ {EMOTION_AXES['x'][1]}\n{EMOTION_AXES['y'][0]} ↔ {EMOTION_AXES['y'][1]}")
        self.ax_map.grid(alpha=0.3)
    
    def update_selection(self, x, y):
        """Update current selection point"""
        self.current_point = (x, y)
        self.cursor.center = (x + 0.5, y + 0.5)  # Center in grid cell
        self.display_random_image()
        self.fig.canvas.draw_idle()
    
    def update_from_slider(self, val):
        """Handle slider changes"""
        self.update_selection(int(self.slider_x.val), int(self.slider_y.val))
    
    def on_click(self, event):
        """Handle map clicks"""
        if event.inaxes == self.ax_map:
            x = int(event.xdata)
            y = int(event.ydata)
            self.slider_x.set_val(x)
            self.slider_y.set_val(y)
            self.update_selection(x, y)
            # print(f"Clicked at: {event.xdata:.2f}, {event.ydata:.2f}")
    
    def display_random_image(self):
        """Show random image from current emotion bucket"""
        self.ax_img.clear()
        
        x, y = self.current_point
        available_imgs = self.grid.get((x, y), [])
        
        if not available_imgs:
            self.ax_img.text(0.5, 0.5, "No images in this emotion zone", 
                           ha='center', va='center', fontsize=12)
            self.ax_img.set_title(f"Zone {x},{y}: No images")
            return
        
        img_path = random.choice(available_imgs)
        data = self.results[img_path]
        img = cv2.cvtColor(cv2.imread(img_path), cv2.COLOR_BGR2RGB)
        
        # Draw face box
        face = data['face_region']
        cv2.rectangle(img, (face['x'], face['y']), 
                     (face['x']+face['w'], face['y']+face['h']), 
                     (0, 255, 0), 2)
        
        self.ax_img.imshow(img)
        self.ax_img.set_title(
            f"Zone {x},{y}: {len(available_imgs)} images\n"
            f"Dominant: {data['dominant']} ({data['emotion'][data['dominant']]:.1f}%)"
        )
        self.ax_img.axis('off')
        
        # Print emotion stats
        print(f"\n📍 Selected zone: {x},{y}")
        print(f"📊 Images in zone: {len(available_imgs)}")
        print("🎭 Emotion scores:")
        for e, score in sorted(data['emotion'].items(), key=lambda x: -x[1]):
            print(f"  - {e}: {score:.1f}%")

if __name__ == "__main__":
    explorer = EmotionExplorer()
    plt.tight_layout()
    plt.show()