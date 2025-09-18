#!/usr/bin/env python3
"""
Collection-wide pose scale/area robustness probe for MediaPipe solutions.pose (single-person).

For each image:
  1) Detect on original. If none, skip.
  2) Shrink isotropically (letterbox on same canvas) until detection FAILS.
     Keep the "last success" frame (smallest still-detected pose).
  3) Expand canvas around that smallest-success frame by EXPAND_STEP each step
     (white background), recording area percentage at each *successful* step.
     Stop after MAX_CONSEC_FAILS consecutive failures.
We keep doing this for images until we've gathered MAX_POSES successes (i.e.,  N images
that had a successful smallest-pose step), then stop scanning.

At the end, print global statistics across all recorded area percentages:
  count, mean, std, min, max (in %).

Usage:
  python pose_collection_limit_test.py
"""

import os
import cv2
import math
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional

from tqdm import tqdm
import mediapipe as mp
import warnings
warnings.filterwarnings("ignore")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")  # quieter TF logs

# ---------------- Configuration ----------------
FOLDER_PATH          = "./wikiart"  # root directory to scan
IMAGE_EXTS           = (".png", ".jpg", ".jpeg", ".webp")

# Stop after this many *successful* poses (images where we found smallest still-detected)
MAX_POSES            = 1000

# Shrinking (to find smallest still-detected pose)
SHRINK_FACTOR_STEP   = 0.90  # each step multiply scale by this (1.0, 0.90, 0.81, ...)
MIN_SCALE            = 0.02  # stop shrinking if scale would go below this

# Canvas expansion (after smallest success)
EXPAND_STEP          = 1.01  # e.g., 1.01 -> +1% each step
MAX_CONSEC_FAILS     = 2     # stop expanding after this many consecutive failures

# MediaPipe pose config (classic single-person)
DET_MIN_CONF         = 0.5
MIN_LANDMARKS_REQ    = 3      # landmarks needed for a valid bbox
# ------------------------------------------------


def find_images_recursive(root: str) -> List[str]:
    out = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(IMAGE_EXTS):
                out.append(os.path.join(dirpath, fn))
    return out


def letterbox_scale(img_bgr, sx: float, sy: float):
    """Keep same canvas size; scale content by (sx, sy); center; pad with black."""
    H, W = img_bgr.shape[:2]
    new_w = max(1, int(round(W * sx)))
    new_h = max(1, int(round(H * sy)))
    resized = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    canvas = np.zeros_like(img_bgr)  # black background
    x0 = (W - new_w) // 2
    y0 = (H - new_h) // 2
    canvas[y0:y0 + new_h, x0:x0 + new_w] = resized
    return canvas


def expand_canvas_keep_content(img_bgr, factor: float, bg: int = 255):
    """Expand canvas by 'factor' with a white background; center original content unchanged."""
    H, W = img_bgr.shape[:2]
    newH = max(1, int(round(H * factor)))
    newW = max(1, int(round(W * factor)))
    big = np.full((newH, newW, 3), fill_value=bg, dtype=img_bgr.dtype)
    y0 = (newH - H) // 2
    x0 = (newW - W) // 2
    big[y0:y0 + H, x0:x0 + W] = img_bgr
    return big


def bbox_from_landmarks_px(landmarks, img_w: int, img_h: int) -> Optional[Tuple[float, float, float, float]]:
    """Raw bbox from normalized landmarks -> (xmin, ymin, xmax, ymax) in pixel space."""
    xs, ys = [], []
    for lm in landmarks:
        if lm.x is None or lm.y is None or math.isnan(lm.x) or math.isnan(lm.y):
            continue
        xs.append(lm.x * img_w)
        ys.append(lm.y * img_h)
    if len(xs) < MIN_LANDMARKS_REQ:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def clip_bbox_to_image(bbox, img_w: int, img_h: int) -> Optional[Tuple[int, int, int, int]]:
    """Clip bbox to [0, W) × [0, H). Return integer (x0,y0,x1,y1) or None if zero/neg area."""
    xmin, ymin, xmax, ymax = bbox
    x0 = max(0.0, min(float(img_w), xmin))
    y0 = max(0.0, min(float(img_h), ymin))
    x1 = max(0.0, min(float(img_w), xmax))
    y1 = max(0.0, min(float(img_h), ymax))
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    w = int(round(x1 - x0))
    h = int(round(y1 - y0))
    if w <= 0 or h <= 0:
        return None
    return int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))


def detect_pose_bbox(img_bgr, pose) -> Optional[Tuple[int, int, int, int]]:
    """Run classic single-person Pose and return a clipped bbox, or None if no detection."""
    H, W = img_bgr.shape[:2]
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    res = pose.process(rgb)
    if not res or not res.pose_landmarks:
        return None
    raw = bbox_from_landmarks_px(res.pose_landmarks.landmark, W, H)
    if raw is None:
        return None
    return clip_bbox_to_image(raw, W, H)


def area_percentage_from_bbox(bbox: Tuple[int, int, int, int], W: int, H: int) -> float:
    """Return 100 * bbox_area / image_area."""
    x0, y0, x1, y1 = bbox
    w = x1 - x0
    h = y1 - y0
    area = w * h
    img_area = W * H
    if img_area <= 0:
        return 0.0
    return 100.0 * area / float(img_area)


def process_one_image(img_path: str, pose, expand_step: float, max_consec_fails: int) -> List[float]:
    """
    Process a single image: find smallest still-detected pose, then expand canvas
    step-by-step and record area percentage for each successful step.
    Returns the list of area percentages (may be empty if no detection on original).
    """
    img = cv2.imread(img_path)
    if img is None or img.size == 0:
        return []

    # Original detection
    bbox0 = detect_pose_bbox(img, pose)
    if bbox0 is None:
        return []

    # Shrink until fail; keep last success
    s = 1.0
    last_img = img
    last_bbox = bbox0

    while s > MIN_SCALE:
        s *= SHRINK_FACTOR_STEP
        test = letterbox_scale(img, s, s)
        bbox = detect_pose_bbox(test, pose)
        if bbox is None:
            break
        last_img = test
        last_bbox = bbox

    # Start with the smallest-success frame
    ratios_pct: List[float] = []
    ratios_pct.append(area_percentage_from_bbox(last_bbox, last_img.shape[1], last_img.shape[0]))

    # Expand canvas gradually; record each successful area %
    factor = 1.0
    consec_fails = 0
    while consec_fails < max_consec_fails:
        factor *= expand_step
        big = expand_canvas_keep_content(last_img, factor, bg=255)
        bbox = detect_pose_bbox(big, pose)
        if bbox is not None:
            consec_fails = 0
            ratios_pct.append(area_percentage_from_bbox(bbox, big.shape[1], big.shape[0]))
        else:
            consec_fails += 1

    return ratios_pct


def summarize(name: str, values_pct: List[float]):
    arr = np.array(values_pct, dtype=np.float64)
    n = arr.size
    if n == 0:
        print(f"{name}: no samples")
        return
    mean = float(arr.mean())
    std = float(arr.std(ddof=1)) if n > 1 else 0.0
    vmin = float(arr.min())
    vmax = float(arr.max())
    print(f"\n{name} (area % over all successful steps)")
    print(f"  samples: {n}")
    print(f"  mean:    {mean:.6f} %")
    print(f"  std:     {std:.6f} %")
    print(f"  min:     {vmin:.6f} %")
    print(f"  max:     {vmax:.6f} %")


def main():
    images = find_images_recursive(FOLDER_PATH)
    if not images:
        print(f"No images found under: {FOLDER_PATH}")
        return

    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=DET_MIN_CONF)

    all_area_percentages: List[float] = []
    poses_processed = 0

    for img_path in tqdm(images, desc="Probing images", unit="img"):
        try:
            series = process_one_image(
                img_path,
                pose=pose,
                expand_step=EXPAND_STEP,
                max_consec_fails=MAX_CONSEC_FAILS
            )
            if not series:
                continue

            # Count this image as one "pose" processed
            poses_processed += 1
            all_area_percentages.extend(series)

            # Optional: quick per-image note; comment out if too verbose
            # print(f"{img_path} -> steps: {len(series)} (last %: {series[-1]:.6f})")

            if poses_processed >= MAX_POSES:
                break

        except Exception as e:
            print(f"Warning on {img_path}: {e}")

    print(f"\nImages scanned: {len(images)}")
    print(f"Poses processed (successful images): {poses_processed}")
    summarize("GLOBAL", all_area_percentages)


if __name__ == "__main__":
    main()
