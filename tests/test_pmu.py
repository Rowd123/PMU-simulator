import numpy as np
from pmu_simulator.config import SimulationConfig
from pmu_simulator.frequency import FrequencyEstimator
from pmu_simulator.operators import phasor_operator
from pmu_simulator.simulation import run_simulation
from pmu_simulator.symmetrical import transform
from pmu_simulator.transmission import schedule


def test_nominal_balanced_noiseless():
    cfg = SimulationConfig(duration=.25, frequency_window=20)
    r = run_simulation(cfg)
    np.testing.assert_allclose(r.sequences[-1, 1], 230, atol=1e-10)
    np.testing.assert_allclose(r.sequences[-1, [0, 2]], 0, atol=1e-10)
    np.testing.assert_allclose(r.frequency[r.frequency_valid], 50, atol=1e-10)
    np.testing.assert_allclose(r.rocof[r.frequency_valid], 0, atol=1e-8)


def test_known_unbalanced_sequences():
    expected = np.array([10+2j, 230-4j, 7+3j])
    alpha = np.exp(2j*np.pi/3)
    inverse = np.array([[1,1,1], [1,alpha**2,alpha], [1,alpha,alpha**2]])
    phases = inverse @ expected
    np.testing.assert_allclose(transform(phases[None])[0], expected)


def test_quadratic_angle_coefficients_exactly():
    fs, f0, m = 4800., 50., 31
    estimator = FrequencyEstimator(fs, f0, m)
    T = (m-1)/fs
    u = (np.arange(m)-(m-1))/(m-1)
    b = np.array([.2, .03, -.004])
    output = None
    for angle in np.column_stack((np.ones(m), u, u*u)) @ b:
        output = estimator.update(angle, True)
    assert output is not None
    np.testing.assert_allclose(output, [f0+b[1]/(2*np.pi*T), b[2]/(np.pi*T*T)], rtol=1e-11)


def test_monte_carlo_phaseur_standard_deviation():
    fs, f0, n, sigma, trials = 4800., 50., 96, 3., 12000
    _, k = phasor_operator(fs, f0, n)
    rng = np.random.default_rng(7)
    estimates = np.empty(trials, complex)
    chunk = 1000
    for start in range(0, trials, chunk):
        noise = rng.normal(0, sigma, (min(chunk, trials-start), n))
        c = noise @ k.T
        estimates[start:start+len(noise)] = c[:, 0] + 1j*c[:, 1]
    # Pour une période complète, S'S=N I : chaque écart-type vaut sigma/sqrt(N).
    expected = sigma/np.sqrt(n)
    np.testing.assert_allclose([estimates.real.std(), estimates.imag.std()], expected, rtol=.025)


def test_non_integer_reporting_and_invalid_start():
    availability = np.arange(9, 100) / 1000
    times, source, valid = schedule(.08, 47., availability)
    np.testing.assert_allclose(times, np.arange(4)/47)
    assert not valid[0] and source[0] == -1
    assert np.all(availability[source[valid]] <= times[valid])
    assert not np.isclose(1000/47, round(1000/47))


def test_invalid_angle_resets_frequency_window():
    estimator = FrequencyEstimator(1000, 50, 3)
    assert estimator.update(0., True) is None
    assert estimator.update(.1, True) is None
    assert estimator.update(np.nan, False) is None
    assert estimator.update(.2, True) is None
    assert estimator.update(.3, True) is None
    assert estimator.update(.4, True) is not None
