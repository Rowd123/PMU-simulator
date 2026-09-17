"""Bruit gaussien indépendant par phase et échantillon."""
import numpy as np


def gaussian_noise(count: int, variances: tuple[float, float, float], rng: np.random.Generator) -> np.ndarray:
    return rng.normal(size=(count, 3)) * np.sqrt(np.asarray(variances))[None, :]
