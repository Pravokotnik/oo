import os
import json
import pickle
from pathlib import Path
import math
from tqdm import tqdm

# Configuration - Update these paths as needed
INPUT_PICKLE = "./pickles/emotion_cache_filtered.pkl"
IMAGE_BASE_DIR = "./wikiart/"
OUTPUT_DIR = "./web_emotion_data/"
CHUNK_SIZE = 1000
GRID_SIZE = 20
EMOTION_AXES = {
    'x': ('angry', 'happy'),
    'y': ('sad', 'fear')
}

def rotate_point(x, y, angle_degrees=45):
    """Rotate a point around origin by given angle (degrees)"""
    theta = math.radians(angle_degrees)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    x_new = cos_t * x - sin_t * y
    y_new = sin_t * x + cos_t * y
    return x_new, y_new

def emotion_to_coords(emotions):
    """Convert emotion percentages to grid coordinates with rotation"""
    # Calculate axis values
    x_val = (emotions[EMOTION_AXES['x'][1]] - emotions[EMOTION_AXES['x'][0]]) / 100.0
    y_val = (emotions[EMOTION_AXES['y'][1]] - emotions[EMOTION_AXES['y'][0]]) / 100.0
    
    # Apply 45-degree rotation
    x_rot, y_rot = rotate_point(x_val, y_val, 45)
    
    # Map to grid coordinates
    x = int((x_rot + 1) * (GRID_SIZE - 1) / 2)
    y = int((y_rot + 1) * (GRID_SIZE - 1) / 2)
    
    # Ensure coordinates stay within grid bounds
    return (
        max(0, min(GRID_SIZE - 1, x)),
        max(0, min(GRID_SIZE - 1, y))
    )

def convert_to_web_format():
    # Create output directories
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    chunks_dir = os.path.join(OUTPUT_DIR, "chunks")
    Path(chunks_dir).mkdir(exist_ok=True)
    
    # Load emotion data
    with open(INPUT_PICKLE, "rb") as f:
        emotion_data = pickle.load(f)
    
    # Convert to relative paths and compute grid positions
    base_path = Path(IMAGE_BASE_DIR).resolve()
    processed_data = []
    
    for img_path, data in tqdm(emotion_data.items(), desc="Processing Images"):
        try:
            # Convert to relative path
            abs_path = Path(img_path).resolve()
            rel_path = str(abs_path.relative_to(base_path))
            
            # Compute grid coordinates
            x, y = emotion_to_coords(data["emotion"])
            
            processed_data.append({
                "path": rel_path.replace("\\", "/"),  # Standardize path format
                "grid_x": x,
                "grid_y": y,
                "dominant": data["dominant"],
                "emotion": data["emotion"],
                "face_region": data["face_region"]
            })
        except Exception as e:
            print(f"Skipping {img_path}: {str(e)}")
    
    # Create grid index
    grid_index = {}
    for item in processed_data:
        key = f"{item['grid_x']},{item['grid_y']}"
        if key not in grid_index:
            grid_index[key] = []
        grid_index[key].append(item["path"])
    
    # Create chunks
    for i in tqdm(range(0, len(processed_data), CHUNK_SIZE), desc="Creating Chunks"):
        chunk_data = {}
        chunk_items = processed_data[i:i+CHUNK_SIZE]
        
        for item in chunk_items:
            # Only store necessary data in chunks
            chunk_data[item["path"]] = {
                "grid_x": item["grid_x"],
                "grid_y": item["grid_y"],
                "dominant": item["dominant"],
                "emotion": item["emotion"],
                "face_region": item["face_region"]
            }
        
        # Save chunk
        with open(os.path.join(chunks_dir, f"chunk_{i//CHUNK_SIZE:04d}.json"), "w") as f:
            json.dump(chunk_data, f)
    
    # Save metadata
    metadata = {
        "grid_size": GRID_SIZE,
        "emotion_axes": EMOTION_AXES,
        "total_images": len(processed_data),
        "chunk_size": CHUNK_SIZE,
        "chunks": [f"chunk_{i//CHUNK_SIZE:04d}.json" 
                  for i in range(0, len(processed_data), CHUNK_SIZE)],
        "grid_index": grid_index
    }
    
    with open(os.path.join(OUTPUT_DIR, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nSuccessfully converted {len(processed_data)} images to web format")
    print(f"Chunks created: {len(metadata['chunks'])}")
    print(f"Metadata saved to: {os.path.join(OUTPUT_DIR, 'metadata.json')}")

if __name__ == "__main__":
    convert_to_web_format()