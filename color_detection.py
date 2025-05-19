import cv2
import os
import numpy as np
import pickle
from pathlib import Path
from tqdm import tqdm
import argparse

# Constants
PICKLE_DIR = "pickles"
FOLDER_PATH = './wikiart/'

os.makedirs(PICKLE_DIR, exist_ok=True)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Art Image Color Analyzer')
    parser.add_argument('--mode', type=str, choices=['mean', 'dominant', 'both'], default='mean',
                       help='Color analysis mode: mean, dominant, or both')
    parser.add_argument('--dominant-colors', type=int, default=3,
                       help='Number of dominant colors to extract (when mode includes dominant)')
    parser.add_argument('--force-recompute', action='store_true',
                       help='Force recompute even if pickle files exist')
    return parser.parse_args()

def find_images_recursive(root_folder):
    """Recursively find all image files in directory"""
    return [os.path.join(dirpath, filename)
            for dirpath, _, filenames in os.walk(root_folder)
            for filename in filenames
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

def calculate_mean_color(image_path):
    """Calculate mean color in BGR and HSV spaces"""
    img = cv2.imread(image_path)
    if img is None:
        return None, None
    
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return np.mean(img.reshape(-1, 3), axis=0), np.mean(hsv.reshape(-1, 3), axis=0)

def calculate_dominant_color(image_path, k=3):
    """Calculate dominant colors using k-means clustering"""
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    pixels = img.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, 0.1)
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    centers = np.uint8(centers)
    counts = np.bincount(labels.flatten())
    return centers[np.argsort(counts)[::-1]]  # Sort by frequency

def process_images(args, image_files):
    """Process images based on selected mode"""
    mean_colors, dominant_colors = {}, {}
    
    for img_path in tqdm(image_files, desc="Analyzing Images", unit="img"):
        try:
            rel_path = os.path.relpath(img_path, FOLDER_PATH)
            
            if args.mode in ['mean', 'both']:
                mean_bgr, mean_hsv = calculate_mean_color(img_path)
                if mean_bgr is not None:
                    mean_colors[rel_path] = {
                        'bgr': mean_bgr,
                        'hsv': mean_hsv,
                        'path': img_path
                    }
            
            if args.mode in ['dominant', 'both'] and img_path in mean_colors:
                dom_colors = calculate_dominant_color(img_path, args.dominant_colors)
                if dom_colors is not None:
                    dominant_colors[rel_path] = {
                        'colors': dom_colors,
                        'path': img_path,
                        'mean_hsv': mean_colors[rel_path]['hsv'] if rel_path in mean_colors else None
                    }
                    
        except Exception as e:
            print(f"\n⚠️ Error in {img_path}: {str(e)[:50]}...")
    
    return mean_colors, dominant_colors

def save_results(args, mean_colors, dominant_colors):
    """Save results to appropriate pickle files"""
    if args.mode in ['mean', 'both']:
        with open(os.path.join(PICKLE_DIR, "mean_colors.pkl"), 'wb') as f:
            pickle.dump(mean_colors, f)
    if args.mode in ['dominant', 'both']:
        with open(os.path.join(PICKLE_DIR, f"dominant_colors_k{args.dominant_colors}.pkl"), 'wb') as f:
            pickle.dump(dominant_colors, f)

def main():
    args = parse_arguments()
    image_files = find_images_recursive(FOLDER_PATH)
    
    mean_colors, dominant_colors = {}, {}
    
    if not args.force_recompute:
        try:
            if args.mode in ['mean', 'both']:
                with open(os.path.join(PICKLE_DIR, "mean_colors.pkl"), 'rb') as f:
                    mean_colors = pickle.load(f)
            if args.mode in ['dominant', 'both']:
                with open(os.path.join(PICKLE_DIR, f"dominant_colors_k{args.dominant_colors}.pkl"), 'rb') as f:
                    dominant_colors = pickle.load(f)
            print("🔍 Loaded existing color data files")
        except FileNotFoundError:
            pass
    
    if (args.mode in ['mean', 'both'] and not mean_colors) or \
       (args.mode in ['dominant', 'both'] and not dominant_colors):
        mean_colors, dominant_colors = process_images(args, image_files)
        save_results(args, mean_colors, dominant_colors)
    
    print("\n📊 Analysis Complete")
    if mean_colors:
        print(f"Mean colors analyzed: {len(mean_colors)} images")
    if dominant_colors:
        print(f"Dominant colors analyzed: {len(dominant_colors)} images (k={args.dominant_colors})")

if __name__ == "__main__":
    main()