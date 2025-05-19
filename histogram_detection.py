import cv2
import os
import numpy as np
from tqdm import tqdm
import pickle
from pathlib import Path

def compute_bgr_histogram(image_path, folder_path, n_bins=8):
    """Optimized version using cv2.calcHist"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        # Calculate 3D histogram using OpenCV's optimized function
        hist = cv2.calcHist(
            images=[img],
            channels=[0, 1, 2],  # BGR channels
            mask=None,
            histSize=[n_bins] * 3,
            ranges=[0, 256] * 3
        )
        
        # Normalize histogram to sum to 1
        hist = hist / np.sum(hist)
        
        return {
            'relative_path': os.path.relpath(image_path, folder_path),
            'histogram': hist.flatten(),
            'img_shape': img.shape,
            'img_path': image_path,
            'bins': n_bins
        }
    except Exception as e:
        print(f"\n⚠️ Error processing {image_path}: {str(e)}")
        return None

def main():
    # Constants
    PICKLE_DIR = "pickles"
    HISTOGRAM_PICKLE_FILE = os.path.join(PICKLE_DIR, "color_histograms.pkl")
    FOLDER_PATH = './wikiart/'
    BINS = 8
    
    os.makedirs(PICKLE_DIR, exist_ok=True)

    if Path(HISTOGRAM_PICKLE_FILE).exists():
        print(f"🔍 Found existing results file")
        return

    # Find images
    print("Finding images...")
    image_files = []
    for dirpath, _, filenames in os.walk(FOLDER_PATH):
        for filename in filenames:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                image_files.append(os.path.join(dirpath, filename))
    
    print(f"Found {len(image_files)} images to process")

    # Process images with progress bar
    histograms = {}
    for img_path in tqdm(image_files, desc="Processing images"):
        result = compute_bgr_histogram(img_path, FOLDER_PATH, BINS)
        if result:
            histograms[result['relative_path']] = {
                'histogram': result['histogram'],
                'img_shape': result['img_shape'],
                'img_path': result['img_path'],
                'bins': result['bins']
            }
    
    # Save results
    with open(HISTOGRAM_PICKLE_FILE, 'wb') as f:
        pickle.dump(histograms, f)
    print(f"✅ Saved results to {HISTOGRAM_PICKLE_FILE}")

    # Verification
    if histograms:
        first_key = next(iter(histograms.keys()))
        print("\nFirst image verification:")
        print(f"Path: {histograms[first_key]['img_path']}")
        print(f"Shape: {histograms[first_key]['img_shape']}")
        print(f"Histogram shape: {histograms[first_key]['histogram'].shape}")
        print(f"Histogram sum: {np.sum(histograms[first_key]['histogram']):.4f} (should be ~1.0)")
        print(f"First 5 values: {histograms[first_key]['histogram'][:5]}")

if __name__ == "__main__":
    main()