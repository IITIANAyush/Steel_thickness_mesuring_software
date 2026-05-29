from scipy.signal import medfilt


def apply_median_filter(signal, kernel_size=7):
    return medfilt(signal, kernel_size)