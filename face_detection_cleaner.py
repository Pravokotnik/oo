import pickle
from pathlib import Path
import tqdm

# Config
INPUT_PICKLE = "./pickles/emotion_cache.pkl"  # Original results
OUTPUT_PICKLE = "./pickles/emotion_cache_filtered.pkl"  # Cleaned results
MIN_FACE_AREA_PCT = 1.0  # Minimum % of image that CAN'T be face (1% = reject ≥99% faces)

def is_invalid_face(detection, img_width, img_height):
    """Check if face covers too much of the image"""
    face_area = detection["face_region"]["w"] * detection["face_region"]["h"]
    img_area = img_width * img_height
    face_pct = (face_area / img_area) * 100
    return face_pct >= (100 - MIN_FACE_AREA_PCT)

def filter_false_positives(results):
    """Remove detections where face covers nearly the entire image"""
    filtered = {}
    skipped_count = 0
    
    for img_path, data in tqdm.tqdm(results.items(), desc="Filtering faces"):
        if data is None:
            continue
            
        img_width, img_height = data["face_region"]["w"] + data["face_region"]["x"], data["face_region"]["h"] + data["face_region"]["y"]
        
        if not is_invalid_face(data, img_width, img_height):
            filtered[img_path] = data
        else:
            skipped_count += 1
    
    print(f"\nRemoved {skipped_count} false-positive faces (≥{100 - MIN_FACE_AREA_PCT}% coverage)")
    return filtered

def main():
    # Load original results
    with open(INPUT_PICKLE, "rb") as f:
        original_results = pickle.load(f)
    
    # Filter results
    filtered_results = filter_false_positives(original_results)
    
    # Save cleaned data
    with open(OUTPUT_PICKLE, "wb") as f:
        pickle.dump(filtered_results, f)
    
    print(f"✅ Saved filtered results to {OUTPUT_PICKLE}")
    print(f"Original: {len(original_results)} entries → New: {len(filtered_results)} entries")

if __name__ == "__main__":
    main()