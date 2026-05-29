import numpy as np


def compute_statistics(thickness_array):

    return {
        'min': float(np.min(thickness_array)),
        'max': float(np.max(thickness_array)),
        'mean': float(np.mean(thickness_array)),
        'std': float(np.std(thickness_array))
    }