import pickle
import json

# Convert ratio_results.pkl to JSON
with open('pickles/ratio_results.pkl', 'rb') as f:
    data = pickle.load(f)
with open('ratio_results.json', 'w') as f:
    json.dump(data, f)

# Convert details_results.pkl to JSON
with open('pickles/details_results.pkl', 'rb') as f:
    data = pickle.load(f)
with open('details_results.json', 'w') as f:
    json.dump(data, f)