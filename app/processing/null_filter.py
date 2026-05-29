import numpy as np

NULL_VALUE = -9999.0


def remove_nulls(x, z):
    mask = z != NULL_VALUE
    return x[mask], z[mask]