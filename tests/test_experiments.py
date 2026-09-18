from pathlib import Path
from unittest.mock import patch
import hashlib
import numpy as np
import pytest
import matplotlib.pyplot as plt
from pmu_simulator.config import SimulationConfig
from pmu_simulator.signals import generate
from pmu_simulator.simulation import run_simulation
from pmu_simulator.symmetrical import transform
from pmu_simulator.animation import animate
from pmu_simulator.presentation import frame_schedule, presentation_view

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('frequency_variation', 'phase_unbalance', 'balanced_am_fm')


@pytest.fixture(scope='module')
def experiments():
    return {name: run_simulation(SimulationConfig.load(ROOT/'examples'/f'{name}.json')) for name in NAMES}


def test_reporting_constant_and_shared(experiments):
    for r in experiments.values():
        assert r.metadata['config']['reporting_rate'] == 50
        np.testing.assert_allclose(np.diff(r.report_times), 1/50, atol=1e-14)


@pytest.mark.parametrize('fps,speed', [(30, .5), (30, 1), (30, 2), (60, 4), (17, 1.3)])
def test_video_clock_and_read_only(experiments, tmp_path, fps, speed):
    r = experiments['balanced_am_fm']
    path = tmp_path/'results.npz'
    r.save(path)
    digest = hashlib.sha256(path.read_bytes()).digest()
    frames = frame_schedule(10, fps, speed)
    assert abs(len(frames)/fps - 10/speed) < 1/fps + 1e-12
    assert frames[-1] == 10
    assert len(frame_schedule(100, 30, 1)) == 3000  # no old 400-frame cap
    with patch('pmu_simulator.animation._save') as save:
        animate(path, tmp_path/'out.mp4', fps=fps, playback_speed=speed, view='modulation')
        np.testing.assert_array_equal(save.call_args.args[2], frames)
        plt.close(save.call_args.args[0])
    assert hashlib.sha256(path.read_bytes()).digest() == digest


@pytest.mark.parametrize('fps,speed', [(0, 1), (30, 0), (-1, 1), (30, np.nan), (30, np.inf)])
def test_invalid_video_clock(fps, speed):
    with pytest.raises(ValueError):
        frame_schedule(10, fps, speed)


def test_balanced_am_fm(experiments):
    cfg = SimulationConfig.load(ROOT/'examples/balanced_am_fm.json')
    g = generate(cfg)
    np.testing.assert_allclose(g.amplitudes[:, 0], g.amplitudes[:, 1])
    np.testing.assert_allclose(g.amplitudes[:, 0], g.amplitudes[:, 2])
    np.testing.assert_allclose(transform(g.true_phasors)[:, [0, 2]], 0, atol=1e-9)
    r = experiments['balanced_am_fm']
    np.testing.assert_allclose(r.true_sequences[:, [0, 2]], 0, atol=1e-9)
    np.testing.assert_allclose(r.sequences[:, 0], 0, atol=1e-9)
    # Fixed nominal-frequency LS has image leakage under AM/FM; do not hide it.
    assert np.max(abs(r.sequences[:, 2])) / 230 < .01
    expected = cfg.frequency.evaluate(g.times)
    np.testing.assert_allclose(g.frequency, expected, atol=1e-12)
    np.testing.assert_allclose(np.diff(g.theta)*cfg.fs/(2*np.pi),
                               (expected[:-1]+expected[1:])/2, atol=1e-9)
    np.testing.assert_allclose(r.frequency_reference[2:-2],
                               cfg.frequency.evaluate(r.estimate_times[2:-2]), atol=1e-5)


def test_unbalance_event(experiments):
    r = experiments['phase_unbalance']
    before = r.estimate_times < 3.9
    after = r.estimate_times > 4.1
    np.testing.assert_allclose(r.sequences[before][:, [0, 2]], 0, atol=1e-9)
    expected = 230*abs(np.exp(1j*np.deg2rad(20))-1)/3
    np.testing.assert_allclose(abs(r.sequences[after][:, [0, 2]]), expected, atol=1e-9)


@pytest.mark.parametrize('view', ['frequency', 'imbalance', 'modulation'])
def test_reveal_only_received_reports(experiments, view):
    r = experiments['phase_unbalance']
    fig, draw = presentation_view(r, view, np.array([0., .5, 10.]), 1)
    artists = draw(0)
    assert len(artists[0].get_xdata()) == 0
    artists = draw(1)
    assert len(artists[0].get_xdata()) == np.count_nonzero(r.report_valid & (r.report_times <= .5))
    draw(2)
    plt.close(fig)
