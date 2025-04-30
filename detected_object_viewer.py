import cv2
import os
import random
import pickle
import numpy as np
from pathlib import Path

# Constants
PICKLE_DIR = "pickles"
RATIO_PICKLE_FILE = os.path.join(PICKLE_DIR, "ratio_results.pkl")
DETAILS_PICKLE_FILE = os.path.join(PICKLE_DIR, "details_results.pkl")
FOLDER_PATH = './wikiart/'
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
NUM_BUCKETS = 100

class ImageViewer:
    def __init__(self):
        self.all_ratios, self.image_details = self.load_data()
        self.bucketed_ratios = self.create_ratio_buckets()
        self.current_class = None
        self.current_bucket_idx = 0
        self.current_images = []
        self.current_image_idx = 0
        self.window_name = "Object Viewer"
        self.scale_factor = 1.0
        self.shift_x = 0
        self.shift_y = 0

    def load_data(self):
        """Load the pickled detection data"""
        if not Path(RATIO_PICKLE_FILE).exists() or not Path(DETAILS_PICKLE_FILE).exists():
            raise FileNotFoundError("Could not find detection results. Run the main script first.")
        
        with open(RATIO_PICKLE_FILE, 'rb') as f:
            all_ratios = pickle.load(f)
        with open(DETAILS_PICKLE_FILE, 'rb') as f:
            image_details = pickle.load(f)
        
        return all_ratios, image_details

    def create_ratio_buckets(self):
        """Convert the 100 ratio buckets into a smaller number of buckets"""
        bucketed = {}
        for class_name in self.all_ratios:
            bucketed[class_name] = {}
            
            all_ratios = []
            for ratio in self.all_ratios[class_name]:
                all_ratios.extend([ratio] * len(self.all_ratios[class_name][ratio]))
            
            if not all_ratios:
                continue
                
            min_ratio = min(all_ratios)
            max_ratio = max(all_ratios)
            min_ratio = 0
            max_ratio = 100
            bucket_size = (max_ratio - min_ratio) / NUM_BUCKETS
            
            for i in range(NUM_BUCKETS):
                lower = min_ratio + i * bucket_size
                upper = min_ratio + (i + 1) * bucket_size
                bucketed[class_name][i] = {
                    'range': (lower, upper),
                    'images': []
                }
            
            for ratio in self.all_ratios[class_name]:
                for img_path in self.all_ratios[class_name][ratio]:
                    bucket_idx = min(int((ratio - min_ratio) / bucket_size), NUM_BUCKETS - 1)
                    bucketed[class_name][bucket_idx]['images'].append(img_path)
        
        return bucketed

    def prepare_image(self, img_path, target_class):
        """Scale image to fit window and center target object"""
        img = cv2.imread(os.path.join(FOLDER_PATH, img_path))
        if img is None:
            return None
            
        h, w = img.shape[:2]
        img_details = self.image_details[img_path]
        
        # Find target detection
        target_detection = None
        for detection in img_details['detections']:
            if detection['class_name'] == target_class:
                target_detection = detection
                break
        
        if not target_detection:
            return None
        
        # Calculate scale factor to fit image in window
        self.scale_factor = min(WINDOW_WIDTH/w, WINDOW_HEIGHT/h)
        scaled_w = int(w * self.scale_factor)
        scaled_h = int(h * self.scale_factor)
        scaled_img = cv2.resize(img, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
        
        # Calculate object center in scaled coordinates
        x1, y1, x2, y2 = target_detection['box_coords']
        obj_center_x = int((x1 + x2) * 0.5 * self.scale_factor)
        obj_center_y = int((y1 + y2) * 0.5 * self.scale_factor)
        
        # Calculate required shift to center object
        self.shift_x = WINDOW_WIDTH//2 - obj_center_x
        self.shift_y = WINDOW_HEIGHT//2 - obj_center_y
        
        # Create black canvas
        canvas = np.zeros((WINDOW_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8)
        
        # Calculate paste coordinates
        x_start = max(0, self.shift_x)
        y_start = max(0, self.shift_y)
        x_end = min(WINDOW_WIDTH, scaled_w + self.shift_x)
        y_end = min(WINDOW_HEIGHT, scaled_h + self.shift_y)
        
        # Calculate source coordinates
        src_x_start = max(0, -self.shift_x)
        src_y_start = max(0, -self.shift_y)
        src_x_end = min(scaled_w, WINDOW_WIDTH - self.shift_x)
        src_y_end = min(scaled_h, WINDOW_HEIGHT - self.shift_y)
        
        # Paste the image
        canvas[y_start:y_end, x_start:x_end] = scaled_img[src_y_start:src_y_end, src_x_start:src_x_end]
        
        # Draw all detections
        for detection in img_details['detections']:
            x1, y1, x2, y2 = detection['box_coords']
            class_name = detection['class_name']
            conf = detection['confidence']
            
            # Transform coordinates
            x1 = int(x1 * self.scale_factor) + self.shift_x
            y1 = int(y1 * self.scale_factor) + self.shift_y
            x2 = int(x2 * self.scale_factor) + self.shift_x
            y2 = int(y2 * self.scale_factor) + self.shift_y
            
            # Only draw if visible in window
            if (x1 < WINDOW_WIDTH and x2 > 0 and y1 < WINDOW_HEIGHT and y2 > 0):
                color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
                cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
                label = f"{class_name} {conf:.2f}"
                cv2.putText(canvas, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return canvas

    def show_image(self):
        """Display the current image"""
        if not self.current_images:
            return
            
        img_path = self.current_images[self.current_image_idx]
        prepared_img = self.prepare_image(img_path, self.current_class)
        
        if prepared_img is not None:
            cv2.imshow(self.window_name, prepared_img)
            
            # Print bucket info
            bucket_range = self.bucketed_ratios[self.current_class][self.current_bucket_idx]['range']
            print(f"\nBucket {self.current_bucket_idx+1}/{NUM_BUCKETS} ({bucket_range[0]:.1f}%-{bucket_range[1]:.1f}%)")
            print(f"Image {self.current_image_idx+1}/{len(self.current_images)}")

    def run(self):
        """Main interaction loop"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Get available classes
        available_classes = sorted(self.bucketed_ratios.keys())
        if not available_classes:
            print("No detections found in the data")
            return
        
        print("\nAvailable detected classes:")
        for i, class_name in enumerate(available_classes, 1):
            total = sum(len(self.bucketed_ratios[class_name][b]['images']) for b in self.bucketed_ratios[class_name])
            print(f"{i}. {class_name} ({total} detections)")
        
        while True:
            try:
                # Get user input for class selection
                user_input = input("\nEnter class name or number (q to quit): ").strip().lower()
                if user_input == 'q':
                    break
                    
                # Try to interpret as number
                try:
                    class_num = int(user_input)
                    if 1 <= class_num <= len(available_classes):
                        self.current_class = available_classes[class_num-1]
                    else:
                        print("Invalid number")
                        continue
                except ValueError:
                    if user_input in available_classes:
                        self.current_class = user_input
                    else:
                        print(f"Class '{user_input}' not found in detections")
                        continue
                
                # Start with middle bucket
                self.current_bucket_idx = NUM_BUCKETS // 2
                self.current_images = self.bucketed_ratios[self.current_class][self.current_bucket_idx]['images']
                random.shuffle(self.current_images)
                self.current_image_idx = 0
                
                if not self.current_images:
                    print(f"No images found in middle bucket for {self.current_class}")
                    continue
                
                self.show_image()
                
                # Image navigation loop
                while True:
                    key = cv2.waitKey(0) & 0xFF
                    
                    # ESC or Q to exit
                    if key == 27 or key == ord('q'):
                        cv2.destroyAllWindows()
                        return
                        
                    # Right arrow or D for next image
                    elif key == 3 or key == ord('d'):
                        self.current_image_idx = (self.current_image_idx + 1) % len(self.current_images)
                        self.show_image()
                        
                    # Left arrow or A for previous image
                    elif key == 2 or key == ord('a'):
                        self.current_image_idx = (self.current_image_idx - 1) % len(self.current_images)
                        self.show_image()
                        
                    # Up arrow or W for next bucket (larger ratios)
                    elif key == 0 or key == ord('w'):
                        if self.current_bucket_idx < NUM_BUCKETS - 1:
                            self.current_bucket_idx += 1
                            self.current_images = self.bucketed_ratios[self.current_class][self.current_bucket_idx]['images']
                            random.shuffle(self.current_images)
                            self.current_image_idx = 0
                            self.show_image()
                            
                    # Down arrow or S for previous bucket (smaller ratios)
                    elif key == 1 or key == ord('s'):
                        if self.current_bucket_idx > 0:
                            self.current_bucket_idx -= 1
                            self.current_images = self.bucketed_ratios[self.current_class][self.current_bucket_idx]['images']
                            random.shuffle(self.current_images)
                            self.current_image_idx = 0
                            self.show_image()
                            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    viewer = ImageViewer()
    viewer.run()