import os

folder = "json_minimal_edges_base64"

if not os.path.exists(folder):
    print(f"Folder '{folder}' does not exist.")
else:
    json_files = [f for f in os.listdir(folder) if f.endswith('.json')]
    print("Found JSON files:")
    for filename in sorted(json_files):
        print(f"- {filename}")
