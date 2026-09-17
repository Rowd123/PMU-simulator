"""Animations reconstruites exclusivement depuis un fichier de résultats."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter
from .results import SimulationResults


def animate(result_file: str | Path, output: str | Path, fps: int = 20,
            mode: str = "continuous", parameter_label: str = "scénario") -> None:
    """Rend une vue synchronisée; ``sweep`` marque des simulations indépendantes."""
    r = SimulationResults.load(result_file)
    fig = plt.figure(figsize=(12, 8), layout="constrained")
    grid = fig.add_gridspec(2, 2)
    ax_signal, ax_vec, ax_metrics = fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, :])
    colors = ("tab:red", "tab:green", "tab:blue")
    for p, label in enumerate("abc"):
        ax_signal.plot([], [], color=colors[p], label=f"Phase {label}")
    ax_signal.set(xlabel="Temps relatif (s)", ylabel="Tension (V)", title="Signaux — période nominale glissante")
    ax_signal.legend(loc="upper right"); ax_signal.grid(True)
    ax_vec.set(title="Phaseurs (plein) et séquences (pointillé)", xlabel="Partie réelle (V)", ylabel="Partie imaginaire (V)")
    ax_vec.axhline(0, color=".7"); ax_vec.axvline(0, color=".7"); ax_vec.set_aspect("equal")
    ax_metrics.set(xlabel="Temps (s)", ylabel="Fréquence (Hz) / ROCOF (Hz/s)", title="Estimations et références")
    ax_metrics.plot(r.estimate_times, r.frequency_reference, "k--", label="Fréquence vraie")
    ax_metrics.plot(r.estimate_times, r.rocof_reference, color=".5", ls="--", label="ROCOF vrai")
    freq_line, = ax_metrics.plot([], [], "tab:purple", label="Fréquence estimée")
    roc_line, = ax_metrics.plot([], [], "tab:orange", label="ROCOF estimé")
    ax_metrics.legend(ncol=2); ax_metrics.grid(True); ax_metrics.set_xlim(0, r.sample_times[-1])
    finite = np.r_[r.frequency_reference[np.isfinite(r.frequency_reference)], r.frequency[np.isfinite(r.frequency)], r.rocof[np.isfinite(r.rocof)]]
    if finite.size: ax_metrics.set_ylim(finite.min()-1, finite.max()+1)
    count = min(max(2, int(r.sample_times[-1] * fps) + 1), 400)
    frame_times = np.linspace(0, r.sample_times[-1], count)

    def draw(frame: int):
        now = frame_times[frame]
        end = np.searchsorted(r.sample_times, now, side="right")
        begin = np.searchsorted(r.sample_times, now - 1/r.metadata["config"]["f0"])
        for p, line in enumerate(ax_signal.lines[:3]): line.set_data(r.sample_times[begin:end], r.samples[begin:end, p])
        ax_signal.relim(); ax_signal.autoscale_view()
        k = np.searchsorted(r.availability_times, now, side="right") - 1
        while len(ax_vec.lines) > 2: ax_vec.lines[-1].remove()
        if k >= 0:
            for p, z in enumerate(r.phasors[k]): ax_vec.plot([0,z.real], [0,z.imag], color=colors[p], lw=2)
            for j, z in enumerate(r.sequences[k]): ax_vec.plot([0,z.real], [0,z.imag], ls="--", label=("X0","X1","X2")[j])
            limit = max(1, np.max(np.abs(np.r_[r.phasors[k], r.sequences[k]]))*1.2); ax_vec.set(xlim=(-limit,limit), ylim=(-limit,limit))
            freq_line.set_data(r.estimate_times[:k+1], r.frequency[:k+1]); roc_line.set_data(r.estimate_times[:k+1], r.rocof[:k+1])
        fig.suptitle(f"t = {now:.3f} s — {parameter_label} — mode {'continu' if mode == 'continuous' else 'balayage indépendant'}")
        return tuple(ax_signal.lines) + (freq_line, roc_line)
    ani = FuncAnimation(fig, draw, frames=count, interval=1000/fps, blit=False)
    output = Path(output)
    writer = PillowWriter(fps=fps) if output.suffix.lower() == ".gif" else FFMpegWriter(fps=fps)
    ani.save(output, writer=writer); plt.close(fig)
