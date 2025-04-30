import cv2
import os
import matplotlib.pyplot as plt
from tqdm import tqdm
import torch
from ultralytics import YOLO
import warnings
import pickle
from pathlib import Path

# 🔇 SILENCE EVERYTHING
warnings.filterwarnings("ignore")
os.environ["YOLO_VERBOSE"] = "False"

# Constants
PICKLE_DIR = "pickles"
RATIO_PICKLE_FILE = os.path.join(PICKLE_DIR, "ratio_results.pkl")
DETAILS_PICKLE_FILE = os.path.join(PICKLE_DIR, "details_results.pkl")
FOLDER_PATH = './wikiart/'

# Ensure pickle directory exists
os.makedirs(PICKLE_DIR, exist_ok=True)

def find_images_recursive(root_folder):
    """Recursively find all image files in directory"""
    image_files = []
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                image_files.append(os.path.join(dirpath, filename))
    return image_files

def process_images(model, image_files, folder_path):
    """Process all images and return detection results"""
    all_ratios = {}
    image_details = {}
    
    for img_path in tqdm(image_files, desc="Scanning Images", unit="img"):
        try:
            img = cv2.imread(img_path)
            if img is None: 
                continue

            results = model.predict(
                img,
                imgsz=640,
                conf=0.4,
                iou=0.45,
                device='0' if torch.cuda.is_available() else 'cpu',
                verbose=False
            )

            h, w = img.shape[:2]
            img_area = h * w
            rel_path = os.path.relpath(img_path, folder_path)
            
            # Initialize entry for this image
            image_details[rel_path] = {
                'detections': [],
                'img_shape': img.shape,
                'img_area': img_area,
                'img_path': img_path
            }
            
            for box in results[0].boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                conf = float(box.conf[0])
                
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                box_area = (x2 - x1) * (y2 - y1)
                ratio = min(100, int((box_area / img_area) * 100))
                
                # Update ratio statistics
                if class_name not in all_ratios:
                    all_ratios[class_name] = {}
                if ratio not in all_ratios[class_name]:
                    all_ratios[class_name][ratio] = []
                all_ratios[class_name][ratio].append(rel_path)
                
                # Store detailed detection info
                detection = {
                    'class_id': class_id,
                    'class_name': class_name,
                    'confidence': conf,
                    'box_coords': (x1, y1, x2, y2),
                    'box_area': box_area,
                    'ratio': ratio,
                    'normalized_ratio': box_area / img_area
                }
                image_details[rel_path]['detections'].append(detection)

        except Exception as e:
            print(f"\n⚠️ Error in {img_path}: {str(e)[:50]}...")
    
    return all_ratios, image_details

def save_results(data, filename):
    """Save results to pickle file"""
    with open(filename, 'wb') as f:
        pickle.dump(data, f)
    print(f"✅ Saved results to {filename}")

def load_results(filename):
    """Load results from pickle file"""
    with open(filename, 'rb') as f:
        return pickle.load(f)

def print_summary(all_ratios):
    """Print detection summary"""
    print("\n📊 Detection Summary:")
    for class_name in sorted(all_ratios.keys()):
        total = sum(len(files) for files in all_ratios[class_name].values())
        print(f"{class_name}: {total} detections")
        for ratio in sorted(all_ratios[class_name].keys()):
            print(f"  - {ratio}%: {len(all_ratios[class_name][ratio])} instances")

def visualize_results(all_ratios, image_details):
    """Create visualization plots"""
    # Plot 1: Size distribution by class
    plt.figure(figsize=(12, 6))
    for class_name in all_ratios:
        ratios = []
        for ratio in all_ratios[class_name]:
            ratios.extend([ratio] * len(all_ratios[class_name][ratio]))
        plt.hist(ratios, bins=20, alpha=0.5, label=class_name)
    plt.title("Object Size Distribution by Class")
    plt.xlabel("Size Ratio (% of image area)")
    plt.ylabel("Frequency")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()
    
    # Plot 2: Detection count per image
    detections_per_image = [len(details['detections']) for details in image_details.values()]
    plt.figure(figsize=(12, 6))
    plt.hist(detections_per_image, bins=30, edgecolor='black')
    plt.title("Number of Detections per Image")
    plt.xlabel("Detections per image")
    plt.ylabel("Frequency")
    plt.grid(True, alpha=0.3)
    plt.show()

def main():
    # Check for existing results
    if Path(RATIO_PICKLE_FILE).exists() and Path(DETAILS_PICKLE_FILE).exists():
        print(f"🔍 Found existing results files")
        all_ratios = load_results(RATIO_PICKLE_FILE)
        image_details = load_results(DETAILS_PICKLE_FILE)
    else:
        # Load model
        model = None
        for model_name in ['yolov9c.pt', 'yolov8x.pt']:
            try:
                model = YOLO(model_name)
                print(f"🔥 Loaded {model_name} successfully!")
                break
            except:
                continue
        if model is None:
            raise FileNotFoundError("No YOLO models found!")

        # Process images
        image_files = find_images_recursive(FOLDER_PATH)
        all_ratios, image_details = process_images(model, image_files, FOLDER_PATH)
        
        # Save both result types
        save_results(all_ratios, RATIO_PICKLE_FILE)
        save_results(image_details, DETAILS_PICKLE_FILE)
    
    # Output results
    print_summary(all_ratios)
    visualize_results(all_ratios, image_details)
    
    # Example of accessing detailed info
    print("\nExample image details:")
    first_image = next(iter(image_details.values()))
    print(f"Image path: {first_image['img_path']}")
    print(f"Dimensions: {first_image['img_shape']}")
    print(f"Detections: {len(first_image['detections'])}")
    if first_image['detections']:
        print("First detection:")
        print(f"  Class: {first_image['detections'][0]['class_name']}")
        print(f"  Confidence: {first_image['detections'][0]['confidence']:.2f}")
        print(f"  Bounding box: {first_image['detections'][0]['box_coords']}")

if __name__ == "__main__":
    main()