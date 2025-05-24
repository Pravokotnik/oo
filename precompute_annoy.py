#!/usr/bin/env python3
import os
import json
import gzip
import base64
import numpy as np
from annoy import AnnoyIndex
import pickle

def decode_base64_gzip(encoded):
    b64data    = encoded['data']
    compressed = base64.b64decode(b64data)
    decompressed = gzip.decompress(compressed)
    arr = np.frombuffer(decompressed, dtype=np.uint8)
    shape = encoded['shape']
    return arr.reshape(shape)

def load_hough_data(json_folder):
    keys = []
    hough_list = []
    metadata = {}

    for filename in sorted(os.listdir(json_folder)):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(json_folder, filename)
        with open(filepath, 'r') as f:
            data = json.load(f)
        for key, val in data.items():
            if 'hough_sinusoids' in val:
                arr = decode_base64_gzip(val['hough_sinusoids'])
                hough_list.append(arr.flatten().astype(np.float32))
                keys.append(key)
                metadata[key] = {
                    'path': val.get('path', ''),
                    'file': filename
                }

    flattened = np.vstack(hough_list)
    return keys, flattened, metadata

def build_and_save_index(flattened, keys, metadata,
                         output_index='pickles/hough.ann',
                         output_meta='pickles/hough_meta.pkl',
                         n_trees=10):
    # ensure output dir exists
    os.makedirs(os.path.dirname(output_index), exist_ok=True)

    dim = flattened.shape[1]
    index = AnnoyIndex(dim, metric='angular')
    for i, vec in enumerate(flattened):
        index.add_item(i, vec)
    index.build(n_trees)
    index.save(output_index)

    # save metadata, keys and dim
    meta = {
        'keys':     keys,
        'metadata': metadata,
        'dim':      dim
    }
    with open(output_meta, 'wb') as f:
        pickle.dump(meta, f)

    print(f"Built and saved Annoy index to {output_index}")
    print(f"Saved metadata (with dim={dim}) to {output_meta}")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Precompute Annoy index for Hough data')
    parser.add_argument('--json-folder', default='json_minimal_edges_base64',
                        help='Folder containing JSON files')
    parser.add_argument('--index-out', default='pickles/hough.ann',
                        help='Output Annoy index file (in pickles/)')
    parser.add_argument('--meta-out', default='pickles/hough_meta.pkl',
                        help='Output metadata pickle (in pickles/)')
    parser.add_argument('--trees', type=int, default=10,
                        help='Number of trees for Annoy')
    args = parser.parse_args()

    keys, flattened, metadata = load_hough_data(args.json_folder)
    build_and_save_index(flattened, keys, metadata,
                         output_index=args.index_out,
                         output_meta=args.meta_out,
                         n_trees=args.trees)
