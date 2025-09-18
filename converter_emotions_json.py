import os
import pickle
import json

PICKLE_FILES = [
    './pickles/emotion_cache.pkl',
    './pickles/emotion_cache_filtered.pkl'
]
OUTPUT_FOLDER = './emotion_json/'

def normalize_path(path):
    path = path.replace("\\", "/")
    if not path.startswith("wikiart/"):
        path = "wikiart/" + path
    return path

def save_style_file(style, entries, suffix):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    out_path = os.path.join(OUTPUT_FOLDER, f"{style}_{suffix}.json")
    converted = {}
    for original_path, data in entries.items():
        norm_path = normalize_path(original_path)
        converted[norm_path] = data
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(converted, f, separators=(',', ':'), ensure_ascii=False)
    print(f"✅ Saved {out_path} with {len(converted)} items")

def process_pickle(pickle_path):
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f)

    grouped = {}
    for path, val in data.items():
        normalized_path = path.replace("\\", "/")
        try:
            style = normalized_path.split('/')[0]
        except IndexError:
            print(f"Skipping malformed path: {path}")
            continue
        grouped.setdefault(style, {})[path] = val

    suffix = os.path.splitext(os.path.basename(pickle_path))[0]
    for style, entries in grouped.items():
        print(f"📁 Processing {style} with {len(entries)} entries from {pickle_path}")
        save_style_file(style, entries, suffix)

def main():
    for pkl in PICKLE_FILES:
        process_pickle(pkl)

if __name__ == '__main__':
    main()
