from __future__ import annotations

from .models import DiscoveryTree, PolicyConfig, RunResult, Score
from .policy import ExplorationPolicy


def replay_tree(tree: DiscoveryTree, config: PolicyConfig, max_rounds: int = 12) -> RunResult:
    """Replay with the exact recorded-child semantics from Dream-RSI section 3."""
    policy = ExplorationPolicy(config)
    revealed = {tree.ROOT_ID}
    replay_rounds: list[list[str]] = []
    reason = "round_limit"

    for _ in range(max_rounds):
        selected = policy.select(tree, revealed)
        if not selected:
            reason = "policy_stop"
            break
        newly_revealed: list[str] = []
        for parent_id in selected:
            children = tree.children.get(parent_id, [])
            child = next((node_id for node_id in children if node_id not in revealed), None)
            if child is not None:
                revealed.add(child)
                newly_revealed.append(child)
        if not newly_revealed:
            reason = "exhausted"
            break
        replay_rounds.append(newly_revealed)
        if revealed == set(tree.nodes):
            reason = "fully_revealed"
            break

    replay_view = DiscoveryTree.from_dict(tree.to_dict())
    replay_view.rounds = replay_rounds
    return RunResult(
        tree=replay_view,
        revealed=frozenset(revealed),
        rounds=len(replay_rounds),
        stopped_reason=reason,
    )


def score_result(result: RunResult, beta_cost: float = 0.025, beta_parallel: float = 0.01) -> Score:
    tree = result.tree
    best = tree.best_node(set(result.revealed))
    requests = tree.non_root_count(set(result.revealed))
    parallelism = requests / max(1, result.rounds)
    value = best.score - beta_cost * requests + beta_parallel * parallelism
    correct = best.diagnosis == tree.incident.root_cause
    return Score(
        value=value,
        quality=best.score,
        requests=requests,
        rounds=result.rounds,
        parallelism=parallelism,
        correct=correct,
        diagnosis=best.diagnosis,
    )
