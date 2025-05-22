import os
import cv2
import numpy as np
import pickle
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

INPUT_FOLDER = './wikiart/'
OUTPUT_DIR = './pickles_edges_by_style/'
NUM_WORKERS = 4
RESIZE_MAX_PIXELS = 2_000_000
THRESH_LOW = 0.04
THRESH_HIGH = 0.16

os.makedirs(OUTPUT_DIR, exist_ok=True)

def imread_unicode(path):
    try:
        with open(path, 'rb') as f:
            img_bytes = f.read()
        img_array = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
        return img
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def resize_if_needed(img):
    h, w = img.shape
    if h * w > RESIZE_MAX_PIXELS:
        scale = np.sqrt(RESIZE_MAX_PIXELS / (h * w))
        img = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img

def compute_derivatives_opencv(I):
    Ix = cv2.Sobel(I, cv2.CV_64F, 1, 0, ksize=3)
    Iy = cv2.Sobel(I, cv2.CV_64F, 0, 1, ksize=3)
    return Ix, Iy

def gradient_magnitude(I):
    Ix, Iy = compute_derivatives_opencv(I)
    Im = np.hypot(Ix, Iy)
    Iphi = np.arctan2(Iy, Ix)
    return Im, Iphi

def non_maxima_suppression_vectorized(Im, Iphi):
    angle = np.rad2deg(Iphi) % 180
    h, w = Im.shape

    def shift(arr, dx, dy):
        shifted = np.roll(arr, shift=dy, axis=0)
        shifted = np.roll(shifted, shift=dx, axis=1)
        if dy > 0:
            shifted[:dy, :] = 0
        elif dy < 0:
            shifted[dy:, :] = 0
        if dx > 0:
            shifted[:, :dx] = 0
        elif dx < 0:
            shifted[:, dx:] = 0
        return shifted

    mask_0 = ((angle >= 0) & (angle < 22.5)) | ((angle >= 157.5) & (angle <= 180))
    mask_45 = (angle >= 22.5) & (angle < 67.5)
    mask_90 = (angle >= 67.5) & (angle < 112.5)
    mask_135 = (angle >= 112.5) & (angle < 157.5)

    left = shift(Im, -1, 0)
    right = shift(Im, 1, 0)
    cond_0 = (Im >= left) & (Im >= right)

    up_right = shift(Im, 1, -1)
    down_left = shift(Im, -1, 1)
    cond_45 = (Im >= up_right) & (Im >= down_left)

    up = shift(Im, 0, -1)
    down = shift(Im, 0, 1)
    cond_90 = (Im >= up) & (Im >= down)

    up_left = shift(Im, -1, -1)
    down_right = shift(Im, 1, 1)
    cond_135 = (Im >= up_left) & (Im >= down_right)

    nms_mask = (
        (mask_0 & cond_0) |
        (mask_45 & cond_45) |
        (mask_90 & cond_90) |
        (mask_135 & cond_135)
    )

    Z = np.where(nms_mask, Im, 0)
    return Z

def hysteresis_threshold(img, tlow, thigh):
    img_8u = np.uint8(np.clip(img / img.max() * 255, 0, 255))
    edges = cv2.Canny(img_8u, int(tlow * 255), int(thigh * 255))
    return edges

def quantize_and_downsample(Im, Iphi, n_downsample=2):
    Im_small = Im[::n_downsample, ::n_downsample]
    Iphi_small = Iphi[::n_downsample, ::n_downsample]

    Im_norm = (Im_small / (Im_small.max() + 1e-8) * 255).clip(0, 255).astype(np.uint8)
    Iphi_norm = ((Iphi_small + np.pi) / (2 * np.pi) * 255).clip(0, 255).astype(np.uint8)

    return Im_norm, Iphi_norm

def process_single_image(img_path, base_folder):
    gray = imread_unicode(img_path)
    if gray is None:
        print(f"⚠️ Warning: could not read {img_path}")
        return None, img_path

    gray = resize_if_needed(gray)

    Im, Iphi = gradient_magnitude(gray)
    nms = non_maxima_suppression_vectorized(Im, Iphi)
    hyst = hysteresis_threshold(nms, THRESH_LOW, THRESH_HIGH)

    Im_q, Iphi_q = quantize_and_downsample(Im, Iphi, n_downsample=2)
    nms_q = (nms[::2, ::2] / (nms.max() + 1e-8) * 255).clip(0, 255).astype(np.uint8)
    hyst_q = hyst[::2, ::2]

    rel_path = os.path.relpath(img_path, base_folder)
    key = rel_path.replace(os.sep, '_')

    data = {
        'path': img_path,
        'gradient_magnitude': Im_q,
        'gradient_angle': Iphi_q,
        'nonmaxima': nms_q,
        'hysteresis': hyst_q
    }
    return key, data

def process_style_folder(style_folder_path, max_workers=NUM_WORKERS):
    style_name = os.path.basename(style_folder_path)
    output_file = os.path.join(OUTPUT_DIR, f"edge_data_{style_name}.pkl")

    if os.path.exists(output_file):
        print(f"Skipping '{style_name}', pickle exists at {output_file}")
        return

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
