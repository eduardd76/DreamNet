from __future__ import annotations

from .environment import NetworkEnvironment
from .models import DiscoveryTree, Incident, PolicyConfig, RunResult
from .policy import ExplorationPolicy


def online_rollout(
    incident: Incident,
    environment: NetworkEnvironment,
    config: PolicyConfig,
    max_rounds: int = 12,
) -> RunResult:
    tree = DiscoveryTree(incident=incident)
    policy = ExplorationPolicy(config)
    revealed = {tree.ROOT_ID}
    reason = "round_limit"

    for _ in range(max_rounds):
        selected = policy.select(tree, revealed)
        if not selected:
            reason = "policy_stop"
            break
        created: list[str] = []
        for parent_id in selected:
            node = environment.expand(tree, parent_id)
            if node is not None:
                tree.add(node)
                revealed.add(node.node_id)
                created.append(node.node_id)
        if not created:
            reason = "exhausted"
            break
        tree.rounds.append(created)
    return RunResult(
        tree=tree,
        revealed=frozenset(revealed),
        rounds=len(tree.rounds),
        stopped_reason=reason,
    )
