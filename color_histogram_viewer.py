import cv2
import numpy as np
import pickle
import random
from pathlib import Path
import matplotlib.pyplot as plt
import os

# Load histogram data
HISTOGRAM_FILE = os.path.join("pickles", "color_histograms.pkl")
with open(HISTOGRAM_FILE, 'rb') as f:
    histograms = pickle.load(f)

# Convert to list for easier access
hist_data = []
for path, data in histograms.items():
    hist_data.append({
        'path': data['path'],
        'hist': data['histogram']
    })

def compare_histograms(hist1, hist2):
    """Compare two histograms using correlation"""
    score = 0
    for channel in ['hue', 'saturation', 'value']:
        score += cv2.compareHist(hist1[channel], hist2[channel], cv2.HISTCMP_CORREL)
    return score / 3  # Average score across channels

def find_closest_histogram(target_hist):
    """Find image with histogram most similar to target"""
    best_score = -1
    best_match = None
    
    for data in hist_data:
        score = compare_histograms(target_hist, data['hist'])
        if score > best_score:
            best_score = score
            best_match = data
    
    return best_match

class InteractiveHistogram:
    def __init__(self):
        self.fig, (self.ax_img, self.ax_hist) = plt.subplots(1, 2, figsize=(16, 6))
        self.current_data = random.choice(hist_data)
        self.current_hist = self.current_data['hist'].copy()
        self.bins = self.current_hist['bins']
        self.bars = None
        
        # Initial display
        self.show_image(self.current_data['path'])
        self.plot_histogram()
        
        # Add randomize button
        ax_random = plt.axes([0.8, 0.01, 0.1, 0.05])
        random_button = plt.Button(ax_random, 'Random Image')
        random_button.on_clicked(self.randomize)
        
        # Connect the click event
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        
        plt.show()
    
    def show_image(self, path):
        """Display current image"""
        img = cv2.imread(path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.ax_img.clear()
        self.ax_img.imshow(img)
        self.ax_img.set_title("Closest Matching Image")
        self.ax_img.axis('off')
    
    def plot_histogram(self):
        """Plot the current histogram"""
        self.ax_hist.clear()
        x = np.arange(self.bins)
        width = 0.25
        
        # Store the bar containers for later interaction
        self.bars = {}
        self.bars['hue'] = self.ax_hist.bar(x - width, self.current_hist['hue'], width, color='red', label='Hue')
        self.bars['saturation'] = self.ax_hist.bar(x, self.current_hist['saturation'], width, color='green', label='Saturation')
        self.bars['value'] = self.ax_hist.bar(x + width, self.current_hist['value'], width, color='blue', label='Value')
        
        self.ax_hist.set_title("Click Bars to Modify Histogram")
        self.ax_hist.set_xlabel("Bin")
        self.ax_hist.set_ylabel("Normalized Frequency")
        self.ax_hist.legend()
        self.ax_hist.grid(True, alpha=0.3)
    
    def randomize(self, event):
        """Load a random image and its histogram"""
        self.current_data = random.choice(hist_data)
        self.current_hist = self.current_data['hist'].copy()
        self.show_image(self.current_data['path'])
        self.plot_histogram()
        self.fig.canvas.draw_idle()
    
    def on_click(self, event):
        """Handle clicks on histogram bars"""
        if event.inaxes != self.ax_hist:
            return
        
        # Determine which bar was clicked
        for channel in ['hue', 'saturation', 'value']:
            for i, bar in enumerate(self.bars[channel]):
                if bar.contains(event)[0]:
                    # Get y position of click relative to bar
                    new_value = event.ydata
                    if new_value < 0:
                        new_value = 0
                    elif new_value > 1:
                        new_value = 1
                    
                    # Update the current histogram
                    self.current_hist[channel][i] = new_value
                    
                    # Normalize the modified channel
                    self.current_hist[channel] = cv2.normalize(
                        self.current_hist[channel], 
                        None
                    ).flatten()
                    
                    # Find closest match
                    closest = find_closest_histogram(self.current_hist)
                    
                    # Update display
                    self.show_image(closest['path'])
                    
                    # Update current data and redraw
                    self.current_data = closest
                    self.current_hist = closest['hist'].copy()
                    self.plot_histogram()
                    self.fig.canvas.draw_idle()
                    return

# Create and show the interactive histogram
InteractiveHistogram()