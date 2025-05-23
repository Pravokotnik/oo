#!/usr/bin/env python3
import os
import json
import gzip
import base64
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
import threading
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class HoughDatabase:
    def __init__(self, json_folder="json_minimal_edges_base64"):
        self.json_folder = json_folder
        self.hough_data = {}    # key: image key, value: numpy 2D array (uint8)
        self.metadata = {}      # key: image key, value: dict (e.g. path, filename)
        self.flattened = None   # numpy 2D array: each row is flattened hough
        self.keys = []
        self.embeddings = None
        self.pca = None
        self.loading_complete = threading.Event()
        threading.Thread(target=self.load_all_data, daemon=True).start()

    def decode_base64_gzip(self, encoded):
        b64data = encoded['data']
        compressed = base64.b64decode(b64data)
        decompressed = gzip.decompress(compressed)
        arr = np.frombuffer(decompressed, dtype=np.uint8)
        shape = encoded['shape']
        return arr.reshape(shape)

    def load_all_data(self):
        logger.info(f"Loading JSON files from folder: {self.json_folder}")
        if not os.path.exists(self.json_folder):
            logger.error(f"Folder '{self.json_folder}' does not exist!")
            return
        total_images = 0
        for filename in os.listdir(self.json_folder):
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(self.json_folder, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                count = 0
                for key, val in data.items():
                    if 'hough_sinusoids' in val:
                        try:
                            hough_arr = self.decode_base64_gzip(val['hough_sinusoids'])
                            self.hough_data[key] = hough_arr
                            self.metadata[key] = {
                                'path': val.get('path', ''),
                                'file': filename
                            }
                            count += 1
                        except Exception as e:
                            logger.warning(f"Error decoding {key}: {e}")
                total_images += count
                logger.info(f"Loaded {count} images from {filename}")
            except Exception as e:
                logger.error(f"Failed to load {filename}: {e}")

        self.keys = list(self.hough_data.keys())
        if total_images == 0:
            logger.warning("No images loaded. Ensure JSON files have correct data.")
            self.loading_complete.set()
            return

        # Precompute flattened arrays
        first_shape = next(iter(self.hough_data.values())).shape
        self.flattened = np.zeros((total_images, first_shape[0]*first_shape[1]), dtype=np.uint8)
        for i, key in enumerate(self.keys):
            self.flattened[i] = self.hough_data[key].flatten()

        # Create PCA embeddings for fast search (optional)
        logger.info("Computing PCA embeddings for faster similarity search...")
        self.pca = PCA(n_components=min(256, self.flattened.shape[1]))
        float_data = self.flattened.astype(np.float32)
        self.embeddings = self.pca.fit_transform(float_data)

        self.loading_complete.set()
        logger.info(f"Loaded total {total_images} images and ready for search.")

    def find_similar(self, query_array, top_k=10, use_embeddings=True):
        if not self.loading_complete.is_set():
            return []

        query_flat = query_array.flatten().astype(np.float32).reshape(1, -1)

        if use_embeddings and self.embeddings is not None and self.pca is not None:
            query_emb = self.pca.transform(query_flat)
            sims = cosine_similarity(query_emb, self.embeddings)[0]
        else:
            data_float = self.flattened.astype(np.float32)
            query_norm = np.linalg.norm(query_flat)
            data_norms = np.linalg.norm(data_float, axis=1)
            if query_norm == 0:
                sims = np.zeros(len(self.keys))
            else:
                dots = np.dot(data_float, query_flat.T).flatten()
                sims = dots / (data_norms * query_norm + 1e-8)

        top_indices = np.argsort(sims)[-top_k:][::-1]
        results = []
        for idx in top_indices:
            key = self.keys[idx]
            results.append({
                'key': key,
                'similarity': float(sims[idx]),
                'path': self.metadata[key]['path'],
                'file': self.metadata[key]['file']
            })
        return results


db = HoughDatabase()

@app.route('/status')
def status():
    return jsonify({
        'loading_complete': db.loading_complete.is_set(),
        'total_images': len(db.keys),
        'has_embeddings': db.embeddings is not None
    })

@app.route('/search', methods=['POST'])
def search():
    if not db.loading_complete.is_set():
        return jsonify({'error': 'Database still loading'}), 503
    data = request.json
    if 'hough_data' not in data:
        return jsonify({'error': 'Missing hough_data'}), 400
    top_k = data.get('top_k', 10)
    use_embeddings = data.get('use_embeddings', True)

    query_data = np.array(data['hough_data'], dtype=np.uint8)
    start = time.time()
    results = db.find_similar(query_data, top_k=top_k, use_embeddings=use_embeddings)
    search_time = time.time() - start
    return jsonify({
        'results': results,
        'search_time_ms': round(search_time * 1000, 2),
        'total_images_searched': len(db.keys),
        'method': 'embeddings' if use_embeddings else 'vectorized'
    })

if __name__ == '__main__':
    print("Starting Hough Similarity Search Server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, threaded=True)
