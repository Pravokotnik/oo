#!/usr/bin/env python3
"""
Find detection limits for MediaPipe solutions.pose (single-person) by progressively
shrinking people relative to the image canvas and binary-searching the smallest size
that still yields a detection.

We test 3 cases per image:
  A) Isotropic shrink:      (scale_x = s, scale_y = s)  -> area ratio limit
  B) Horizontal-only:       (scale_x = s, scale_y = 1)  -> min width limit
  C) Vertical-only:         (scale_x = 1, scale_y = s)  -> min height limit

For the "last successful" scale in each case, we compute a clipped bbox and derive:
  - width (px), height (px), area (px^2), area_ratio = area / (W*H)

We print per-image thresholds and global minima. No files saved.
"""

import os
import cv2
import math
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, List, Dict

from tqdm import tqdm
import mediapipe as mp
import warnings
warnings.filterwarnings("ignore")

# ---------------- CONFIG ----------------
FOLDER_PATH = "./wikiart"    # root of your dataset
IMAGE_EXTS  = (".png", ".jpg", ".jpeg", ".webp")

# Binary search parameters
S_MIN = 0.01      # search lower bound for scale
S_MAX = 1.00      # start from original size
TOL   = 0.005     # stop when high-low < TOL
MAX_ITERS = 20

# Pose settings (same as your program)
MIN_LANDMARKS_REQUIRED = 3
DET_MIN_CONF = 0.5
# ---------------------------------------


def find_images_recursive(root: str) -> List[str]:
    out = []
    for d, _, files in os.walk(root):
        for fn in files:
            if fn.lower().endswith(IMAGE_EXTS):
                out.append(os.path.join(d, fn))
    return out


def letterbox_scale(img: np.ndarray, scale_x: float, scale_y: float) -> np.ndarray:
    """
    Return a new image of the same WxH as input, where the content is scaled by
    (scale_x, scale_y) and centered; remaining area is padded with black.
    """
    H, W = img.shape[:2]
    new_w = max(1, int(round(W * scale_x)))
    new_h = max(1, int(round(H * scale_y)))

    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    canvas = np.zeros_like(img)

    x0 = (W - new_w) // 2
    y0 = (H - new_h) // 2
    canvas[y0:y0+new_h, x0:x0+new_w] = resized
    return canvas


def bbox_from_landmarks_px(landmarks, img_w: int, img_h: int) -> Optional[Tuple[float, float, float, float]]:
    xs, ys = [], []
    for lm in landmarks:
        if lm.x is None or lm.y is None or math.isnan(lm.x) or math.isnan(lm.y):
            continue
        xs.append(lm.x * img_w)
        ys.append(lm.y * img_h)
    if len(xs) < MIN_LANDMARKS_REQUIRED:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def clip_bbox_to_image(bbox: Tuple[float, float, float, float], W: int, H: int) -> Optional[Tuple[int, int, int, int]]:
    xmin, ymin, xmax, ymax = bbox
    x0 = max(0.0, min(float(W), xmin))
    y0 = max(0.0, min(float(H), ymin))
    x1 = max(0.0, min(float(W), xmax))
    y1 = max(0.0, min(float(H), ymax))
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    w = int(round(x1 - x0))
    h = int(round(y1 - y0))
    if w <= 0 or h <= 0:
        return None
    return int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))


def detect_pose_bbox(img_bgr: np.ndarray, pose) -> Optional[Tuple[int,int,int,int]]:
    """Run single-person pose and return a CLIPPED bbox or None if no detection."""
    H, W = img_bgr.shape[:2]
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    res = pose.process(rgb)
    if not res or not res.pose_landmarks:
        return None
    raw = bbox_from_landmarks_px(res.pose_landmarks.landmark, W, H)
    if raw is None:
        return None
    clipped = clip_bbox_to_image(raw, W, H)
    return clipped


def metric_from_bbox(bbox: Tuple[int,int,int,int], W: int, H: int) -> Dict[str, float]:
    x0,y0,x1,y1 = bbox
    bw = x1 - x0
    bh = y1 - y0
    area = bw * bh
    return {
        "width_px":  bw,
        "height_px": bh,
        "area_px2":  area,
        "area_ratio": area / float(W*H) if W>0 and H>0 else float("inf"),
    }


def search_limit(img_bgr: np.ndarray, pose, mode: str) -> Optional[Dict[str, float]]:
    """
    Binary search the smallest scale 's' that still yields detection, for:
      mode == "iso"  -> (sx = s, sy = s)
      mode == "h"    -> (sx = s, sy = 1)
      mode == "v"    -> (sx = 1, sy = s)

    Returns metrics at the last successful scale, or None if never detected.
    """
    assert mode in ("iso", "h", "v")
    H, W = img_bgr.shape[:2]

    low, high = S_MIN, S_MAX  # invariant: low=known_fail, high=known_success (we'll ensure a success first)
    # First check if original detects:
    bbox0 = detect_pose_bbox(img_bgr, pose)
    if bbox0 is None:
        return None  # cannot test this image for this mode

    # Initialize search bounds:
    known_success_bbox = bbox0
    known_success_scale = 1.0

    # Try shrinking until it fails at low bound (optional warm-up)
    # We'll just start binary search directly.

    iters = 0
    while (high - low) > TOL and iters < MAX_ITERS:
        iters += 1
        mid = (low + high) / 2.0
        if mode == "iso":
            test = letterbox_scale(img_bgr, mid, mid)
        elif mode == "h":
            test = letterbox_scale(img_bgr, mid, 1.0)
        else:  # "v"
            test = letterbox_scale(img_bgr, 1.0, mid)

        bbox = detect_pose_bbox(test, pose)
        if bbox is not None:
            # success -> try smaller (move high down)
            high = mid
            known_success_bbox = bbox
            known_success_scale = mid
        else:
            # fail -> move low up
            low = mid

    # Use the last success to compute metrics on that test image
    if mode == "iso":
        best_img = letterbox_scale(img_bgr, known_success_scale, known_success_scale)
    elif mode == "h":
        best_img = letterbox_scale(img_bgr, known_success_scale, 1.0)
    else:
        best_img = letterbox_scale(img_bgr, 1.0, known_success_scale)

    # We already have known_success_bbox for that "best_img" because we saved it when success happened.
    metrics = metric_from_bbox(known_success_bbox, W=best_img.shape[1], H=best_img.shape[0])
    metrics["scale"] = known_success_scale
    return metrics


def main():
    # Init detector (single-person, like your code)
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=DET_MIN_CONF)

    images = find_images_recursive(FOLDER_PATH)
    if not images:
        print(f"No images under {FOLDER_PATH}")
        return

    # Global minima trackers for each mode and metric
    global_min = {
        # per mode, track minima over width_px, height_px, area_px2, area_ratio
        "iso": {"width_px": (float("inf"), ""), "height_px": (float("inf"), ""), "area_px2": (float("inf"), ""), "area_ratio": (float("inf"), "")},
        "h":   {"width_px": (float("inf"), ""), "height_px": (float("inf"), ""), "area_px2": (float("inf"), ""), "area_ratio": (float("inf"), "")},
        "v":   {"width_px": (float("inf"), ""), "height_px": (float("inf"), ""), "area_px2": (float("inf"), ""), "area_ratio": (float("inf"), "")},
    }

    def maybe_update(mode: str, metrics: Dict[str, float], img_path: str) -> bool:
        changed = False
        for k in ("width_px","height_px","area_px2","area_ratio"):
            val, path = global_min[mode][k]
            if metrics[k] < val:
                global_min[mode][k] = (metrics[k], img_path)
                changed = True
        return changed

    def print_block(title: str, d: Dict[str, Tuple[float,str]]):
        print(f"\n[{title}] current minima:")
        wv, wp = d["width_px"];   print(f"WIDTH(px):   {int(wv) if wv < float('inf') else wv} | {wp}")
        hv, hp = d["height_px"];  print(f"HEIGHT(px):  {int(hv) if hv < float('inf') else hv} | {hp}")
        av, ap = d["area_px2"];   print(f"AREA(px^2):  {int(av) if av < float('inf') else av} | {ap}")
        rv, rp = d["area_ratio"]; print(f"AREA RATIO:  {rv:.8f} | {rp}" if rv < float('inf') else f"AREA RATIO:  {rv} | {rp}")

    for img_path in tqdm(images, desc="Probing limits", unit="img"):
        img = cv2.imread(img_path)
        if img is None or img.size == 0:
            continue

        # For each mode, search the smallest detectable scale and update minima
        for mode, label in (("iso","ISOTROPIC"), ("h","HORIZONTAL-ONLY"), ("v","VERTICAL-ONLY")):
            try:
                metrics = search_limit(img, pose, mode)
                if metrics is None:
                    continue  # this image not usable for this mode
                if maybe_update(mode, metrics, img_path):
                    # If any metric improved, print ALL four for this mode
                    print_block(label, global_min[mode])
            except Exception as e:
                print(f"Warning on {img_path} [{mode}]: {e}")

    # Final snapshot
    print("\n=== FINAL GLOBAL MINIMA ===")
    print_block("ISOTROPIC", global_min["iso"])
    print_block("HORIZONTAL-ONLY", global_min["h"])
    print_block("VERTICAL-ONLY", global_min["v"])


if __name__ == "__main__":
    main()
