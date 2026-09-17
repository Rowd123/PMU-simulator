"""Génération des signaux et références, sans connaissance des estimateurs."""
from dataclasses import dataclass
import numpy as np
from .config import SimulationConfig
from .noise import gaussian_noise


@dataclass
class GeneratedSignals:
    times: np.ndarray
    samples: np.ndarray
    true_phasors: np.ndarray
    amplitudes: np.ndarray
    angles: np.ndarray
    frequency: np.ndarray
    theta: np.ndarray


def generate(config: SimulationConfig) -> GeneratedSignals:
    count = int(np.floor(config.duration * config.fs)) + 1
    t = np.arange(count) / config.fs
    f = config.frequency.evaluate(t)
    # Intégrale trapézoïdale, avec phase exactement nulle à l'origine.
    theta = np.zeros(count)
    theta[1:] = 2*np.pi*np.cumsum((f[:-1] + f[1:]) / (2*config.fs))
    a = np.column_stack([p.evaluate(t) for p in config.amplitudes])
    phi = np.deg2rad(np.column_stack([p.evaluate(t) for p in config.angles_deg]))
    carrier = theta[:, None] + phi
    clean = np.sqrt(2) * a * np.cos(carrier)
    samples = clean + gaussian_noise(count, config.noise_variances, np.random.default_rng(config.seed))
    true = a * np.exp(1j * (carrier - 2*np.pi*config.f0*t[:, None]))
    return GeneratedSignals(t, samples, true, a, phi, f, theta)
