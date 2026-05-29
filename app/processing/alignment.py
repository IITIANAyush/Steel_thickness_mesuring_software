import numpy as np
from scipy.interpolate import interp1d


def align_profiles(
    x_top,
    z_top,
    x_bottom,
    z_bottom,
    n_points=1024
):

    x_min = max(x_top.min(), x_bottom.min())
    x_max = min(x_top.max(), x_bottom.max())

    x_common = np.linspace(x_min, x_max, n_points)

    f_top = interp1d(
        x_top,
        z_top,
        kind='linear',
        fill_value='extrapolate'
    )

    f_bottom = interp1d(
        x_bottom,
        z_bottom,
        kind='linear',
        fill_value='extrapolate'
    )

    z_top_interp = f_top(x_common)
    z_bottom_interp = f_bottom(x_common)

    return x_common, z_top_interp, z_bottom_interp