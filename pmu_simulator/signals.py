"""Génération des signaux et références, sans connaissance des estimateurs."""
from dataclasses import dataclass, replace
import numpy as np
from .config import SignalComponent, SimulationConfig
from .noise import gaussian_noise


@dataclass
class GeneratedSignals:
    """Échantillons totaux ; les profils et phaseurs décrivent la principale."""
    times: np.ndarray
    samples: np.ndarray
    true_phasors: np.ndarray
    amplitudes: np.ndarray
    angles: np.ndarray
    frequency: np.ndarray
    theta: np.ndarray
    generated_components: np.ndarray | None = None  # (composante, échantillon, phase), sans bruit


def _generate_component(component: SignalComponent, t: np.ndarray,
                        fs: float, f0: float) -> GeneratedSignals:
    """Même construction temporelle et même référence que le signal historique."""
    f = component.frequency.evaluate(t)
    # Intégrale trapézoïdale, avec phase exactement nulle à l'origine.
    theta = np.zeros(len(t))
    theta[1:] = 2*np.pi*np.cumsum((f[:-1] + f[1:]) / (2*fs))
    a = np.column_stack([p.evaluate(t) for p in component.amplitudes])
    phi = np.deg2rad(np.column_stack([p.evaluate(t) for p in component.angles_deg]))
    carrier = theta[:, None] + phi
    clean = np.sqrt(2) * a * np.cos(carrier)
    true = a * np.exp(1j * (carrier - 2*np.pi*f0*t[:, None]))
    return GeneratedSignals(t, clean, true, a, phi, f, theta)


def generate(config: SimulationConfig) -> GeneratedSignals:
    count = int(np.floor(config.duration * config.fs)) + 1
    t = np.arange(count) / config.fs
    components = config.signal_components
    primary = _generate_component(components[0], t, config.fs, config.f0)
    # Un seul tableau de diagnostic, sans liste puis copie de tous les signaux.
    generated_components = np.empty((len(components), count, 3))
    generated_components[0] = primary.samples
    for index, component in enumerate(components[1:], start=1):
        generated_components[index] = _generate_component(
            component, t, config.fs, config.f0
        ).samples
    samples = generated_components.sum(axis=0) + gaussian_noise(
        count, config.noise_variances, np.random.default_rng(config.seed)
    )
    # Ne jamais sommer les références : seul le signal temporel est superposé.
    return replace(primary, samples=samples, generated_components=generated_components)
