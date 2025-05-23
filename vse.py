import os
import cv2
import numpy as np
import json
import base64
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

INPUT_FOLDER = './wikiart/'
JSON_OUTPUT_DIR = './json_minimal_edges_base64/'
NUM_WORKERS = 4
RESIZE_FACTOR = 0.25  # downscale factor
MAX_JSON_SIZE_BYTES = 100 * 1024**2  # 100 MB max JSON size

os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)

def imread_unicode(path):
    try:
        with open(path, 'rb') as f:
            img_bytes = f.read()
        img_array = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def canny_edge(img_gray, sigma=1.0, low_thresh=0.2, high_thresh=0.5):
    blurred = cv2.GaussianBlur(img_gray, (0, 0), sigma)
    return cv2.Canny(blurred, int(low_thresh * 255), int(high_thresh * 255))

def quantize_downscale(img, scale=0.25):
    h, w = img.shape[:2]
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    resized = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
    return resized

def create_hough_sinusoids(edges, num_rho=180, num_theta=180):
    h, w = edges.shape
    D = int(np.ceil(np.sqrt(h**2 + w**2)))
    theta_range = np.linspace(-np.pi/2, np.pi/2, num_theta, dtype=np.float32)

    ys, xs = np.nonzero(edges)
    if len(xs) == 0:
        return np.zeros((num_rho, num_theta), dtype=np.uint8)

    xs = xs[:, None].astype(np.float32)
    ys = ys[:, None].astype(np.float32)

    cos_t = np.cos(theta_range)[None, :].astype(np.float32)
    sin_t = np.sin(theta_range)[None, :].astype(np.float32)

    rho_vals = xs * cos_t + ys * sin_t
    rho_idx = np.round(rho_vals + D).astype(np.int32)
    np.clip(rho_idx, 0, num_rho - 1, out=rho_idx)

    hough_vis = np.zeros((num_rho, num_theta), dtype=np.uint32)
    theta_idx = np.arange(num_theta)
    theta_idx = np.broadcast_to(theta_idx, rho_idx.shape)

    np.add.at(hough_vis, (rho_idx.ravel(), theta_idx.ravel()), 1)

    hough_vis = np.clip(hough_vis, 0, 255).astype(np.uint8)
    return hough_vis

import gzip
import io

def encode_array(arr: np.ndarray) -> dict:
    """
    Encode a numpy array as a gzip-compressed base64 string with shape and dtype metadata.
    """
    arr_bytes = arr.tobytes()
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode='wb') as f:
        f.write(arr_bytes)
    compressed_bytes = out.getvalue()

    b64_str = base64.b64encode(compressed_bytes).decode('ascii')
    return {
        'shape': arr.shape,
        'dtype': str(arr.dtype),
        'data': b64_str
    }

def process_single_image(img_path, base_folder):
    original = imread_unicode(img_path)
    if original is None:
        print(f"⚠️ Warning: could not read {img_path}")
        return None, img_path

    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    edges_full = canny_edge(gray)
    edges_ds = quantize_downscale(edges_full, RESIZE_FACTOR)

    # Precompute Hough sinusoids visualization on downscaled edges
    hough_sinusoids_vis = create_hough_sinusoids(edges_ds)

    rel_path = os.path.relpath(img_path, base_folder)
    key = rel_path.replace(os.sep, '_')

    data = {
        'path': img_path,
        'edges_downscaled': encode_array(edges_ds),
        'hough_sinusoids': encode_array(hough_sinusoids_vis),
    }
    return key, data

def save_json_chunks(data_dict, base_output_path, max_json_size=MAX_JSON_SIZE_BYTES):
    chunk = {}
    current_size = 0
    chunk_idx = 1

    for key, value in data_dict.items():
        entry_json = json.dumps({key: value}, separators=(',', ':'))
        entry_size = len(entry_json.encode('utf-8'))

        if current_size + entry_size > max_json_size and chunk:
            out_path = f"{base_output_path}_part{chunk_idx}.json"
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, separators=(',', ':'), ensure_ascii=False)
            print(f"Saved {out_path} with {len(chunk)} items, size ~{current_size / (1024**2):.2f} MB")
            chunk_idx += 1
            chunk = {}
            current_size = 0

        chunk[key] = value
        current_size += entry_size

    if chunk:
        out_path = f"{base_output_path}_part{chunk_idx}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, separators=(',', ':'), ensure_ascii=False)
        print(f"Saved {out_path} with {len(chunk)} items, size ~{current_size / (1024**2):.2f} MB")

def process_style_folder(style_folder_path, max_workers=NUM_WORKERS):
    style_name = os.path.basename(style_folder_path)
    print(f"\nProcessing style folder: {style_folder_path}")

    image_paths = [os.path.join(style_folder_path, f) for f in os.listdir(style_folder_path)
                   if f.lower().endswith(('.jpg', '.png', '.jpeg'))]

    all_data = {}

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_image, img, style_folder_path): img for img in image_paths}
        for future in tqdm(as_completed(futures), total=len(futures), desc=f"Processing {style_name}"):
            try:
                result = future.result()
                if result is None:
                    continue
                key, data = result
                if data is not None:
                    all_data[key] = data
            except Exception as e:
                print(f"Error processing image: {e}")

    output_folder = JSON_OUTPUT_DIR
    os.makedirs(output_folder, exist_ok=True)
    base_output_path = os.path.join(output_folder, style_name)
    save_json_chunks(all_data, base_output_path)

def main():
    style_folders = [os.path.join(INPUT_FOLDER, d) for d in os.listdir(INPUT_FOLDER)
                     if os.path.isdir(os.path.join(INPUT_FOLDER, d))]
    if not style_folders:
        print(f"No style folders found in {INPUT_FOLDER}")
        return

    for style_folder in style_folders:
        style_name = os.path.basename(style_folder)
        output_folder = os.path.join(JSON_OUTPUT_DIR, style_name)

        # Check if output folder exists and has JSON files
        if os.path.exists(output_folder) and any(f.endswith('.json') for f in os.listdir(output_folder)):
            print(f"Skipping '{style_name}' — already processed.")
            continue

        print(f"Processing style folder: {style_folder}")
        process_style_folder(style_folder, NUM_WORKERS)


if __name__ == "__main__":
    main()
