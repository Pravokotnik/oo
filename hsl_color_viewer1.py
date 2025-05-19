import os
import pickle
import random
from pathlib import Path
from tkinter import Tk, Scale, Frame, Canvas, Label, HORIZONTAL, NW
from PIL import Image, ImageTk, ImageOps
import colorsys
from collections import defaultdict
from threading import Thread
from queue import Queue

class HSLColorPicker:
    def __init__(self, root, pickle_path="pickles/mean_colors.pkl", grid_size=16, bucket_granularity=16):
        self.root = root
        self.root.title("Art Color Picker")
        
        # Configuration
        self.grid_size = grid_size
        self.bucket_granularity = bucket_granularity
        self.current_hue = 0
        self.active_requests = set()
        self.load_queue = Queue()
        self.worker_thread = Thread(target=self._image_worker, daemon=True)
        self.worker_thread.start()
        
        # Load color data
        self.color_data = self.load_color_data(pickle_path)
        if not self.color_data:
            raise ValueError("No color data found - run the mean color pickler first")
        
        # Build buckets
        print("Building color buckets...")
        self.color_buckets = self.build_color_buckets()
        
        # UI Setup
        self.setup_ui()
        self.update_display()
    
    def _image_worker(self):
        """Background thread for loading images"""
        while True:
            task = self.load_queue.get()
            if task == "STOP":
                break
                
            cell_id, path, size = task
            try:
                img = Image.open(path)
                img = ImageOps.fit(img, (size, size), method=Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.root.after(0, self._update_cell, cell_id, photo)
            except Exception as e:
                print(f"Error loading {path}: {str(e)[:50]}")
            finally:
                self.load_queue.task_done()
                self.active_requests.discard(path)
    
    def _update_cell(self, cell_id, photo):
        """Update a cell with loaded image (main thread)"""
        if cell_id in self.canvas_images:
            self.canvas.itemconfig(cell_id, image=photo)
            self.canvas_images[cell_id] = photo  # Keep reference
    
    def load_color_data(self, pickle_path):
        if not Path(pickle_path).exists():
            return None
        with open(pickle_path, "rb") as f:
            return pickle.load(f)
    
    def build_color_buckets(self):
        buckets = defaultdict(list)
        for rel_path, data in self.color_data.items():
            bgr = data['bgr']
            bucket_key = (
                min(int(bgr[2] * self.bucket_granularity / 256), self.bucket_granularity-1),
                min(int(bgr[1] * self.bucket_granularity / 256), self.bucket_granularity-1),
                min(int(bgr[0] * self.bucket_granularity / 256), self.bucket_granularity-1)
            )
            buckets[bucket_key].append(data['path'])
        return buckets
    
    def hsl_to_rgb_bucket(self, h, s, l):
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return (
            min(int(r * self.bucket_granularity), self.bucket_granularity-1),
            min(int(g * self.bucket_granularity), self.bucket_granularity-1),
            min(int(b * self.bucket_granularity), self.bucket_granularity-1)
        )
    
    def find_closest_image(self, target_h, target_s, target_l):
        target_bucket = self.hsl_to_rgb_bucket(target_h, target_s, target_l)
        candidates = self.color_buckets.get(target_bucket, [])
        return random.choice(candidates) if candidates else None
    
    def setup_ui(self):
        self.main_frame = Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)
        
        self.canvas = Canvas(self.main_frame, width=800, height=800, bg='white')
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas_images = {}  # Stores PhotoImage references
        
        self.hue_frame = Frame(self.main_frame)
        self.hue_frame.pack(fill="x", padx=10, pady=5)
        Label(self.hue_frame, text="Hue:").pack(side="left")
        self.hue_slider = Scale(self.hue_frame, from_=0, to=360, orient=HORIZONTAL,
                              command=lambda _: self.on_hue_change())
        self.hue_slider.pack(fill="x", expand=True)
        
        self.info_label = Label(self.main_frame, text="")
        self.info_label.pack(fill="x", padx=10, pady=5)
    
    def on_hue_change(self):
        self.current_hue = self.hue_slider.get() / 360.0
        self.update_display()
    
    def update_display(self):
        """Refresh the entire display with new hue"""
        # Clear previous state
        self.canvas.delete("all")
        self.canvas_images = {}
        self.active_requests.clear()
        
        # Drain the queue of any pending requests
        while not self.load_queue.empty():
            self.load_queue.get()
            self.load_queue.task_done()
        
        cell_size = 800 // self.grid_size
        
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                # Photoshop-style HSL distribution:
                # X-axis (columns) = saturation (0 to 1)
                # Y-axis (rows) = lightness (1 to 0)
                saturation = col / (self.grid_size - 1)
                lightness = 1.0 - (row / (self.grid_size - 1))
                
                # Calculate target color
                img_path = self.find_closest_image(self.current_hue, saturation, lightness)
                x1, y1 = col * cell_size, row * cell_size
                
                if img_path:
                    cell_id = self.canvas.create_image(x1, y1, anchor=NW)
                    self.canvas_images[cell_id] = None  # Reserve spot
                    self.active_requests.add(img_path)
                    self.load_queue.put((cell_id, img_path, cell_size))
                else:
                    # Show empty cell with border
                    self.canvas.create_rectangle(x1, y1, x1+cell_size, y1+cell_size,
                                               fill='white', outline='lightgray')
        
        self.info_label.config(text=f"Hue: {int(self.current_hue*360)}° | Grid: {self.grid_size}x{self.grid_size}")

    def __del__(self):
        self.load_queue.put("STOP")
        self.worker_thread.join()

if __name__ == "__main__":
    root = Tk()
    app = HSLColorPicker(root, grid_size=16, bucket_granularity=16)
    root.mainloop()