from __future__ import annotations

import json
from pathlib import Path

from .environment import NetworkEnvironment
from .models import DiscoveryTree, PolicyConfig
from .optimizer import evaluate_policy, optimize_policy
from .policy import baseline_policy
from .replay import score_result
from .reporting import aggregate, result_trace, write_demo_report, write_json
from .rollout import online_rollout


def run_demo(
    output_dir: Path,
    train_count: int = 84,
    test_count: int = 42,
    candidates: int = 400,
    seed: int = 7,
    beta_cost: float = 0.025,
    beta_parallel: float = 0.01,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline = baseline_policy()

    train_env = NetworkEnvironment(seed=seed)
    train_incidents = train_env.generate_incidents(train_count, "train")
    train_results = [online_rollout(i, train_env, baseline) for i in train_incidents]
    train_trees = [result.tree for result in train_results]
    for tree in train_trees:
        write_json(output_dir / "trees" / f"{tree.incident.incident_id}.json", tree.to_dict())

    learned, leaderboard = optimize_policy(
        baseline,
        train_trees,
        candidates=candidates,
        seed=seed + 1,
        beta_cost=beta_cost,
        beta_parallel=beta_parallel,
    )
    write_json(output_dir / "learned_policy.json", learned.to_dict())
    write_json(output_dir / "leaderboard.json", leaderboard[:50])

    _, baseline_replay_scores = evaluate_policy(
        baseline, train_trees, beta_cost, beta_parallel
    )
    _, learned_replay_scores = evaluate_policy(
        learned, train_trees, beta_cost, beta_parallel
    )

    test_env_a = NetworkEnvironment(seed=seed + 100)
    test_incidents_a = test_env_a.generate_incidents(test_count, "test")
    online_baseline_results = [online_rollout(i, test_env_a, baseline) for i in test_incidents_a]
    online_baseline_scores = [
        score_result(result, beta_cost, beta_parallel) for result in online_baseline_results
    ]

    # Generate the identical incident distribution in an independent environment for fair comparison.
    test_env_b = NetworkEnvironment(seed=seed + 100)
    test_incidents_b = test_env_b.generate_incidents(test_count, "test")
    online_learned_results = [online_rollout(i, test_env_b, learned) for i in test_incidents_b]
    online_learned_scores = [
        score_result(result, beta_cost, beta_parallel) for result in online_learned_results
    ]

    metrics = {
        "replay_train": {
            "baseline": aggregate(baseline_replay_scores),
            "learned": aggregate(learned_replay_scores),
        },
        "online_holdout": {
            "baseline": aggregate(online_baseline_scores),
            "learned": aggregate(online_learned_scores),
        },
    }
    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "sample_baseline_trace.json", result_trace(online_baseline_results[0]))
    write_json(output_dir / "sample_learned_trace.json", result_trace(online_learned_results[0]))
    write_demo_report(
        output_dir / "report.md",
        baseline,
        learned,
        metrics["replay_train"]["baseline"],
        metrics["replay_train"]["learned"],
        metrics["online_holdout"]["baseline"],
        metrics["online_holdout"]["learned"],
    )
    return {
        "objective": {"beta_cost": beta_cost, "beta_parallel": beta_parallel},
        "baseline": baseline.to_dict(),
        "learned": learned.to_dict(),
        "metrics": metrics,
    }


def replay_saved_tree(tree_path: Path, policy_path: Path) -> dict[str, object]:
    from .replay import replay_tree

    tree = DiscoveryTree.from_dict(json.loads(tree_path.read_text(encoding="utf-8")))
    policy = PolicyConfig.from_dict(json.loads(policy_path.read_text(encoding="utf-8")))
    result = replay_tree(tree, policy)
    return {
        "score": score_result(result).__dict__,
        "trace": result_trace(result),
        "stopped_reason": result.stopped_reason,
    }
