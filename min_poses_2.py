#!/usr/bin/env python3
"""
Pose detection limit test with MediaPipe solutions.pose (single-person).

Flow:
1) Detect on original image.
2) Shrink person isotropically until detection fails. Record smallest scale with success.
3) Expand canvas gradually by a chosen multiplier (e.g. 1.1 each step).
   Keep person pixel size fixed in the center.
   Stop when detection fails twice in a row.
4) Print and (optionally) visualize.

Usage:
  python pose_limit_test.py /path/to/standing_man.jpg [--show]
"""

import sys, os, math, cv2, numpy as np, warnings
warnings.filterwarnings("ignore")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import mediapipe as mp

# -------------------- Tunables --------------------
MIN_LANDMARKS_REQUIRED = 3
DET_MIN_CONF = 0.5
SHRINK_FACTOR_STEP = 0.9    # how much to shrink person each step until fail
MIN_SCALE = 0.02            # stop shrinking if scale gets this small
EXPAND_STEP = 1.05           # canvas expansion multiplier per step
STOP_AFTER_FAILS = 2        # stop after N consecutive failures
# --------------------------------------------------


def letterbox_scale(img_bgr, sx, sy):
    H, W = img_bgr.shape[:2]
    new_w = max(1, int(round(W * sx)))
    new_h = max(1, int(round(H * sy)))
    resized = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    canvas = np.zeros_like(img_bgr)  # black background
    x0 = (W - new_w) // 2
    y0 = (H - new_h) // 2
    canvas[y0:y0+new_h, x0:x0+new_w] = resized
    return canvas


def expand_canvas_keep_content(img_bgr, factor, bg=255):
    """Expand canvas by factor, put content centered on white background."""
    H, W = img_bgr.shape[:2]
    newH, newW = int(round(H*factor)), int(round(W*factor))
    big = np.full((newH, newW, 3), fill_value=bg, dtype=img_bgr.dtype)
    y0 = (newH - H)//2
    x0 = (newW - W)//2
    big[y0:y0+H, x0:x0+W] = img_bgr
    return big


def bbox_from_landmarks_px(landmarks, W, H):
    xs, ys = [], []
    for lm in landmarks:
        if lm.x is None or lm.y is None or math.isnan(lm.x) or math.isnan(lm.y):
            continue
        xs.append(lm.x * W); ys.append(lm.y * H)
    if len(xs) < MIN_LANDMARKS_REQUIRED: return None
    return min(xs), min(ys), max(xs), max(ys)


def clip_bbox_to_image(bbox, W, H):
    xmin,ymin,xmax,ymax = bbox
    x0 = max(0.0, min(W, xmin)); y0 = max(0.0, min(H, ymin))
    x1 = max(0.0, min(W, xmax)); y1 = max(0.0, min(H, ymax))
    x0,x1 = min(x0,x1), max(x0,x1); y0,y1 = min(y0,y1), max(y0,y1)
    w,h = int(round(x1-x0)), int(round(y1-y0))
    if w<=0 or h<=0: return None
    return int(x0),int(y0),int(x1),int(y1)


def detect_pose_bbox(img_bgr, pose):
    H,W = img_bgr.shape[:2]
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    res = pose.process(rgb)
    if not res or not res.pose_landmarks: return None
    raw = bbox_from_landmarks_px(res.pose_landmarks.landmark, W, H)
    if raw is None: return None
    return clip_bbox_to_image(raw, W, H)


def metrics_from_bbox(bbox, W, H):
    x0,y0,x1,y1 = bbox
    w,h = x1-x0, y1-y0
    area = w*h
    return dict(width_px=w, height_px=h, area_px2=area,
                area_ratio=area/(W*H) if W*H>0 else float("inf"))


def draw_bbox(img, bbox, label=""):
    out = img.copy()
    x0,y0,x1,y1 = bbox
    cv2.rectangle(out,(x0,y0),(x1,y1),(0,255,0),2)
    if label:
        cv2.putText(out,label,(x0,max(0,y0-10)),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)
    return out


def main():
    if len(sys.argv)<2:
        print("Usage: python pose_limit_test.py <image_path> [--show]")
        sys.exit(1)
    image_path = sys.argv[1]
    show_flag = ("--show" in sys.argv)

    img = cv2.imread(image_path)
    if img is None or img.size==0:
        sys.exit(f"Could not read {image_path}")

    H0,W0 = img.shape[:2]
    pose = mp.solutions.pose.Pose(static_image_mode=True,
                                  min_detection_confidence=DET_MIN_CONF)

    # Detect original
    bbox0 = detect_pose_bbox(img, pose)
    if bbox0 is None:
        sys.exit("No pose in original image")

    m0 = metrics_from_bbox(bbox0,W0,H0)
    print(f"Original {W0}x{H0}")
    print(f" WIDTH: {m0['width_px']} | HEIGHT: {m0['height_px']} | AREA: {m0['area_px2']} | RATIO: {m0['area_ratio']:.8f}")

    # Shrink until fail
    s=1.0
    last={"scale":s,"bbox":bbox0,"img":img.copy(),"metrics":m0}
    while s>MIN_SCALE:
        s*=SHRINK_FACTOR_STEP
        test=letterbox_scale(img,s,s)
        bbox=detect_pose_bbox(test,pose)
        if bbox is None: break
        last={"scale":s,"bbox":bbox,"img":test,"metrics":metrics_from_bbox(bbox,test.shape[1],test.shape[0])}

    ms=last["metrics"]
    print("\nSmallest still-detected pose:")
    print(f" SCALE: {last['scale']:.4f} | WIDTH: {ms['width_px']} | HEIGHT: {ms['height_px']} | AREA: {ms['area_px2']} | RATIO: {ms['area_ratio']:.8f}")
    if show_flag:
        vis=draw_bbox(last["img"],last["bbox"],f"scale={last['scale']:.3f}")
        cv2.imshow("Smallest detected",vis); cv2.waitKey(0)

    # Expand gradually
    print("\nCanvas expansion test (factor {:.2f} each step, stop after {} fails):".format(EXPAND_STEP,STOP_AFTER_FAILS))
    base=last["img"]; base_bbox=last["bbox"]
    factor=1.0
    fail_count=0
    step=0
    while fail_count<STOP_AFTER_FAILS:
        factor*=EXPAND_STEP; step+=1
        big=expand_canvas_keep_content(base,factor,bg=255)
        bbox=detect_pose_bbox(big,pose)
        if bbox is not None:
            fail_count=0
            m=metrics_from_bbox(bbox,big.shape[1],big.shape[0])
            print(f" step {step}: factor={factor:.3f} | detected=True | ratio={m['area_ratio']:.10f}")
            if show_flag:
                vis=draw_bbox(big,bbox,f"x{factor:.2f}")
                cv2.imshow(f"Expand {factor:.2f}",vis); cv2.waitKey(0)
        else:
            fail_count+=1
            print(f" step {step}: factor={factor:.3f} | detected=False")
            if show_flag:
                cv2.imshow(f"Expand {factor:.2f}",big); cv2.waitKey(0)

    print("\nStopped after {} consecutive failures.".format(STOP_AFTER_FAILS))
    if show_flag: cv2.destroyAllWindows()


if __name__=="__main__":
    main()
