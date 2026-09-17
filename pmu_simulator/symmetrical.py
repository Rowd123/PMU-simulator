"""Composantes homopolaire, directe et inverse."""
import numpy as np
from .operators import symmetrical_operator


def transform(phasors: np.ndarray) -> np.ndarray:
    return np.asarray(phasors) @ symmetrical_operator().T


def polar(values: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    magnitude = np.abs(values)
    valid = magnitude >= threshold
    angle = np.where(valid, np.angle(values), np.nan)
    return magnitude, angle, valid
