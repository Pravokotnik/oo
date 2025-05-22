import os
import cv2
import numpy as np
import pickle
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from hough_utils import hough_find_lines3, nonmaxima_suppression_box

INPUT_FOLDER = './wikiart/'
OUTPUT_FILE = 'pickles/hough_data_sample.pkl'  # changed output file for test
NUM_WORKERS = 4  # Adjust if you want
RESIZE_FACTOR = 0.5  # or 1.0 for no resize

def canny_edge(img_gray, sigma=1.0, low_thresh=0.1, high_thresh=0.3):
    blurred = cv2.GaussianBlur(img_gray, (0, 0), sigma)
    return cv2.Canny(blurred, int(low_thresh * 255), int(high_thresh * 255))

def create_hough_sinusoids(edges, num_rho=180, num_theta=180):
    h, w = edges.shape
    D = int(np.ceil(np.sqrt(h**2 + w**2)))
    theta_range = np.linspace(-np.pi/2, np.pi/2, num_theta)

    ys, xs = np.nonzero(edges)
    if len(xs) == 0:
        return np.zeros((num_rho, num_theta), dtype=np.uint8)

    xs = xs[:, None]
    ys = ys[:, None]

    cos_t = np.cos(theta_range)[None, :]
    sin_t = np.sin(theta_range)[None, :]

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
    original = cv2.imread(img_path)
    if original is None:
        print(f"⚠️ Warning: could not read {img_path}")
        return None, img_path

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

def process_all_images_parallel(folder, max_workers=NUM_WORKERS, max_images=10):
    image_paths = [os.path.join(dp, f)
                   for dp, _, files in os.walk(folder)
                   for f in files if f.lower().endswith(('.jpg', '.png', '.jpeg'))]

    image_paths = image_paths[:max_images]  # Take only first 10 images

    all_data = {}
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_image, img, folder): img for img in image_paths}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing images"):
            try:
                result = future.result()
                if result is None:
                    continue
                key, data = result
                if data is not None:
                    all_data[key] = data
            except Exception as e:
                print(f"Error processing image: {e}")

    return all_data

if __name__ == "__main__":
    print(f"Starting processing first 10 images in {INPUT_FOLDER} with {NUM_WORKERS} workers...")
    all_data = process_all_images_parallel(INPUT_FOLDER, NUM_WORKERS, max_images=10)

    print(f"\nSaving sample data to {OUTPUT_FILE} ...")
    with open(OUTPUT_FILE, 'wb') as f:
        pickle.dump(all_data, f)
    print("Done!")
