from __future__ import annotations

import argparse
import json
from pathlib import Path

from .demo import replay_saved_tree, run_demo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dreamnet")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="run online collection, dreaming, and holdout evaluation")
    demo.add_argument("--output", type=Path, default=Path("artifacts/demo"))
    demo.add_argument("--train", type=int, default=84)
    demo.add_argument("--test", type=int, default=42)
    demo.add_argument("--candidates", type=int, default=400)
    demo.add_argument("--seed", type=int, default=7)
    demo.add_argument("--beta-cost", type=float, default=0.025)
    demo.add_argument("--beta-parallel", type=float, default=0.01)

    replay = subparsers.add_parser("replay", help="replay a saved tree with a saved policy")
    replay.add_argument("tree", type=Path)
    replay.add_argument("policy", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "demo":
        result = run_demo(
            args.output,
            args.train,
            args.test,
            args.candidates,
            args.seed,
            args.beta_cost,
            args.beta_parallel,
        )
    else:
        result = replay_saved_tree(args.tree, args.policy)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
