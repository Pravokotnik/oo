import os
import pickle
import json

# Input paths
PICKLE_DIR = "./pickles"
DETAILS_PICKLE = os.path.join(PICKLE_DIR, "details_results.pkl")
RATIO_PICKLE = os.path.join(PICKLE_DIR, "ratio_results.pkl")

# Output paths
DETAILS_JSON_DIR = "./details"
RATIO_JSON_DIR = "./ratio"

# Ensure output directories exist
os.makedirs(DETAILS_JSON_DIR, exist_ok=True)
os.makedirs(RATIO_JSON_DIR, exist_ok=True)

def normalize_path(path):
    # Fix backslashes to forward slashes and ensure path starts with 'wikiart/'
    path = path.replace("\\", "/")
    if not path.startswith("wikiart/"):
        path = "wikiart/" + path
    return path

def convert_details():
    with open(DETAILS_PICKLE, "rb") as f:
        details_data = pickle.load(f)

    grouped_by_style = {}
    for img_path, metadata in details_data.items():
        norm_path = normalize_path(img_path)
        # Extract style folder from path: wikiart/StyleName/imagename.jpg
        style = norm_path.split("/")[1] if "/" in norm_path else "Unknown"
        grouped_by_style.setdefault(style, {})[norm_path] = {
            "path": norm_path,
            **metadata
        }

    for style, images in grouped_by_style.items():
        json_path = os.path.join(DETAILS_JSON_DIR, f"{style}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(images, f, ensure_ascii=False, separators=(",", ":"))
        print(f"✅ Saved details JSON for style: {style} ({len(images)} images)")

def convert_ratios():
    with open(RATIO_PICKLE, "rb") as f:
        ratio_data = pickle.load(f)

    for class_name, buckets in ratio_data.items():
        converted = {}
        for bucket, paths in buckets.items():
            # bucket might be a string, convert to int
            converted[int(bucket)] = [normalize_path(p) for p in paths]

        json_path = os.path.join(RATIO_JSON_DIR, f"{class_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({class_name: converted}, f, ensure_ascii=False, separators=(",", ":"))
        print(f"✅ Saved ratio JSON for class: {class_name} ({sum(len(v) for v in converted.values())} images)")

def main():
    convert_details()
    convert_ratios()

if __name__ == "__main__":
    main()
