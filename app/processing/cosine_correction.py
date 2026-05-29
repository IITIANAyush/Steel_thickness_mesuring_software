import numpy as np


def cosine_correct(thickness, slope_angle_rad):
    return thickness * np.cos(slope_angle_rad)