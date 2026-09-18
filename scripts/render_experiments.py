"""Generate each simulation once, then render with independent playback speeds."""
import argparse
from pathlib import Path
from pmu_simulator.animation import animate
from pmu_simulator.config import SimulationConfig
from pmu_simulator.simulation import run_simulation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--speeds', type=float, nargs=3, default=(2, .5, 1),
                        metavar=('FREQUENCY', 'IMBALANCE', 'MODULATION'))
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for name, view, speed in zip(('frequency_variation', 'phase_unbalance', 'balanced_am_fm'),
                                 ('frequency', 'imbalance', 'modulation'), args.speeds):
        result = args.output_dir / 'results' / f'{name}.npz'
        run_simulation(SimulationConfig.load(root / 'examples' / f'{name}.json')).save(result)
        animate(result, args.output_dir / 'videos' / f'{name}.mp4',
                fps=args.fps, playback_speed=speed, view=view)


if __name__ == '__main__':
    main()
