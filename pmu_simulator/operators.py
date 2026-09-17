"""Opérateurs numériques immuables, mis en cache par leurs seuls paramètres."""
from functools import lru_cache
import numpy as np


@lru_cache(maxsize=32)
def phasor_operator(fs: float, f0: float, n: int) -> tuple[np.ndarray, np.ndarray]:
    tau = (np.arange(n) - (n - 1) / 2) / fs
    s = np.sqrt(2) * np.column_stack((np.cos(2*np.pi*f0*tau), -np.sin(2*np.pi*f0*tau)))
    return s, np.linalg.pinv(s)


@lru_cache(maxsize=32)
def frequency_operator(m: int) -> tuple[np.ndarray, np.ndarray]:
    u = (np.arange(m) - (m - 1)) / (m - 1)
    b = np.column_stack((np.ones(m), u, u*u))
    return b, np.linalg.pinv(b)


@lru_cache(maxsize=1)
def symmetrical_operator() -> np.ndarray:
    alpha = np.exp(2j*np.pi/3)
    return np.array([[1, 1, 1], [1, alpha, alpha**2], [1, alpha**2, alpha]], complex) / 3
