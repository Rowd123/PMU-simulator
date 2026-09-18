"""Interface en ligne de commande reproductible."""
import argparse
from .animation import animate
from .config import SimulationConfig
from .simulation import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulateur PMU triphasé")
    sub = parser.add_subparsers(dest="command", required=True)
    sim = sub.add_parser("simulate"); sim.add_argument("config"); sim.add_argument("-o", "--output", required=True)
    anim = sub.add_parser("animate"); anim.add_argument("results"); anim.add_argument("-o", "--output", required=True)
    anim.add_argument("--fps", type=int, default=20); anim.add_argument("--mode", choices=("continuous", "sweep"), default="continuous")
    anim.add_argument("--parameter", default="scénario nominal")
    anim.add_argument("--playback-speed", type=float, default=1.0,
                      help="Vitesse de lecture : 2 = deux fois plus rapide, 0.5 = deux fois plus lent")
    anim.add_argument("--view", choices=("legacy", "frequency", "imbalance", "modulation"), default="legacy")
    args = parser.parse_args()
    if args.command == "simulate": run_simulation(SimulationConfig.load(args.config)).save(args.output)
    else: animate(args.results, args.output, args.fps, args.mode, args.parameter, args.playback_speed, args.view)


if __name__ == "__main__": main()
