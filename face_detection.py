import os
import pickle
from tqdm import tqdm
from pathlib import Path
from deepface import DeepFace
import cv2

# Config
IMAGE_DIR = "./wikiart/"  # Your image folder
PICKLE_PATH = "./pickles/emotion_cache.pkl"
DETECTOR_BACKEND = "opencv"  # "mtcnn" for more accuracy (slower)

def scan_images(image_dir):
    """Find all images recursively"""
    return [
        os.path.join(root, f)
        for root, _, files in os.walk(image_dir)
        for f in files
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]

def analyze_emotions(image_paths, cache_path):
    """Batch-process images with cached results (ONLY saves faces)"""
    if Path(cache_path).exists():
        with open(cache_path, "rb") as f:
            return pickle.load(f)
    
    results = {}
    for img_path in tqdm(image_paths, desc="Processing Faces"):
        try:
            analysis = DeepFace.analyze(
                img_path=img_path,
                actions=["emotion"],
                detector_backend=DETECTOR_BACKEND,
                enforce_detection=False,  # Skip if no face
                silent=True
            )
            if analysis:  # ONLY store if face detected <<<
                results[img_path] = {
                    "emotion": analysis[0]["emotion"],
                    "dominant": analysis[0]["dominant_emotion"],
                    "face_region": analysis[0]["region"]
                }
            # No 'else' clause = skip entirely <<<
        except Exception as e:
            print(f"⚠️ Error on {img_path}: {str(e)[:50]}...")
    
    with open(cache_path, "wb") as f:
        pickle.dump(results, f)
    return results

def main():
    image_paths = scan_images(IMAGE_DIR)
    emotion_data = analyze_emotions(image_paths, PICKLE_PATH)
    
    # Stats
    total_faces = sum(1 for v in emotion_data.values() if v)
    print(f"\n📊 Results: {total_faces}/{len(image_paths)} images had faces")
    print("Sample emotion data:", next(v for v in emotion_data.values() if v))

if __name__ == "__main__":
    main()