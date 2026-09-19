"""Analytical and end-to-end checks for a sum of triphasic components."""
from dataclasses import fields
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
import pytest

from pmu_simulator.animation import animate
from pmu_simulator.config import SignalComponent, SimulationConfig
from pmu_simulator.presentation import presentation_view
from pmu_simulator.results import SimulationResults
from pmu_simulator.signals import generate
from pmu_simulator.simulation import run_simulation
from pmu_simulator.symmetrical import transform

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("count", [1, 3, 8])
def test_analytical_balanced_sum_for_any_component_count(count):
    frequencies = 49.5 + np.arange(count) * 1.25
    amplitudes = 100 / (1 + np.arange(count))
    angles = 15 * np.arange(count)[:, None] + np.array([0, -120, 120])
    cfg = SimulationConfig(fs=800, duration=.4, components=[
        {"frequency": f, "amplitudes": a, "angles_deg": phi.tolist()}
        for f, a, phi in zip(frequencies, amplitudes, angles)
    ])
    g = generate(cfg)
    phase = (2 * np.pi * frequencies[:, None, None] * g.times[None, :, None]
             + np.deg2rad(angles[:, None, :]))
    expected = np.sqrt(2) * amplitudes[:, None, None] * np.cos(phase)
    np.testing.assert_allclose(g.generated_components, expected, atol=2e-10)
    np.testing.assert_allclose(g.samples, expected.sum(axis=0), atol=2e-10)
    # Each frequency has a balanced positive-sequence triplet, and xa+xb+xc=0.
    phasors = amplitudes[:, None, None] * np.exp(1j * phase)
    np.testing.assert_allclose(transform(phasors)[..., [0, 2]], 0, atol=1e-10)
    np.testing.assert_allclose(g.generated_components.sum(axis=2), 0, atol=2e-10)
    np.testing.assert_allclose(g.samples.sum(axis=1), 0, atol=2e-10)


def test_independent_frequency_amplitude_and_angle_profiles():
    cfg = SimulationConfig(fs=800, duration=.5, components=[
        {"frequency": {"kind": "ramp", "value": 49, "final": 53, "duration": .5},
         "amplitudes": {"kind": "sine", "value": 100, "amplitude": 10,
                        "modulation_frequency": 2}},
        {"frequency": {"kind": "ramp", "value": 60, "final": 59, "duration": .5},
         "amplitudes": [10, 20, 30],
         "angles_deg": [{"kind": "ramp", "value": 20, "final": 30,
                         "duration": .5}, -100, 140]},
    ])
    g = generate(cfg)
    t = g.times
    # A linear frequency ramp integrates exactly to a quadratic phase.
    theta0 = 2 * np.pi * (49 * t + 4 * t**2)
    theta1 = 2 * np.pi * (60 * t - t**2)
    amplitude0 = 100 + 10 * np.sin(4 * np.pi * t)
    angle0 = np.deg2rad([0, -120, 120])
    angle1 = np.deg2rad(np.column_stack((20 + 20*t, t*0 - 100, t*0 + 140)))
    expected = np.stack([
        np.sqrt(2) * amplitude0[:, None] * np.cos(theta0[:, None] + angle0),
        np.sqrt(2) * np.array([10, 20, 30]) * np.cos(theta1[:, None] + angle1),
    ])
    np.testing.assert_allclose(g.generated_components, expected, atol=1e-10)
    np.testing.assert_allclose(g.samples, expected.sum(axis=0), atol=1e-10)


@pytest.mark.parametrize("name", ["nominal", "balanced_am_fm"])
def test_single_component_preserves_legacy_results(name):
    cfg = SimulationConfig.load(ROOT / "examples" / f"{name}.json")
    cfg.fs, cfg.duration = 800, .3
    cfg.noise_variances = (1., 2., 3.)
    old_format = cfg.to_dict()
    assert "components" not in old_format
    component = {key: old_format.pop(key) for key in ("frequency", "amplitudes", "angles_deg")}
    explicit = SimulationConfig(**old_format, components=[component])
    legacy, modern = run_simulation(cfg), run_simulation(explicit)
    for field in fields(SimulationResults):
        if field.name != "metadata":
            np.testing.assert_array_equal(getattr(legacy, field.name), getattr(modern, field.name))


@pytest.mark.parametrize("components", [[], {}, [12], [{"amplitudes": [1, 2]}],
                                        [{"angles_deg": [0, 120]}]])
def test_invalid_component_configuration(components):
    with pytest.raises(ValueError):
        SimulationConfig(components=components)


def test_noise_is_added_once_to_the_sum_and_zero_component_is_neutral():
    common = dict(fs=800, duration=.3, seed=42, noise_variances=(1., 4., 9.))
    component = SignalComponent(frequency=50.5, amplitudes=230)
    cfg = SimulationConfig(**common, components=[component])
    expanded = SimulationConfig(**common, components=[component,
                               {"frequency": 52, "amplitudes": 0}])
    one, two = run_simulation(cfg), run_simulation(expanded)
    for field in fields(SimulationResults):
        if field.name not in ("metadata", "generated_components"):
            np.testing.assert_array_equal(getattr(one, field.name), getattr(two, field.name))
    many = SimulationConfig(**common, components=[component,
                            {"frequency": 52, "amplitudes": 20},
                            {"frequency": 55, "amplitudes": 10}])
    g = generate(many)
    expected_noise = np.random.default_rng(42).normal(size=g.samples.shape) * [1, 2, 3]
    np.testing.assert_array_equal(g.samples, g.generated_components.sum(axis=0) + expected_noise)
    np.testing.assert_array_equal(generate(many).samples, g.samples)


@pytest.fixture(scope="module")
def multicomponent():
    cfg = SimulationConfig.load(ROOT / "examples/multicomponent.json")
    return cfg, run_simulation(cfg)


def test_total_goes_through_the_existing_pmu_and_reference_stays_primary(multicomponent):
    cfg, total = multicomponent
    assert len(cfg.signal_components) == 3
    single = [run_simulation(SimulationConfig(
        fs=cfg.fs, f0=cfg.f0, duration=cfg.duration,
        reporting_rate=cfg.reporting_rate, components=[component]
    )) for component in cfg.signal_components]
    # The unchanged LS estimator is linear in its input samples.
    np.testing.assert_allclose(total.phasors, sum(r.phasors for r in single), atol=1e-10)
    np.testing.assert_allclose(total.sequences, sum(r.sequences for r in single), atol=1e-10)
    np.testing.assert_array_equal(total.samples, total.generated_components.sum(axis=0))
    for name in ("true_sample_phasors", "true_phasors", "true_sequences",
                 "frequency_reference", "rocof_reference", "reference_frequency_valid",
                 "report_times", "report_source", "report_valid"):
        np.testing.assert_array_equal(getattr(total, name), getattr(single[0], name))
    np.testing.assert_allclose(total.frequency_reference[2:-2], 50.5, atol=1e-9)
    np.testing.assert_allclose(total.true_sequences[:, [0, 2]], 0, atol=1e-9)
    np.testing.assert_allclose(total.sequences[:, 0], 0, atol=1e-9)
    np.testing.assert_array_equal(total.report_times, np.arange(501) / 50)
    # Beating is present in the estimated frequency; it is not a fixed mean.
    assert np.ptp(total.frequency[total.frequency_valid]) > .01
    assert np.max(abs(total.phasors - single[0].phasors)) > 1


def test_npz_round_trip_and_legacy_file_loading(multicomponent, tmp_path):
    cfg, result = multicomponent
    path = tmp_path / "new" / "multicomponent.npz"
    result.save(path)
    restored = SimulationResults.load(path)
    assert restored.metadata["component_count"] == 3
    assert restored.metadata["reference_component_index"] == 0
    assert restored.metadata == json.loads(json.dumps(result.metadata))
    for field in fields(SimulationResults):
        if field.name != "metadata":
            np.testing.assert_array_equal(getattr(restored, field.name), getattr(result, field.name))
    replay = generate(SimulationConfig(**restored.metadata["config"]))
    np.testing.assert_array_equal(replay.samples, result.samples)
    np.testing.assert_array_equal(replay.generated_components, result.generated_components)
    # Old files have neither the diagnostic array nor the new metadata keys.
    legacy = run_simulation(SimulationConfig(fs=800, duration=.2))
    legacy.generated_components = None
    legacy.metadata.pop("component_count")
    legacy.metadata.pop("reference_component_index")
    legacy_path = tmp_path / "legacy.npz"
    legacy.save(legacy_path)
    restored_legacy = SimulationResults.load(legacy_path)
    assert restored_legacy.generated_components is None
    np.testing.assert_array_equal(restored_legacy.samples, legacy.samples)
    assert SimulationConfig(**restored_legacy.metadata["config"]).components is None


def test_multicomponent_video_labels_reporting_and_read_only(multicomponent, tmp_path):
    cfg, result = multicomponent
    fig, draw = presentation_view(result, "multicomponent", np.array([0., .5, 10.]), 1)
    try:
        assert len(draw(0)[0].get_xdata()) == 0
        received = np.count_nonzero(result.report_valid & (result.report_times <= .5))
        assert len(draw(1)[0].get_xdata()) == received
        draw(2)
        for ax in fig.axes:
            assert ax.lines[0].get_label() == "Référence (composante principale)"
            assert ax.lines[1].get_label() == "Estimation PMU (signal total)"
    finally:
        plt.close(fig)
    path = tmp_path / "result.npz"
    result.save(path)
    digest = hashlib.sha256(path.read_bytes()).digest()
    with patch("pmu_simulator.animation._save") as save:
        animate(path, tmp_path / "out.mp4", view="multicomponent", fps=20, playback_speed=2)
        assert len(save.call_args.args[2]) == 100
        plt.close(save.call_args.args[0])
    assert hashlib.sha256(path.read_bytes()).digest() == digest
