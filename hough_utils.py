import numpy as np
import cv2

def compute_derivatives(I, sigma):
    size = int(2 * np.ceil(3 * sigma) + 1)
    x = np.arange(-size // 2 + 1, size // 2 + 1)

    G = (1 / (np.sqrt(2 * np.pi) * sigma)) * np.exp(-x**2 / (2 * sigma**2))
    G /= np.sum(G)

    D = -(x / (np.sqrt(2 * np.pi) * sigma**3)) * np.exp(-x**2 / (2 * sigma**2))
    D /= np.sum(np.abs(D))

    G = G.reshape(1, -1)
    D = D.reshape(1, -1)

    def convolute(I, k):
        k = np.flip(k)
        return cv2.filter2D(I, -1, k, borderType=cv2.BORDER_REPLICATE)

    Ix = convolute(I, D)
    Iy = convolute(I, D.T)

    return Ix, Iy

def gradient_magnitude(I, sigma=1):
    Ix, Iy = compute_derivatives(I, sigma)
    Im = np.sqrt(Ix**2 + Iy**2)
    return Im, np.arctan2(Iy, Ix)

def findedges(I, theta, sigma=1):
    Im, _ = gradient_magnitude(I, sigma)
    Ie = np.where(Im >= theta, 1, 0).astype(np.uint8)
    return Ie

def hough_find_lines3(I, num_bins_rho, num_bins_theta, t):
    Ie = findedges(I, t)
    h, w = Ie.shape
    D = int(np.ceil(np.sqrt(h**2 + w**2)))

    ys, xs = np.nonzero(Ie)
    if len(xs) == 0:
        return np.zeros((num_bins_rho, num_bins_theta), dtype=np.uint32)

    theta_range = np.linspace(-np.pi/2, np.pi/2, num_bins_theta)
    cos_t = np.cos(theta_range)[None, :]  # shape (1, num_theta)
    sin_t = np.sin(theta_range)[None, :]  # shape (1, num_theta)

    xs = xs[:, None]  # shape (N,1)
    ys = ys[:, None]

    rho_vals = xs * cos_t + ys * sin_t  # shape (N, num_theta)
    rho_idx = np.round((rho_vals + D) / (2 * D) * (num_bins_rho - 1)).astype(np.int32)
    np.clip(rho_idx, 0, num_bins_rho - 1, out=rho_idx)

    A = np.zeros((num_bins_rho, num_bins_theta), dtype=np.uint32)

    theta_idx = np.arange(num_bins_theta)
    theta_idx = np.broadcast_to(theta_idx, rho_idx.shape)

    np.add.at(A, (rho_idx.ravel(), theta_idx.ravel()), 1)

    return A

def nonmaxima_suppression_box(accumulator):
    acc = np.copy(accumulator)
    h, w = acc.shape
    acc = np.pad(acc, 1, mode='constant', constant_values=0)

    # Vectorized non-max suppression
    for row in range(1, h+1):
        for col in range(1, w+1):
            neighborhood = acc[row-1:row+2, col-1:col+2]
            if acc[row, col] < np.max(neighborhood):
                acc[row, col] = 0
    return acc[1:h+1, 1:w+1]
