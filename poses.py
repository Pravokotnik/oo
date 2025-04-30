import cv2
import pickle
import numpy as np
import umap
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import mediapipe as mp
import os

# Initialize MediaPipe
mp_pose = mp.solutions.pose

# Constants
WINDOW_NAME = "Pose Explorer"
UMAP_CACHE_FILE = "./pickles/umap_cache.pkl"
POSE_RESULTS_FILE = "./pickles/pose_results.pkl"

# Display parameters
DISPLAY_WIDTH = 1200
DISPLAY_HEIGHT = 900
POSE_REFERENCE_SIZE = 400  # Consistent visual size for all poses

def ensure_pickle_dir():
    os.makedirs(os.path.dirname(UMAP_CACHE_FILE), exist_ok=True)

def load_results(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)

def save_umap_cache(embedding, keys, valid_poses):
    ensure_pickle_dir()
    with open(UMAP_CACHE_FILE, 'wb') as f:
        pickle.dump({
            'embedding': embedding,
            'keys': keys,
            'valid_poses': valid_poses
        }, f)

def load_umap_cache():
    if not os.path.exists(UMAP_CACHE_FILE):
        return None
    with open(UMAP_CACHE_FILE, 'rb') as f:
        return pickle.load(f)
    
def rotate_vector(v, degrees):
    """Rotate a 2D vector by specified degrees"""
    theta = np.radians(degrees)
    c, s = np.cos(theta), np.sin(theta)
    return np.array([
        c*v[0] - s*v[1],
        s*v[0] + c*v[1]
    ])

def normalize_pose(landmarks):
    """Standardize pose size and position for both display and UMAP"""
    lm_coords = np.array([(lm['x'], lm['y']) for lm in landmarks])
    
    # Center around torso midpoint
    torso_midpoint = np.mean([
        lm_coords[11],  # Left shoulder
        lm_coords[12],  # Right shoulder
        lm_coords[23],  # Left hip
        lm_coords[24]   # Right hip
    ], axis=0)
    
    centered = lm_coords - torso_midpoint
    
    # Normalize based on torso size (same as display scaling)
    torso_size = np.linalg.norm(lm_coords[11] - lm_coords[24])
    if torso_size > 0:
        centered /= torso_size
    
    return centered.flatten()  # Flatten for UMAP

def create_umap_plot(embedding, current_idx, direction=None):
    """Create UMAP visualization plot"""
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.scatter(embedding[:, 0], embedding[:, 1], s=5, alpha=0.5)
    
    # Highlight current point
    ax.scatter(embedding[current_idx, 0], embedding[current_idx, 1], 
               s=100, c='red', edgecolors='black')
    
    # Draw direction arrow if provided
    if direction is not None:
        ax.arrow(embedding[current_idx, 0], embedding[current_idx, 1],
                 direction[0], direction[1], 
                 head_width=0.1, head_length=0.15, fc='blue', ec='blue')
    
    ax.set_title("Pose Similarity Space (UMAP)")
    plt.tight_layout()
    
    # Convert plot to OpenCV image
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    buf = canvas.buffer_rgba()
    plot_img = np.asarray(buf)
    plt.close(fig)
    
    return cv2.cvtColor(plot_img, cv2.COLOR_RGBA2BGR)

def prepare_umap_data(pose_results):
    cache = load_umap_cache()
    if cache:
        print("Loaded UMAP results from cache")
        return cache['embedding'], cache['keys'], cache['valid_poses']
    
    print("Computing UMAP embedding...")
    valid_poses = {k: v for k, v in pose_results.items() if v['landmarks']}
    
    # Use same normalization as display
    features = [normalize_pose(data['landmarks']) for data in valid_poses.values()]
    keys = list(valid_poses.keys())
    
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)
    
    reducer = umap.UMAP(n_components=2, random_state=42)
    embedding = reducer.fit_transform(scaled_features)
    
    save_umap_cache(embedding, np.array(keys), valid_poses)
    return embedding, np.array(keys), valid_poses

def prepare_display(image, landmarks):
    """Prepare image with pose perfectly centered in window"""
    h, w = image.shape[:2]
    
    # Get pose bounding box in original image coordinates
    lm_coords = np.array([(lm['x']*w, lm['y']*h) for lm in landmarks])
    min_x, min_y = lm_coords.min(axis=0)
    max_x, max_y = lm_coords.max(axis=0)
    
    # Calculate pose center and dimensions
    pose_center_x = (min_x + max_x) / 2
    pose_center_y = (min_y + max_y) / 2
    pose_width = max_x - min_x
    pose_height = max_y - min_y
    
    # Calculate scale to fit pose to reference size
    scale = POSE_REFERENCE_SIZE / max(pose_height, pose_width)
    
    # Calculate new image dimensions after scaling
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    # Scale the image
    scaled_img = cv2.resize(image, (new_w, new_h))
    
    # Calculate where pose center should be in display
    target_center_x = DISPLAY_WIDTH // 2
    target_center_y = DISPLAY_HEIGHT // 2
    
    # Calculate offsets to position scaled image
    scaled_pose_center_x = pose_center_x * scale
    scaled_pose_center_y = pose_center_y * scale
    
    x_offset = int(target_center_x - scaled_pose_center_x)
    y_offset = int(target_center_y - scaled_pose_center_y)
    
    # Create display canvas
    display_img = np.zeros((DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), dtype=np.uint8)
    
    # Calculate copy region (handle edge cases)
    img_start_x = max(0, -x_offset)
    img_start_y = max(0, -y_offset)
    img_end_x = min(new_w, DISPLAY_WIDTH - x_offset)
    img_end_y = min(new_h, DISPLAY_HEIGHT - y_offset)
    
    disp_start_x = max(0, x_offset)
    disp_start_y = max(0, y_offset)
    disp_end_x = min(DISPLAY_WIDTH, x_offset + new_w)
    disp_end_y = min(DISPLAY_HEIGHT, y_offset + new_h)
    
    # Place image on canvas
    display_img[disp_start_y:disp_end_y, disp_start_x:disp_end_x] = \
        scaled_img[img_start_y:img_end_y, img_start_x:img_end_x]
    
    # Adjust landmarks to display coordinates
    adj_landmarks = []
    for lm in landmarks:
        adj_landmarks.append({
            'x': (lm['x'] * w * scale + x_offset) / DISPLAY_WIDTH,
            'y': (lm['y'] * h * scale + y_offset) / DISPLAY_HEIGHT,
            'z': lm['z'],
            'visibility': lm['visibility']
        })
    
    return display_img, adj_landmarks

def draw_pose(image, landmarks):
    """Draw perfectly aligned pose"""
    h, w = image.shape[:2]
    overlay = image.copy()
    
    for connection in mp_pose.POSE_CONNECTIONS:
        start_idx, end_idx = connection
        pt1 = (int(landmarks[start_idx]['x']*w), int(landmarks[start_idx]['y']*h))
        pt2 = (int(landmarks[end_idx]['x']*w), int(landmarks[end_idx]['y']*h))
        cv2.line(overlay, pt1, pt2, (0,255,0), 2)
    
    for lm in landmarks:
        pt = (int(lm['x']*w), int(lm['y']*h))
        cv2.circle(overlay, pt, 4, (0,0,255), -1)
    
    return cv2.addWeighted(image, 0.7, overlay, 0.3, 0)

def find_next_pose(embedding, current_idx, direction, step_size=0.5):
    """Find next pose in the specified direction"""
    target_point = embedding[current_idx] + direction * step_size
    distances = np.linalg.norm(embedding - target_point, axis=1)
    distances[current_idx] = np.inf
    return np.argmin(distances)

def display_pose_sequence():
    """Display pose sequence with fixed sizes"""
    pose_results = load_results(POSE_RESULTS_FILE)
    embedding, keys, valid_poses = prepare_umap_data(pose_results)
    current_idx = np.random.choice(len(keys))
    direction = np.array([1.0, 0.0])
    
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, DISPLAY_WIDTH, DISPLAY_HEIGHT)
    cv2.namedWindow("UMAP Projection", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("UMAP Projection", 800, 600)
    
    while True:
        current_key = keys[current_idx]
        current_data = valid_poses[current_key]
        img = cv2.imread(current_data['img_path'])
        
        if img is None:
            print(f"Could not load image: {current_data['img_path']}")
            current_idx = np.random.choice(len(keys))
            continue
        
        display_img, adj_landmarks = prepare_display(img, current_data['landmarks'])
        result_img = draw_pose(display_img, adj_landmarks)
        
        umap_plot = create_umap_plot(embedding, current_idx, direction)
        
        cv2.imshow(WINDOW_NAME, result_img)
        cv2.imshow("UMAP Projection", umap_plot)
        
        key = cv2.waitKey(0) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('n'):
            current_idx = find_next_pose(embedding, current_idx, direction)
        elif key == ord('r'):
            current_idx = np.random.choice(len(keys))
        elif key == ord('a'):  # Rotate direction left
            direction = rotate_vector(direction, 15)  # +15 degrees
        elif key == ord('d'):  # Rotate direction right
            direction = rotate_vector(direction, -15)  # -15 degrees
        elif key == ord('w'):
            direction *= 1.2
        elif key == ord('s'):
            direction *= 0.8
    
    cv2.destroyAllWindows()

def main():
    ensure_pickle_dir()
    print("\n🎨 Pose Sequence Explorer")
    print("Controls:")
    print("  'n' - Next pose in current direction")
    print("  'a' - Rotate direction left")
    print("  'd' - Rotate direction right")
    print("  'w' - Increase step size")
    print("  's' - Decrease step size")
    print("  'r' - Random new image")
    print("  'q' - Quit\n")
    display_pose_sequence()

if __name__ == "__main__":
    main()