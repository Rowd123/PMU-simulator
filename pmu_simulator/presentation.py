"""Presentation views: reveal saved PMU reports, never recalculate measurements."""
import numpy as np
import matplotlib.pyplot as plt


def frame_schedule(duration, fps, playback_speed):
    """Frame endpoints; encoded duration differs from duration/speed by <1/fps."""
    if not all(np.isfinite(x) and x > 0 for x in (duration, fps, playback_speed)):
        raise ValueError("duration, fps et playback_speed doivent être finis et positifs")
    count = max(1, int(np.ceil(duration * fps / playback_speed)))
    return np.minimum((np.arange(count) + 1) * playback_speed / fps, duration)


def unwrapped_phase(values, valid):
    """Unwrap each valid run at estimator cadence, before selecting reports."""
    result = np.full(len(values), np.nan)
    indices = np.flatnonzero(valid & np.isfinite(values))
    for group in np.split(indices, np.flatnonzero(np.diff(indices) != 1) + 1):
        if len(group):
            result[group] = np.rad2deg(np.unwrap(np.angle(values[group])))
    return result


def presentation_view(r, view, frame_times, playback_speed):
    valid = r.report_valid
    src = r.report_source[valid]
    arrival = r.report_times[valid]
    times = r.estimate_times[src]
    estimated = r.report_sequences[valid]
    reference = r.true_sequences[src]
    fig = plt.figure(figsize=(12.8, 7.2), layout="constrained")
    traces, vectors = [], []
    colors = ("#BA641D", "#168578", "#6D69B4")
    duration = r.metadata["config"]["duration"]
    multicomponent = view == "multicomponent" or r.metadata.get("component_count", 1) > 1
    reference_label = "référence principale" if multicomponent else "référence"

    def chart(ax, series, ylabel):
        for values, label, color, style in series:
            line, = ax.plot([], [], color=color, ls=style, lw=2, label=label)
            traces.append((line, values))
        finite = np.concatenate([v[np.isfinite(v)] for v, *_ in series])
        if len(finite):
            lo, hi = finite.min(), finite.max()
            pad = max((hi-lo)*.12, abs(hi)*.002, .01)
            ax.set_ylim(lo-pad, hi+pad)
        ax.set(xlim=(0, duration), ylabel=ylabel)
        ax.grid(alpha=.2)
        ax.legend(loc="upper left", ncol=2, fontsize=9)

    def pair(ref, est):
        ref_label = "Référence (composante principale)" if multicomponent else "Référence"
        est_label = "Estimation PMU (signal total)" if multicomponent else "Estimation PMU"
        return [(ref, ref_label, "#323D48", "--"), (est, est_label, colors[1], "-")]

    if view == "imbalance":
        grid = fig.add_gridspec(2, 2)
        for ax, values, labels, title in (
            (fig.add_subplot(grid[0, 0]), r.report_phasors[valid], ("Va", "Vb", "Vc"), "Phaseurs estimés"),
            (fig.add_subplot(grid[0, 1]), estimated, ("V0 · homopolaire", "V1 · positive", "V2 · négative"), "Composantes symétriques estimées"),
        ):
            limit = max(1, np.nanmax(np.abs(values))*1.15)
            ax.set(xlim=(-limit, limit), ylim=(-limit, limit), aspect="equal",
                   xlabel="Réel (V RMS)", ylabel="Imaginaire (V RMS)", title=title)
            ax.axhline(0, color=".8"); ax.axvline(0, color=".8")
            for j, label in enumerate(labels):
                line, = ax.plot([], [], color=colors[j], lw=2, marker="o", markevery=[1], label=label)
                vectors.append((line, values[:, j]))
            ax.legend(loc="upper left", fontsize=8)
        ax = fig.add_subplot(grid[1, :])
        chart(ax, [(np.abs(estimated[:, j]), f"|V{j}| PMU", colors[j], "-") for j in range(3)] +
              [(np.abs(reference[:, j]), f"|V{j}| {reference_label}", colors[j], "--") for j in range(3)], "Amplitude (V RMS)")
        ax.set_xlabel("Temps représentatif de la mesure (s)")
        title = "Déséquilibre angulaire"
    else:
        axes = fig.subplots(4 if view == "modulation" else 3, 1, sharex=True)
        chart(axes[0], pair(np.abs(reference[:, 1]), np.abs(estimated[:, 1])), "|V1| (V RMS)")
        ref_phase = unwrapped_phase(r.true_sequences[:, 1], np.abs(r.true_sequences[:, 1]) >= r.metadata['config']['angle_threshold'])
        phase = unwrapped_phase(r.sequences[:, 1], r.sequence_angle_valid[:, 1])
        chart(axes[1], pair(ref_phase[src], phase[src]), "Phase V1 (°)\ndéroulée")
        freq = np.where(r.report_frequency_valid[valid], r.report_frequency[valid], np.nan)
        chart(axes[2], pair(r.frequency_reference[src], freq), "Fréquence (Hz)")
        if view == "modulation":
            chart(axes[3], [(np.abs(estimated[:, j]), f"|V{j}| PMU", colors[j], "-") for j in (0, 2)] +
                  [(np.abs(reference[:, j]), f"|V{j}| {reference_label}", colors[j], "--") for j in (0, 2)], "Résidus (V RMS)")
        axes[-1].set_xlabel("Temps représentatif de la mesure (s)")
        title = {"modulation": "AM / FM équilibrée",
                 "multicomponent": "Superposition de composantes"}.get(view, "Variation de fréquence")
    heading = fig.suptitle("")

    def draw(frame):
        now = frame_times[frame]
        end = np.searchsorted(arrival, now, side="right")
        for line, values in traces:
            line.set_data(times[:end], values[:end])
        for line, values in vectors:
            z = values[end-1] if end else np.nan + 1j*np.nan
            line.set_data([0, z.real], [0, z.imag])
        heading.set_text(f"{title}  |  t = {now:.2f} s  |  PMU : {r.metadata['config']['reporting_rate']:g} trames/s  |  lecture ×{playback_speed:g}")
        return tuple(line for line, _ in traces + vectors) + (heading,)

    return fig, draw
