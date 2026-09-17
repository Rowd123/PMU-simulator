"""Estimateur LS glissant, vectorisé sur les trois phases."""
from collections import deque
import numpy as np
from .operators import phasor_operator


class PhasorEstimator:
    def __init__(self, fs: float, f0: float, window: int):
        self.fs, self.f0, self.window = fs, f0, window
        self.S, self.K = phasor_operator(fs, f0, window)
        self.buffer: deque[np.ndarray] = deque(maxlen=window)

    @property
    def window_duration(self) -> float:
        return (self.window - 1) / self.fs

    def update(self, samples: np.ndarray, sample_time: float) -> tuple[float, np.ndarray] | None:
        self.buffer.append(np.asarray(samples))
        if len(self.buffer) < self.window:
            return None
        y = np.asarray(self.buffer)
        c = self.K @ y
        local = c[0] + 1j*c[1]
        tref = sample_time - (self.window - 1)/(2*self.fs)
        return tref, local * np.exp(-2j*np.pi*self.f0*tref)
