import cv2
import os
import pickle
from pathlib import Path
from tqdm import tqdm
import mediapipe as mp
import warnings

# 🔇 Silence warnings
warnings.filterwarnings("ignore")

# Constants
POSE_PICKLE_FILE = "./pickles/pose_results.pkl"
FOLDER_PATH = './wikiart/'  # Change to your image folder

def find_images_recursive(root_folder):
    """Recursively find all image files in directory"""
    image_files = []
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                image_files.append(os.path.join(dirpath, filename))
    return image_files

def process_images_for_poses(image_files, folder_path):
    """Process all images and return pose detection results"""
    pose_results = {}
    
    # Initialize MediaPipe Pose
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5)
    
    for img_path in tqdm(image_files, desc="Detecting Poses", unit="img"):
        try:
            img = cv2.imread(img_path)
            if img is None:
                continue
                
            # Convert to RGB and process
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb_img)
            
            rel_path = os.path.relpath(img_path, folder_path)
            
            if results.pose_landmarks:
                # Store normalized landmark coordinates (0-1 scale)
                landmarks = []
                for landmark in results.pose_landmarks.landmark:
                    landmarks.append({
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z,
                        'visibility': landmark.visibility
                    })
                
                pose_results[rel_path] = {
                    'landmarks': landmarks,
                    'img_path': img_path,
                    'img_shape': img.shape
                }
                
        except Exception as e:
            print(f"\n⚠️ Error in {img_path}: {str(e)[:50]}...")
    
    return pose_results

def save_results(data, filename):
    """Save results to pickle file"""
    with open(filename, 'wb') as f:
        pickle.dump(data, f)
    print(f"✅ Saved pose results to {filename}")

def load_results(filename):
    """Load results from pickle file"""
    with open(filename, 'rb') as f:
        return pickle.load(f)

def print_summary(pose_results):
    """Print detection summary"""
    print("\n📊 Pose Detection Summary:")
    print(f"Total images processed: {len(pose_results)}")
    print(f"Images with poses detected: {sum(1 for v in pose_results.values() if v['landmarks'])}")

def main():
    # Check for existing results
    if Path(POSE_PICKLE_FILE).exists():
        print(f"🔍 Found existing results file")
        pose_results = load_results(POSE_PICKLE_FILE)
    else:
        # Process images
        image_files = find_images_recursive(FOLDER_PATH)
        pose_results = process_images_for_poses(image_files, FOLDER_PATH)
        save_results(pose_results, POSE_PICKLE_FILE)
    
    # Output results
    print_summary(pose_results)
    
    # Example of accessing pose data
    print("\nExample pose data:")
    first_pose = next((v for v in pose_results.values() if v['landmarks']), None)
    if first_pose:
        print(f"Image path: {first_pose['img_path']}")
        print(f"Landmarks count: {len(first_pose['landmarks'])}")
        print(f"First landmark coordinates (normalized 0-1):")
        print(f"  X: {first_pose['landmarks'][0]['x']:.3f}")
        print(f"  Y: {first_pose['landmarks'][0]['y']:.3f}")
        print(f"  Z: {first_pose['landmarks'][0]['z']:.3f}")
        print(f"  Visibility: {first_pose['landmarks'][0]['visibility']:.3f}")

if __name__ == "__main__":
    main()