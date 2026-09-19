"""Orchestration pure du calcul, sans dépendance envers l'affichage."""
import numpy as np
from .config import SimulationConfig
from .frequency import FrequencyEstimator, theoretical_frequency
from .phasor import PhasorEstimator
from .results import SimulationResults
from .signals import generate
from .symmetrical import polar, transform
from .transmission import schedule


def run_simulation(config: SimulationConfig) -> SimulationResults:
    generated = generate(config)
    pe = PhasorEstimator(config.fs, config.f0, config.N)
    fe = FrequencyEstimator(config.fs, config.f0, config.M)
    tref, avail, phasors, frequencies, rocofs, freq_valid = [], [], [], [], [], []
    for i, (t, sample) in enumerate(zip(generated.times, generated.samples)):
        result = pe.update(sample, t)
        if result is None:
            continue
        tr, x = result
        seq = transform(x[None, :])[0]
        valid_angle = abs(seq[1]) >= config.angle_threshold
        fr = fe.update(np.angle(seq[1]), valid_angle)
        tref.append(tr); avail.append(t); phasors.append(x)
        if fr is None:
            frequencies.append(np.nan); rocofs.append(np.nan); freq_valid.append(False)
        else:
            frequencies.append(fr[0]); rocofs.append(fr[1]); freq_valid.append(True)
    tref_a, avail_a, xhat = np.asarray(tref), np.asarray(avail), np.asarray(phasors)
    true = np.column_stack([
        np.interp(tref_a, generated.times, generated.true_phasors[:, p].real)
        + 1j*np.interp(tref_a, generated.times, generated.true_phasors[:, p].imag)
        for p in range(3)
    ])
    seq, true_seq = transform(xhat), transform(true)
    _, _, angle_valid = polar(seq, config.angle_threshold)
    fref, rref, ref_valid = theoretical_frequency(tref_a, true_seq[:, 1], config.f0, config.angle_threshold)
    report_times, report_source, report_valid = schedule(config.duration, config.reporting_rate, avail_a)
    report_phasors = np.full((len(report_times), 3), np.nan + 1j*np.nan)
    report_sequences = np.full_like(report_phasors, np.nan + 1j*np.nan)
    report_frequency = np.full(len(report_times), np.nan)
    report_rocof = np.full(len(report_times), np.nan)
    report_frequency_valid = np.zeros(len(report_times), bool)
    src = report_source[report_valid]
    report_phasors[report_valid] = xhat[src]
    report_sequences[report_valid] = seq[src]
    report_frequency[report_valid] = np.asarray(frequencies)[src]
    report_rocof[report_valid] = np.asarray(rocofs)[src]
    report_frequency_valid[report_valid] = np.asarray(freq_valid)[src]
    return SimulationResults(
        generated.times, generated.samples, generated.true_phasors, tref_a, avail_a, xhat, true,
        seq, true_seq, np.asarray(frequencies), np.asarray(rocofs), fref, rref,
        np.ones(xhat.shape, bool), angle_valid, np.asarray(freq_valid), ref_valid,
        report_times, report_source, report_valid, report_phasors, report_sequences,
        report_frequency, report_rocof, report_frequency_valid,
        {"config": config.to_dict(), "phasor_window_samples": config.N,
         "phasor_window_duration_s": pe.window_duration, "frequency_window_samples": config.M,
         "absolute_start": config.absolute_start,
         "sequence_order": ["homopolaire", "directe", "inverse"],
         "reference_component_index": 0, "component_count": len(config.signal_components)},
        generated_components=generated.generated_components)
