"""Ordonnancement des trames, indépendant des cadences de calcul."""
import numpy as np


def schedule(duration: float, rate: float, availability: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    times = np.arange(int(np.floor(duration * rate)) + 1) / rate
    # searchsorted respecte toute valeur réelle de fs/fr, sans arrondir le rapport.
    source = np.searchsorted(availability, times, side="right") - 1
    valid = source >= 0
    return times, source, valid
