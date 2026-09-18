from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bgp_demo import fixture_suite, live_run
from .demo import replay_saved_tree, run_demo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dreamnet")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser(
        "demo", help="run online collection, dreaming, and holdout evaluation"
    )
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

    bgp_demo = subparsers.add_parser(
        "bgp-demo", help="run the BGP procedural graph against deterministic fixtures"
    )
    bgp_demo.add_argument("--fixtures", type=Path, default=Path("examples/fixtures"))
    bgp_demo.add_argument("--output", type=Path, default=Path("artifacts/bgp-demo"))

    bgp_run = subparsers.add_parser(
        "bgp-run", help="run the BGP procedural graph against a live FRR Containerlab"
    )
    bgp_run.add_argument("--live", action="store_true", required=True)
    bgp_run.add_argument("--incident", required=True)
    bgp_run.add_argument("--expected-prefix", default="192.0.2.1/32")
    bgp_run.add_argument("--lab-prefix", default="clab-dreamnet-bgp")
    bgp_run.add_argument("--output", type=Path, default=Path("artifacts/bgp-live"))
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
    elif args.command == "replay":
        result = replay_saved_tree(args.tree, args.policy)
    elif args.command == "bgp-demo":
        result = fixture_suite(args.fixtures, args.output)
    else:
        result = live_run(
            incident_id=args.incident,
            expected_prefix=args.expected_prefix,
            output=args.output,
            lab_prefix=args.lab_prefix,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
