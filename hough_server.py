#!/usr/bin/env python3
import os
import json
import gzip
import base64
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from annoy import AnnoyIndex
import threading
import logging
import time
import pickle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class HoughDatabase:
    def __init__(self,
                 json_folder="json_minimal_edges_base64",
                 ann_file="pickles/hough.ann",
                 meta_file="pickles/hough_meta.pkl",
                 n_trees=10):
        self.json_folder = json_folder
        self.ann_file = ann_file
        self.meta_file = meta_file
        self.n_trees = n_trees
        self.keys = []
        self.metadata = {}
        self.index = None
        self.loading_complete = threading.Event()
        threading.Thread(target=self.load_all_data, daemon=True).start()

    def decode_base64_gzip(self, encoded):
        data_b64 = encoded['data']
        compressed = base64.b64decode(data_b64)
        decompressed = gzip.decompress(compressed)
        arr = np.frombuffer(decompressed, dtype=np.uint8)
        return arr.reshape(encoded['shape'])

    def load_all_data(self):
        # Try loading precomputed files
        if os.path.exists(self.ann_file) and os.path.exists(self.meta_file):
            logger.info("Loading precomputed Annoy index and metadata...")
            with open(self.meta_file, 'rb') as f:
                meta = pickle.load(f)
            self.keys = meta['keys']
            self.metadata = meta['metadata']
            dim = meta['dim']
            self.index = AnnoyIndex(dim, metric='angular')
            self.index.load(self.ann_file)
            logger.info(f"Loaded {len(self.keys)} items from precomputed index.")
            self.loading_complete.set()
            return

        # Fallback: build from JSON
        logger.info(f"Precomputed files missing. Building index from JSON in '{self.json_folder}'...")
        if not os.path.exists(self.json_folder):
            logger.error(f"JSON folder '{self.json_folder}' not found.")
            self.loading_complete.set()
            return

        hough_vectors = []
        for filename in sorted(os.listdir(self.json_folder)):
            if not filename.endswith('.json'):
                continue
            path = os.path.join(self.json_folder, filename)
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                for key, val in data.items():
                    if 'hough_sinusoids' in val:
                        arr = self.decode_base64_gzip(val['hough_sinusoids'])
                        hough_vectors.append(arr.flatten().astype(np.float32))
                        self.keys.append(key)
                        self.metadata[key] = {'path': val.get('path',''), 'file': filename}
            except Exception as e:
                logger.warning(f"Skipping {filename}: {e}")

        if not hough_vectors:
            logger.error("No Hough data found in JSON files.")
            self.loading_complete.set()
            return

        # Build the Annoy index
        stacked = np.vstack(hough_vectors)
        dim = stacked.shape[1]
        self.index = AnnoyIndex(dim, metric='angular')
        for i, vec in enumerate(stacked):
            self.index.add_item(i, vec)
        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.ann_file), exist_ok=True)
        self.index.build(self.n_trees)
        self.index.save(self.ann_file)

        # Save metadata for future loads
        meta = {'keys': self.keys, 'metadata': self.metadata, 'dim': dim}
        with open(self.meta_file, 'wb') as f:
            pickle.dump(meta, f)
        logger.info(f"Built and saved index ({len(self.keys)} items, dim={dim}) to '{self.ann_file}' and metadata to '{self.meta_file}'")

        self.loading_complete.set()

    def find_similar(self, query_array, top_k=10):
        if not self.loading_complete.is_set():
            return []
        q = query_array.flatten().astype(np.float32)
        idxs, dists = self.index.get_nns_by_vector(q, top_k, include_distances=True)
        results = []
        for idx, dist in zip(idxs, dists):
            key = self.keys[idx]
            results.append({'key': key, 'distance': float(dist), 'path': self.metadata[key]['path'], 'file': self.metadata[key]['file']})
        return results

# Instantiate database
HDB = HoughDatabase()

@app.route('/status')
def status():
    return jsonify({'loading_complete': HDB.loading_complete.is_set(), 'total_images': len(HDB.keys)})

@app.route('/search', methods=['POST'])
def search():
    if not HDB.loading_complete.is_set():
        return jsonify({'error': 'Database still loading'}), 503
    data = request.get_json()
    if 'hough_data' not in data:
        return jsonify({'error': 'Missing hough_data'}), 400
    query = np.array(data['hough_data'], dtype=np.uint8)
    top_k = data.get('top_k', 10)
    start = time.time()
    results = HDB.find_similar(query, top_k=top_k)
    elapsed = (time.time() - start) * 1000
    return jsonify({'results': results, 'search_time_ms': round(elapsed, 2)})

if __name__ == '__main__':
    print("Starting Hough Similarity Search Server with precomputed Annoy index on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, threaded=True)
