from __future__ import annotations

from dataclasses import dataclass

from .models import DiscoveryTree, PolicyConfig


@dataclass
class PolicyState:
    last_best: float = 0.0
    stalled_rounds: int = 0


class ExplorationPolicy:
    def __init__(self, config: PolicyConfig):
        self.config = config
        self.state = PolicyState()

    def reset(self) -> None:
        self.state = PolicyState()

    def select(self, tree: DiscoveryTree, revealed: set[str]) -> list[str]:
        cfg = self.config
        best = tree.best_node(revealed).score
        count = tree.non_root_count(revealed)
        root_children = sum(1 for n in revealed if tree.nodes[n].parent_id == tree.ROOT_ID)

        if best > self.state.last_best + 1e-9:
            self.state.stalled_rounds = 0
        else:
            self.state.stalled_rounds += 1
        self.state.last_best = best

        if best >= cfg.stop_threshold or count >= cfg.max_nodes:
            return []

        candidates: list[tuple[float, str]] = []
        for node_id in tree.leaves(revealed):
            node = tree.nodes[node_id]
            if node.depth >= 3:
                continue
            value = cfg.evidence_weight * node.score - cfg.depth_penalty * node.depth
            if node.score >= cfg.refine_threshold:
                value += 0.35
            candidates.append((value, node_id))

        can_open = root_children < cfg.max_branches
        must_open = root_children < cfg.min_branches
        if can_open:
            root_value = cfg.root_priority
            if must_open:
                root_value += 1.0
            if cfg.open_after_stall and self.state.stalled_rounds > 0:
                root_value += 0.25
            candidates.append((root_value, tree.ROOT_ID))

        candidates.sort(key=lambda item: (item[0], item[1] == tree.ROOT_ID), reverse=True)
        return [node_id for _, node_id in candidates[: cfg.workers]]


def baseline_policy() -> PolicyConfig:
    """Broad fixed exploration: deliberately safe but expensive."""
    return PolicyConfig(
        name="fixed_parallel",
        workers=3,
        min_branches=6,
        max_branches=6,
        max_nodes=18,
        refine_threshold=0.0,
        stop_threshold=1.01,
        root_priority=0.65,
        depth_penalty=0.0,
        evidence_weight=1.0,
        open_after_stall=True,
    )
