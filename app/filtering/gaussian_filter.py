from scipy.ndimage import gaussian_filter1d


def apply_gaussian_filter(signal, sigma=2.0):
    return gaussian_filter1d(signal, sigma=sigma)