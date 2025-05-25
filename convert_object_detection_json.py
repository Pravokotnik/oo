import os
import pickle
import json

# Config
DETAILS_PICKLE = './details_results.pkl'
RATIOS_PICKLE = './ratio_results.pkl'
OUTPUT_FOLDER = './detected_objects/'

def normalize_entry(details_entry, ratio_entry, path):
    return {
        "path": "wikiart/" + path.replace("\\", "/"),
        "details": details_entry,
        "ratio": ratio_entry
    }

def save_style_file(style, entries):
    out_path = os.path.join(OUTPUT_FOLDER, f"{style}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, separators=(',', ':'), ensure_ascii=False)
    print(f"✅ Saved {style}.json with {len(entries)} items")

def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    with open(DETAILS_PICKLE, 'rb') as f:
        details = pickle.load(f)

    with open(RATIOS_PICKLE, 'rb') as f:
        ratios = pickle.load(f)

    grouped = {}

    for path, detail in details.items():
        normalized_path = path.replace("\\", "/")
        style = normalized_path.split('/')[0]
        ratio = ratios.get(path, None)

        if ratio is None:
            print(f"⚠️ Missing ratio for {path}, skipping")
            continue

        entry = normalize_entry(detail, ratio, path)
        grouped.setdefault(style, {})[path] = entry

    for style, entries in grouped.items():
        save_style_file(style, entries)

if __name__ == '__main__':
    main()
