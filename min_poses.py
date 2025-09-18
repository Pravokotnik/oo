#!/usr/bin/env python3
"""
Scan a folder recursively using MediaPipe solutions.pose (single-person),
track global minima across all images for:

1) min bbox height (px)
2) min bbox width  (px)
3) min bbox area   (px^2)
4) min (bbox area / image area)

Whenever ANY of these improves, print ALL FOUR current minima, each on its own line:
- WIDTH(px):  <value> | <image_path>
- HEIGHT(px): <value> | <image_path>
- AREA(px^2): <value> | <image_path>
- AREA RATIO: <value> | <image_path>

No files are written.
"""

import os
import cv2
import math
from pathlib import Path
from typing import List, Tuple, Optional

from tqdm import tqdm
import mediapipe as mp
import warnings
warnings.filterwarnings("ignore")

# --------------- CONFIG ---------------
FOLDER_PATH = "./wikiart"   # root folder to scan (change as needed)
IMAGE_EXTS  = (".png", ".jpg", ".jpeg", ".webp")
MIN_LANDMARKS_REQUIRED = 3  # ignore if too few valid points
# --------------------------------------


def find_images_recursive(root_folder: str) -> List[str]:
    images = []
    for dirpath, _, filenames in os.walk(root_folder):
        for fn in filenames:
            if fn.lower().endswith(IMAGE_EXTS):
                images.append(os.path.join(dirpath, fn))
    return images


def bbox_from_landmarks_px(
    landmarks, img_w: int, img_h: int
) -> Optional[Tuple[float, float, float, float]]:
    """
    Raw bbox (xmin, ymin, xmax, ymax) in pixel coords from normalized landmarks.
    Landmarks may lie slightly outside [0,1]. Returns None if too few usable points.
    """
    xs, ys = [], []
    for lm in landmarks:
        if lm.x is None or lm.y is None or math.isnan(lm.x) or math.isnan(lm.y):
            continue
        xs.append(lm.x * img_w)
        ys.append(lm.y * img_h)

    if len(xs) < MIN_LANDMARKS_REQUIRED:
        return None

    return min(xs), min(ys), max(xs), max(ys)


def clip_bbox_to_image(
    bbox: Tuple[float, float, float, float], img_w: int, img_h: int
) -> Optional[Tuple[int, int, int, int]]:
    """
    Intersect (xmin, ymin, xmax, ymax) with image rect [0,w) x [0,h).
    Returns integer (x0, y0, x1, y1) or None if no overlap.
    """
    xmin, ymin, xmax, ymax = bbox

    x0 = max(0.0, min(float(img_w), xmin))
    y0 = max(0.0, min(float(img_h), ymin))
    x1 = max(0.0, min(float(img_w), xmax))
    y1 = max(0.0, min(float(img_h), ymax))

    # ensure proper ordering
    x0c, x1c = min(x0, x1), max(x0, x1)
    y0c, y1c = min(y0, y1), max(y0, y1)

    w = int(round(x1c - x0c))
    h = int(round(y1c - y0c))
    if w <= 0 or h <= 0:
        return None

    return int(round(x0c)), int(round(y0c)), int(round(x1c)), int(round(y1c))


def main():
    images = find_images_recursive(FOLDER_PATH)
    if not images:
        print(f"No images found under: {FOLDER_PATH}")
        return

    # Init single-person pose detector (same as your program)
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5)

    # Global minima trackers: (value, img_path)
    min_w   = (float("inf"), "")
    min_h   = (float("inf"), "")
    min_a   = (float("inf"), "")
    min_r   = (float("inf"), "")

    def try_update_min(current, candidate_value, img_path):
        """Return (updated_flag, new_state_tuple)"""
        cur_val, _ = current
        if candidate_value < cur_val:
            return True, (candidate_value, img_path)
        return False, current

    def print_all_minima():
        print("\n=== New minima found ===")
        print(f"WIDTH(px):  {int(min_w[0])} | {min_w[1]}")
        print(f"HEIGHT(px): {int(min_h[0])} | {min_h[1]}")
        print(f"AREA(px^2): {int(min_a[0])} | {min_a[1]}")
        print(f"AREA RATIO: {min_r[0]:.8f} | {min_r[1]}")

    for img_path in tqdm(images, desc="Scanning", unit="img"):
        try:
            img = cv2.imread(img_path)
            if img is None:
                continue
            H, W = img.shape[:2]
            if W == 0 or H == 0:
                continue
            img_area = W * H

            # Detect pose (single person)
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)
            if not results or not results.pose_landmarks:
                continue

            # Build bbox from landmarks -> clip to image
            raw_bbox = bbox_from_landmarks_px(results.pose_landmarks.landmark, W, H)
            if raw_bbox is None:
                continue
            clipped = clip_bbox_to_image(raw_bbox, W, H)
            if clipped is None:
                continue

            x0, y0, x1, y1 = clipped
            bw = x1 - x0
            bh = y1 - y0
            ba = bw * bh
            ratio = ba / img_area if img_area > 0 else float("inf")

            changed = False
            updated, min_w_new = try_update_min(min_w, bw, img_path); changed |= updated; min_w = min_w_new
            updated, min_h_new = try_update_min(min_h, bh, img_path); changed |= updated; min_h = min_h_new
            updated, min_a_new = try_update_min(min_a, ba, img_path); changed |= updated; min_a = min_a_new
            updated, min_r_new = try_update_min(min_r, ratio, img_path); changed |= updated; min_r = min_r_new

            if changed:
                print_all_minima()

        except Exception as e:
            print(f"Warning: error on {img_path}: {e}")

    # Optional: final snapshot (in case nothing changed after the last print)
    if all(v[0] < float("inf") for v in (min_w, min_h, min_a, min_r)):
        print("\n=== Final minima ===")
        print_all_minima()


if __name__ == "__main__":
    main()
