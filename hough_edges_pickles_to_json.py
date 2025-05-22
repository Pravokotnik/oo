import os
import pickle
import json
import numpy as np

# Set your folder paths here:
PICKLE_FOLDERS = ['./pickles_by_style/', './pickles_edges_by_style/']
OUTPUT_FOLDER_BASE = './hough_edges_json_output/'

# Max size for each JSON file (100 MB)
MAX_JSON_SIZE_BYTES = 100 * 1024 * 1024  # 100MB

def numpy_to_list(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError("Unknown type")

def save_json_chunks(data_dict, base_output_path):
    """
    Save data_dict as multiple JSON files under 100MB each.
    """
    chunk = {}
    current_size = 0
    chunk_idx = 1

    for key, value in data_dict.items():
        # Convert numpy arrays to lists recursively for JSON serialization
        def convert(obj):
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            else:
                return obj
        json_val = convert(value)

        # Estimate size of this entry when dumped to JSON
        entry_json = json.dumps({key: json_val}, separators=(',', ':'))
        entry_size = len(entry_json.encode('utf-8'))

        # If adding this entry exceeds max size, save current chunk and start new
        if current_size + entry_size > MAX_JSON_SIZE_BYTES and chunk:
            out_path = f"{base_output_path}_part{chunk_idx}.json"
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, separators=(',', ':'), ensure_ascii=False)
            print(f"Saved {out_path} with {len(chunk)} items, size ~{current_size / (1024*1024):.2f} MB")
            chunk_idx += 1
            chunk = {}
            current_size = 0

        chunk[key] = json_val
        current_size += entry_size

    # Save remaining chunk
    if chunk:
        out_path = f"{base_output_path}_part{chunk_idx}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, separators=(',', ':'), ensure_ascii=False)
        print(f"Saved {out_path} with {len(chunk)} items, size ~{current_size / (1024*1024):.2f} MB")

def convert_pickles_to_json(pickle_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    pickle_files = [f for f in os.listdir(pickle_folder) if f.endswith('.pkl')]

    for pf in pickle_files:
        pickle_path = os.path.join(pickle_folder, pf)
        base_name = os.path.splitext(pf)[0]
        base_output_path = os.path.join(output_folder, base_name)

        # Check if JSON chunk(s) already exist for this pickle
        existing_jsons = [f for f in os.listdir(output_folder) if f.startswith(base_name) and f.endswith('.json')]
        if existing_jsons:
            print(f"Skipping '{pf}', JSON chunks already exist.")
            continue

        print(f"Loading pickle: {pickle_path}")
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)

        print(f"Converting and saving to JSON chunks with base path: {base_output_path}")
        save_json_chunks(data, base_output_path)


def main():
    for folder in PICKLE_FOLDERS:
        output_folder = OUTPUT_FOLDER_BASE + os.path.basename(os.path.normpath(folder)) + '/'
        convert_pickles_to_json(folder, output_folder)

if __name__ == '__main__':
    main()
