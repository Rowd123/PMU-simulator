"""Configuration validée et profils temporels du simulateur."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Profile:
    """Profil constant, échelon, rampe ou modulation sinusoïdale."""
    kind: str = "constant"
    value: float = 0.0
    time: float = 0.0
    final: float | None = None
    duration: float = 0.0
    amplitude: float = 0.0
    modulation_frequency: float = 1.0
    phase_deg: float = 0.0

    def evaluate(self, t: np.ndarray) -> np.ndarray:
        if self.kind == "constant":
            return np.full_like(t, self.value, dtype=float)
        if self.kind == "step":
            return np.where(t < self.time, self.value, self.final_value)
        if self.kind == "ramp":
            q = np.clip((t - self.time) / self.duration, 0.0, 1.0)
            return self.value + q * (self.final_value - self.value)
        if self.kind == "sine":
            return self.value + self.amplitude * np.sin(
                2 * np.pi * self.modulation_frequency * t + np.deg2rad(self.phase_deg)
            )
        raise ValueError(f"type de profil inconnu: {self.kind}")

    @property
    def final_value(self) -> float:
        if self.final is None:
            raise ValueError("'final' est requis pour un échelon ou une rampe")
        return self.final

    @classmethod
    def parse(cls, value: float | dict[str, Any] | "Profile") -> "Profile":
        if isinstance(value, cls):
            return value
        return cls(value=float(value)) if np.isscalar(value) else cls(**value)


def _default_amplitudes() -> tuple[Profile, ...]:
    return tuple(Profile(value=230.0) for _ in range(3))


def _default_angles() -> tuple[Profile, ...]:
    return tuple(Profile(value=x) for x in (0.0, -120.0, 120.0))


@dataclass
class SimulationConfig:
    f0: float = 50.0
    fs: float = 4800.0
    reporting_rate: float = 50.0
    duration: float = 1.0
    seed: int = 1234
    frequency: Profile = field(default_factory=lambda: Profile(value=50.0))
    amplitudes: tuple[Profile, Profile, Profile] = field(default_factory=_default_amplitudes)
    angles_deg: tuple[Profile, Profile, Profile] = field(default_factory=_default_angles)
    noise_variances: tuple[float, float, float] = (0.0, 0.0, 0.0)
    phasor_window: int | None = None
    frequency_window: int | None = None
    angle_threshold: float = 1e-9
    absolute_start: str | None = None

    def __post_init__(self) -> None:
        self.frequency = Profile.parse(self.frequency)
        if isinstance(self.amplitudes, (int, float, dict, Profile)):
            self.amplitudes = (Profile.parse(self.amplitudes),) * 3
        self.amplitudes = tuple(Profile.parse(x) for x in self.amplitudes)  # type: ignore[assignment]
        self.angles_deg = tuple(Profile.parse(x) for x in self.angles_deg)  # type: ignore[assignment]
        if len(self.amplitudes) != 3 or len(self.angles_deg) != 3:
            raise ValueError("amplitudes et angles_deg doivent avoir trois éléments")
        if np.isscalar(self.noise_variances):
            self.noise_variances = (float(self.noise_variances),) * 3
        self.noise_variances = tuple(float(x) for x in self.noise_variances)  # type: ignore[assignment]
        if len(self.noise_variances) != 3 or min(self.noise_variances) < 0:
            raise ValueError("les trois variances doivent être positives ou nulles")
        if min(self.f0, self.fs, self.reporting_rate, self.duration) <= 0:
            raise ValueError("f0, fs, reporting_rate et duration doivent être positifs")
        if self.N < 2:
            raise ValueError("phasor_window doit fournir au moins deux observations")
        tau = (np.arange(self.N) - (self.N - 1) / 2) / self.fs
        s = np.sqrt(2) * np.column_stack((np.cos(2*np.pi*self.f0*tau), -np.sin(2*np.pi*self.f0*tau)))
        if np.linalg.matrix_rank(s) < 2:
            raise ValueError("configuration de phaseur de rang insuffisant")
        if self.M < 3:
            raise ValueError("frequency_window doit être supérieur ou égal à 3")

    @property
    def N(self) -> int:
        return self.phasor_window or round(self.fs / self.f0)

    @property
    def M(self) -> int:
        return self.frequency_window or max(3, round(4 * self.fs / self.f0))

    @classmethod
    def load(cls, path: str | Path) -> "SimulationConfig":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
