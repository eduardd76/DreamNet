from __future__ import annotations

import random
from dataclasses import replace
from statistics import mean

from .models import DiscoveryTree, PolicyConfig, Score
from .replay import replay_tree, score_result


def evaluate_policy(
    config: PolicyConfig,
    trees: list[DiscoveryTree],
    beta_cost: float = 0.025,
    beta_parallel: float = 0.01,
) -> tuple[float, list[Score]]:
    scores = [score_result(replay_tree(tree, config), beta_cost, beta_parallel) for tree in trees]
    return mean(score.value for score in scores), scores


def _mutate(parent: PolicyConfig, rng: random.Random, index: int) -> PolicyConfig:
    choices = {
        "workers": rng.choice([1, 2, 3, 4]),
        "min_branches": rng.choice([1, 2, 3, 4, 5]),
        "max_branches": rng.choice([3, 4, 5, 6]),
        "max_nodes": rng.choice([6, 8, 10, 12, 15, 18]),
        "refine_threshold": rng.choice([0.10, 0.20, 0.30, 0.40, 0.47, 0.55]),
        "stop_threshold": rng.choice([0.76, 0.90, 0.95, 0.99, 1.01]),
        "root_priority": rng.choice([0.15, 0.30, 0.45, 0.60, 0.80]),
        "depth_penalty": rng.choice([0.0, 0.02, 0.05, 0.08, 0.12]),
        "evidence_weight": rng.choice([0.8, 1.0, 1.25, 1.5]),
        "open_after_stall": rng.choice([True, False]),
    }
    keys = rng.sample(list(choices), k=rng.choice([2, 3, 4]))
    updates = {key: choices[key] for key in keys}
    candidate = replace(parent, name=f"dream_candidate_{index:04d}", **updates)
    if candidate.min_branches > candidate.max_branches:
        candidate = replace(candidate, min_branches=candidate.max_branches)
    return candidate


def optimize_policy(
    initial: PolicyConfig,
    trees: list[DiscoveryTree],
    candidates: int = 400,
    seed: int = 11,
    beta_cost: float = 0.025,
    beta_parallel: float = 0.01,
) -> tuple[PolicyConfig, list[dict[str, float | str | int]]]:
    """Evolutionary policy-code search standing in for the paper's policy LLM."""
    rng = random.Random(seed)
    best = initial
    best_value, best_scores = evaluate_policy(best, trees, beta_cost, beta_parallel)
    leaderboard: list[dict[str, float | str | int]] = [_summary(best, best_value, best_scores)]

    elites: list[PolicyConfig] = [initial]
    for index in range(candidates):
        parent = rng.choice(elites[-12:])
        candidate = _mutate(parent, rng, index)
        value, scores = evaluate_policy(candidate, trees, beta_cost, beta_parallel)
        leaderboard.append(_summary(candidate, value, scores))
        if value > best_value:
            best, best_value, best_scores = candidate, value, scores
            elites.append(best)

    leaderboard.sort(key=lambda row: float(row["objective"]), reverse=True)
    best = replace(best, name="dreamnet_learned")
    return best, leaderboard


def _summary(
    config: PolicyConfig, value: float, scores: list[Score]
) -> dict[str, float | str | int]:
    return {
        "policy": config.name,
        "objective": round(value, 6),
        "accuracy": round(mean(s.correct for s in scores), 6),
        "quality": round(mean(s.quality for s in scores), 6),
        "requests": round(mean(s.requests for s in scores), 6),
        "rounds": round(mean(s.rounds for s in scores), 6),
    }
