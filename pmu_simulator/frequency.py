"""Estimation de fréquence/ROCOF sur l'angle de séquence directe."""
from collections import deque
import numpy as np
from .operators import frequency_operator


class FrequencyEstimator:
    def __init__(self, fs: float, f0: float, window: int):
        self.fs, self.f0, self.window = fs, f0, window
        self.B, self.G = frequency_operator(window)
        self.angles: deque[float] = deque(maxlen=window)
        self.last_raw: float | None = None
        self.last_unwrapped: float | None = None

    def update(self, angle: float, valid: bool) -> tuple[float, float] | None:
        if not valid or not np.isfinite(angle):
            self.angles.clear(); self.last_raw = self.last_unwrapped = None
            return None
        if self.last_raw is None:
            unwrapped = angle
        else:
            # np.unwrap local: corrige les sauts, sans imposer de monotonie.
            delta = (angle - self.last_raw + np.pi) % (2*np.pi) - np.pi
            unwrapped = self.last_unwrapped + delta  # type: ignore[operator]
        self.last_raw, self.last_unwrapped = angle, unwrapped
        self.angles.append(unwrapped)
        if len(self.angles) < self.window:
            return None
        b = self.G @ np.asarray(self.angles)
        T = (self.window - 1) / self.fs
        return self.f0 + b[1]/(2*np.pi*T), b[2]/(np.pi*T*T)


def theoretical_frequency(times: np.ndarray, positive_sequence: np.ndarray, f0: float,
                          threshold: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    valid = np.abs(positive_sequence) >= threshold
    angle = np.unwrap(np.angle(positive_sequence))
    f = np.full(times.shape, np.nan); rocof = np.full(times.shape, np.nan)
    if len(times) > 2:
        f[valid] = f0 + np.gradient(angle, times)[valid]/(2*np.pi)
        rocof[valid] = np.gradient(f, times)[valid]
    # Les dérivées numériques ne constituent pas une référence aux discontinuités.
    jumps = np.flatnonzero(np.abs(np.diff(angle)) > .5)
    for j in jumps:
        valid[max(0, j):min(len(valid), j+2)] = False
    f[~valid] = rocof[~valid] = np.nan
    return f, rocof, valid
