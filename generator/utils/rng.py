import numpy as np


def create_rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)
