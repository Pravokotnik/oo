import cv2
import numpy as np
import pickle
import random
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from pathlib import Path

def load_data(mode='mean', dominant_k=3):
    """Load precomputed data from your original analysis"""
    pickle_file = {
        'mean': "mean_colors.pkl",
        'dominant': f"dominant_colors_k{dominant_k}.pkl"
    }[mode]
    
    with open(Path("pickles") / pickle_file, 'rb') as f:
        data = pickle.load(f)
    
    # Convert to list of (hue, saturation, value, path)
    color_data = []
    for path, item in data.items():
        if mode == 'mean':
            h, s, v = item['hsv']
            color_data.append((h, s/255.0, v/255.0, item['path']))
        else:
            for color in item['colors']:
                hsv = cv2.cvtColor(np.array([[color]], dtype=np.uint8), cv2.COLOR_BGR2HSV)[0][0]
                h, s, v = hsv
                color_data.append((h, s/255.0, v/255.0, item['path']))
    
    return color_data

def create_instant_viewer(color_data, grid_size=10):
    """Create interactive viewer with zero-lag performance"""
    # Initialize display
    fig, axes = plt.subplots(grid_size, grid_size, figsize=(12, 12))
    plt.subplots_adjust(left=0, right=1, bottom=0.1, top=0.9, wspace=0, hspace=0)
    
    # Pre-render empty black cells
    empty_cell = np.zeros((1, 1, 3), dtype=np.float32)
    for ax_row in axes:
        for ax in ax_row:
            ax.imshow(empty_cell)
            ax.axis('off')
    
    def update_grid(hue_value):
        """Instant grid update using precomputed data"""
        # Find closest matches for each grid cell
        grid_matches = {}
        for h, s, v, path in color_data:
            # Calculate grid position
            i = min(int(v * grid_size), grid_size-1)  # Value -> vertical
            j = min(int(s * grid_size), grid_size-1)  # Saturation -> horizontal
            
            # Score based on hue difference
            hue_diff = min(abs(h - hue_value), 180 - abs(h - hue_value))
            current_score = grid_matches.get((i, j), (float('inf'), None))[0]
            
            if hue_diff < current_score:
                grid_matches[(i, j)] = (hue_diff, path)
        
        # Update display
        for (i, j), (_, path) in grid_matches.items():
            img = cv2.imread(path)
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                axes[i][j].imshow(img, aspect='auto')
        
        plt.suptitle(f"Hue: {int(hue_value)}°", y=0.95)
        plt.draw()
    
    # Add slider
    ax_slider = plt.axes([0.2, 0.02, 0.6, 0.03])
    hue_slider = Slider(ax_slider, 'Hue', 0, 179, valinit=120)
    hue_slider.on_changed(update_grid)
    
    plt.show()

if __name__ == "__main__":
    # Load precomputed mean colors (change to 'dominant' if needed)
    color_data = load_data(mode='mean')
    
    # Create interactive viewer (10x10 grid)
    create_instant_viewer(color_data, grid_size=10)