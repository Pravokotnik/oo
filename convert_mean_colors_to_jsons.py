import os
import pickle
import json

# Config
PICKLE_FILE = './pickles/mean_colors.pkl'
OUTPUT_FOLDER = './mean_colors/'

def normalize_entry(hsv, path):
    h, s, v = hsv
    return {
        "h": int(h),
        "s": round(s / 255.0, 3),
        "v": round(v / 255.0, 3),
        "path": "wikiart/" + path.replace("\\", "/")
    }

def save_style_file(style, entries):
    out_path = os.path.join(OUTPUT_FOLDER, f"{style}.json")
    converted = {
        path: normalize_entry(entry["hsv"], path)
        for path, entry in entries.items()
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(converted, f, separators=(',', ':'), ensure_ascii=False)
    print(f"✅ Saved {style}.json with {len(converted)} items")

def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    with open(PICKLE_FILE, 'rb') as f:
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

    for style, entries in grouped.items():
        print(f"📁 Processing {style} with {len(entries)} entries")
        save_style_file(style, entries)

if __name__ == '__main__':
    main()
