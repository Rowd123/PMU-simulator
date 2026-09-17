"""Conteneur et format NPZ autonome destiné au calcul différé des graphiques."""
from __future__ import annotations
from dataclasses import dataclass, fields
import json
from pathlib import Path
import numpy as np


@dataclass
class SimulationResults:
    sample_times: np.ndarray
    samples: np.ndarray
    true_sample_phasors: np.ndarray
    estimate_times: np.ndarray
    availability_times: np.ndarray
    phasors: np.ndarray
    true_phasors: np.ndarray
    sequences: np.ndarray
    true_sequences: np.ndarray
    frequency: np.ndarray
    rocof: np.ndarray
    frequency_reference: np.ndarray
    rocof_reference: np.ndarray
    phasor_valid: np.ndarray
    sequence_angle_valid: np.ndarray
    frequency_valid: np.ndarray
    reference_frequency_valid: np.ndarray
    report_times: np.ndarray
    report_source: np.ndarray
    report_valid: np.ndarray
    report_phasors: np.ndarray
    report_sequences: np.ndarray
    report_frequency: np.ndarray
    report_rocof: np.ndarray
    report_frequency_valid: np.ndarray
    metadata: dict

    def save(self, path: str | Path) -> None:
        arrays = {f.name: getattr(self, f.name) for f in fields(self) if f.name != "metadata"}
        np.savez_compressed(path, **arrays, metadata=np.array(json.dumps(self.metadata)))

    @classmethod
    def load(cls, path: str | Path) -> "SimulationResults":
        with np.load(path, allow_pickle=False) as data:
            args = {f.name: data[f.name] for f in fields(cls) if f.name != "metadata"}
            args["metadata"] = json.loads(str(data["metadata"]))
        return cls(**args)
