# chunked_json_converter.py
import json
import pickle
import os
from math import ceil
from tqdm import tqdm

def convert_to_chunks(pickle_path, output_dir, chunk_size=1000):
    os.makedirs(output_dir, exist_ok=True)
    
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f)
    
    items = list(data.items())
    total_chunks = ceil(len(items) / chunk_size)
    
    for chunk_idx in tqdm(range(total_chunks), desc="Creating chunks"):
        chunk_data = {}
        start = chunk_idx * chunk_size
        end = start + chunk_size
        
        for rel_path, img_data in items[start:end]:
            # Store with original path as key
            chunk_data[rel_path] = {
                'histogram': img_data['histogram'].tolist(),
                'img_path': img_data['img_path'].replace('\\', '/'),
                'img_shape': img_data['img_shape'],
                'bins': img_data['bins']
            }
        
        # Save as chunk_0001.json, etc.
        with open(os.path.join(output_dir, f"chunk_{chunk_idx:04d}.json"), 'w') as f:
            json.dump(chunk_data, f)

if __name__ == "__main__":
    convert_to_chunks(
        "pickles/color_histograms.pkl",
        "histogram_chunks",
        chunk_size=1000  # Adjust based on performance
    )