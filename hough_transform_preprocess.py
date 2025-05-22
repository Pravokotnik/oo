import os
import cv2
import numpy as np
import pickle
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from hough_utils import hough_find_lines3, nonmaxima_suppression_box, findedges

INPUT_FOLDER = './wikiart/'
OUTPUT_DIR = './pickles_by_style/'
NUM_WORKERS = 8
RESIZE_FACTOR = 0.25  # More aggressive downscale to reduce memory use

os.makedirs(OUTPUT_DIR, exist_ok=True)

def imread_unicode(path):
    import numpy as np
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

def process_single_image(img_path, base_folder):
    original = imread_unicode(img_path)
    if original is None:
        print(f"⚠️ Warning: could not read {img_path}")
        return None, img_path

    # Auto resize if very large
    if original.shape[0] * original.shape[1] > 2_000_000:
        scale = np.sqrt(2_000_000 / (original.shape[0] * original.shape[1]))
        original = cv2.resize(original, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)

    if RESIZE_FACTOR != 1.0:
        gray = cv2.resize(gray, (0, 0), fx=RESIZE_FACTOR, fy=RESIZE_FACTOR, interpolation=cv2.INTER_AREA)

    edges = canny_edge(gray)
    acc = hough_find_lines3(gray, 180, 180, t=0.2)
    acc = nonmaxima_suppression_box(acc)
    sinusoids_vis = create_hough_sinusoids(edges, 180, 180)

    rel_path = os.path.relpath(img_path, base_folder)
    key = rel_path.replace(os.sep, '_')

    data = {
        'path': img_path,
        'shape': gray.shape,
        'edges': edges.astype(np.uint8),
        'accumulator': acc.astype(np.float32),
        'sinusoids_vis': sinusoids_vis,
    }
    return key, data

def process_style_folder(style_folder_path, max_workers=NUM_WORKERS):
    style_name = os.path.basename(style_folder_path)
    output_file = os.path.join(OUTPUT_DIR, f"hough_data_{style_name}.pkl")

    # Skip if pickle file already exists
    if os.path.exists(output_file):
        print(f"Skipping '{style_name}' because pickle file already exists at {output_file}")
        return

    print(f"\nProcessing style folder: {style_folder_path}")
    image_paths = [os.path.join(style_folder_path, f)
                   for f in os.listdir(style_folder_path)
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

    print(f"Saving data for style '{style_name}' to {output_file} ...")
    with open(output_file, 'wb') as f:
        pickle.dump(all_data, f)
    print(f"Done processing style '{style_name}'.")

def main():
    style_folders = [os.path.join(INPUT_FOLDER, d) for d in os.listdir(INPUT_FOLDER)
                     if os.path.isdir(os.path.join(INPUT_FOLDER, d))]

    for style_folder in style_folders:
        process_style_folder(style_folder, NUM_WORKERS)

if __name__ == "__main__":
    main()
