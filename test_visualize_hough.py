import pickle

with open('hough_data_sample.pkl', 'rb') as f:
    data_dict = pickle.load(f)

import matplotlib.pyplot as plt

def visualize_hough_data(data):
    path = data['path']
    edges = data['edges']
    accumulator = data['accumulator']
    sinusoids_vis = data['sinusoids_vis']

    plt.figure(figsize=(15, 10))

    plt.suptitle(f"Visualization for: {path}", fontsize=16)

    plt.subplot(2, 2, 1)
    plt.title("Edges (Canny)")
    plt.imshow(edges, cmap='gray')
    plt.axis('off')

    plt.subplot(2, 2, 2)
    plt.title("Hough Accumulator")
    plt.imshow(accumulator, cmap='hot', aspect='auto')
    plt.colorbar()
    plt.axis('on')

    plt.subplot(2, 2, 3)
    plt.title("Sinusoidal Curves Visualization")
    plt.imshow(sinusoids_vis, cmap='gray', aspect='auto', origin='lower')
    plt.axis('on')

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()

for key in list(data_dict.keys())[:5]:  # visualize first 5 images
    print(f"Visualizing {key}")
    visualize_hough_data(data_dict[key])
