from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
import cv2
import numpy as np
import pickle
import base64
from pathlib import Path

# Constants from poses_viewer.py
POSE_RESULTS_FILE = "./pickles/pose_results.pkl"
UMAP_CACHE_FILE = "./pickles/umap_cache.pkl"
IMAGE_DIR = "./wikiart/"  # Base directory for images

app = Flask(__name__, static_folder='.')
CORS(app)

def load_results(filename):
    """Load results from pickle file"""
    with open(filename, 'rb') as f:
        return pickle.load(f)
        
def load_umap_cache():
    """Load UMAP embedding data from cache"""
    if not os.path.exists(UMAP_CACHE_FILE):
        return None
    with open(UMAP_CACHE_FILE, 'rb') as f:
        return pickle.load(f)

@app.route('/api/poses')
def get_poses():
    """Return pose data for all images"""
    if not os.path.exists(POSE_RESULTS_FILE):
        return jsonify({"error": "Pose data not found"}), 404
    
    pose_results = load_results(POSE_RESULTS_FILE)
    
    # Filter for successful pose detections and convert to serializable format
    valid_poses = {}
    for key, data in pose_results.items():
        if data.get('landmarks'):
            valid_poses[key] = {
                'img_path': data['img_path'],
                'landmarks': [
                    {
                        'x': lm['x'], 
                        'y': lm['y'], 
                        'z': lm['z'], 
                        'visibility': float(lm['visibility'])
                    } for lm in data['landmarks']
                ]
            }
    
    return jsonify(valid_poses)

@app.route('/api/umap')
def get_umap():
    """Return UMAP embedding data"""
    cache_data = load_umap_cache()
    if not cache_data:
        return jsonify({"error": "UMAP data not found"}), 404
    
    # Convert numpy arrays to lists for JSON serialization
    return jsonify({
        'embedding': cache_data['embedding'].tolist(),
        'keys': cache_data['keys'].tolist()
    })

@app.route('/api/pose/<path:pose_id>')
def get_single_pose(pose_id):
    """Get data for a specific pose"""
    if not os.path.exists(POSE_RESULTS_FILE):
        return jsonify({"error": "Pose data not found"}), 404
    
    pose_results = load_results(POSE_RESULTS_FILE)
    
    # Normalize path for better matching
    pose_id = pose_id.replace('\\', '/')
    
    # First try exact match
    if pose_id in pose_results:
        pass # Use exact match
    else:
        # Try with IMAGE_DIR prefix
        alt_id = os.path.join(IMAGE_DIR, pose_id).replace('\\', '/')
        if alt_id in pose_results:
            pose_id = alt_id
        else:
            # Try more flexible matching
            pose_id_norm = pose_id.lower()
            for key in pose_results.keys():
                key_norm = key.lower().replace('\\', '/')
                if key_norm.endswith(pose_id_norm) or os.path.basename(key_norm) == os.path.basename(pose_id_norm):
                    pose_id = key
                    break
    
    if pose_id in pose_results and pose_results[pose_id].get('landmarks'):
        pose_data = pose_results[pose_id]
        return jsonify({
            'img_path': pose_data['img_path'],
            'landmarks': pose_data['landmarks']
        })
    else:
        return jsonify({"error": "Pose not found"}), 404

@app.route('/api/pose-image/<path:pose_id>')
def get_pose_image(pose_id):
    """Return a rendered image of the pose with landmarks"""
    if not os.path.exists(POSE_RESULTS_FILE):
        print(f"ERROR: Pose results file not found: {POSE_RESULTS_FILE}")
        return jsonify({"error": "Pose data file not found"}), 404
    
    pose_results = load_results(POSE_RESULTS_FILE)
    
    # Debug info
    print(f"Looking for pose ID: {pose_id}")
    
    # Normalize path for better matching (convert backslashes to forward slashes)
    pose_id = pose_id.replace('\\', '/')
    
    # First try exact match
    if pose_id in pose_results:
        pose_data = pose_results[pose_id]
    else:
        # Try with IMAGE_DIR prefix
        alt_id = os.path.join(IMAGE_DIR, pose_id).replace('\\', '/')
        if alt_id in pose_results:
            pose_id = alt_id
            print(f"Found using alternative ID with IMAGE_DIR prefix: {pose_id}")
        else:
            # Try a more flexible matching approach - look for partial matches
            possible_matches = []
            pose_id_norm = pose_id.lower()  # Case-insensitive matching
            
            for key in pose_results.keys():
                key_norm = key.lower().replace('\\', '/')
                
                # Check if the key ends with our pose_id (file path ending)
                if key_norm.endswith(pose_id_norm):
                    possible_matches.append(key)
                # Also check if pose_id contains the filename from the key
                elif os.path.basename(key_norm) == os.path.basename(pose_id_norm):
                    possible_matches.append(key)
            
            # If we found exactly one match, use it
            if len(possible_matches) == 1:
                pose_id = possible_matches[0]
                print(f"Found using flexible matching: {pose_id}")
            # If multiple matches, try to find the best one
            elif len(possible_matches) > 1:
                # Prefer keys that contain more of the original pose_id path components
                path_parts = pose_id.split('/')
                best_match = None
                best_score = 0
                
                for match in possible_matches:
                    score = sum(1 for part in path_parts if part in match)
                    if score > best_score:
                        best_score = score
                        best_match = match
                
                if best_match:
                    pose_id = best_match
                    print(f"Found best match from multiple: {pose_id} (score: {best_score})")
                else:
                    # Fall back to first match
                    pose_id = possible_matches[0]
                    print(f"Found using first of multiple matches: {pose_id}")
    
    # Final check if we found a valid pose
    if pose_id not in pose_results or not pose_results[pose_id].get('landmarks'):
        print(f"ERROR: No valid pose found for: {pose_id}")
        return jsonify({"error": f"Pose not found: {pose_id}"}), 404
    
    pose_data = pose_results[pose_id]
    img_path = pose_data['img_path']
    
    print(f"Found pose, image path: {img_path}")
    
    try:
        # Check if the image exists at the specified path
        if not os.path.exists(img_path):
            print(f"ERROR: Image file not found at: {img_path}")
            
            # Try options to find the actual image file
            possible_paths = [
                img_path,  # Original path
                os.path.join(IMAGE_DIR, os.path.basename(img_path)),  # Just the filename in IMAGE_DIR
                os.path.join(IMAGE_DIR, pose_id)  # Use pose_id as relative path
            ]
            
            # Extract style and artist from pose_id if possible
            parts = pose_id.split('/')
            if len(parts) >= 2:
                style = parts[-2]
                # Try standard pattern: style/artist_title.jpg
                possible_paths.append(os.path.join(IMAGE_DIR, style, os.path.basename(img_path)))
            
            # Try all possible paths
            for path in possible_paths:
                if os.path.exists(path):
                    img_path = path
                    print(f"Found image at: {img_path}")
                    break
        
        # Still couldn't find the image
        if not os.path.exists(img_path):
            return jsonify({"error": f"Could not locate image file"}), 404
        
        # Read the image
        img = cv2.imread(img_path)
        if img is None:
            print(f"ERROR: Could not read image: {img_path}")
            return jsonify({"error": f"Could not read image: {img_path}"}), 404
        
        # Draw pose landmarks on the image
        h, w = img.shape[:2]
        for landmark in pose_data['landmarks']:
            x, y = int(landmark['x'] * w), int(landmark['y'] * h)
            if 0 <= x < w and 0 <= y < h:
                cv2.circle(img, (x, y), 5, (0, 255, 0), -1)
        
        # Convert image to base64 for transmission
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'image_data': f"data:image/jpeg;base64,{img_base64}"
        })
    except Exception as e:
        print(f"ERROR processing image: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error processing image: {str(e)}"}), 500

@app.route('/api/nearest-pose')
def get_nearest_pose():
    """Find nearest pose in UMAP space to given coordinates"""
    try:
        x = float(request.args.get('x', 0))
        y = float(request.args.get('y', 0))
        
        cache_data = load_umap_cache()
        if not cache_data:
            return jsonify({"error": "UMAP data not found"}), 404
        
        embedding = cache_data['embedding']
        keys = cache_data['keys']
        
        # Find closest point in embedding space
        query_point = np.array([x, y])
        distances = np.linalg.norm(embedding - query_point, axis=1)
        nearest_idx = np.argmin(distances)
        
        nearest_key = keys[nearest_idx]
        
        return jsonify({
            'pose_id': nearest_key,
            'embedding': embedding[nearest_idx].tolist()
        })
    except Exception as e:
        return jsonify({"error": f"Error finding nearest pose: {str(e)}"}), 500

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve image files from the wikiart directory"""
    return send_from_directory(IMAGE_DIR, filename)

@app.route('/')
def index():
    """Serve the main application page"""
    return send_from_directory('.', 'poses.html')

if __name__ == '__main__':
    print("Starting Poses API Server...")
    print(f"Pose data: {os.path.exists(POSE_RESULTS_FILE)}")
    print(f"UMAP data: {os.path.exists(UMAP_CACHE_FILE)}")
    app.run(debug=True, port=7000)