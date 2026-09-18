from __future__ import annotations

import random
from dataclasses import dataclass, field

from .catalog import BRANCHES, FAULTS, GENERIC_TOOLS, Fault
from .models import DiscoveryTree, Incident, Node


@dataclass
class NetworkEnvironment:
    """Frozen incident generator, discovery agent, and deterministic evaluator."""

    seed: int = 7
    rng: random.Random = field(init=False)
    _fault_by_incident: dict[str, Fault] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    def generate_incidents(self, count: int, prefix: str) -> list[Incident]:
        incidents: list[Incident] = []
        for index in range(count):
            fault = FAULTS[index % len(FAULTS)]
            order = list(BRANCHES)
            self.rng.shuffle(order)
            incident = Incident(
                incident_id=f"{prefix}-{index:03d}",
                protocol=fault.protocol,
                root_cause=fault.root_cause,
                target_branch=fault.branch,
                severity=fault.severity,
                symptoms=fault.symptoms,
                branch_order=tuple(order),
            )
            self._fault_by_incident[incident.incident_id] = fault
            incidents.append(incident)
        return incidents

    def register(self, incident: Incident) -> None:
        match = next(
            f for f in FAULTS
            if f.protocol == incident.protocol and f.root_cause == incident.root_cause
        )
        self._fault_by_incident[incident.incident_id] = match

    def expand(self, tree: DiscoveryTree, parent_id: str) -> Node | None:
        fault = self._fault_by_incident[tree.incident.incident_id]
        if parent_id == tree.ROOT_ID:
            opened = {tree.nodes[node_id].branch for node_id in tree.children[tree.ROOT_ID]}
            branch = next((b for b in tree.incident.branch_order if b not in opened), None)
            if branch is None:
                return None
            depth = 1
        else:
            parent = tree.nodes[parent_id]
            branch = parent.branch
            depth = parent.depth + 1
            if depth > 3:
                return None

        node_id = f"n{len(tree.nodes):03d}"
        if branch == fault.branch:
            tool = fault.tools[depth - 1]
            observation = fault.observations[depth - 1]
            scores = (0.48, 0.78, 1.00)
            score = scores[depth - 1]
            diagnosis = fault.root_cause if depth == 3 else None
            hypothesis = f"Evidence supports {fault.root_cause.replace('_', ' ')}"
        else:
            tool = GENERIC_TOOLS[branch][depth - 1]
            observation = self._negative_observation(branch, depth)
            score = (0.10, 0.16, 0.20)[depth - 1]
            diagnosis = None
            hypothesis = f"No decisive evidence in {branch} branch"

        latency = 60 + 35 * depth + (17 * len(branch)) % 80
        return Node(
            node_id=node_id,
            parent_id=parent_id,
            branch=branch,
            depth=depth,
            tool=tool,
            observation=observation,
            hypothesis=hypothesis,
            diagnosis=diagnosis,
            score=score,
            latency_ms=latency,
        )

    @staticmethod
    def _negative_observation(branch: str, depth: int) -> str:
        messages = {
            "transport": ("Peer is reachable", "Path is stable", "No transport fault found"),
            "session": ("Session parameters appear normal", "No protocol error", "Session branch cleared"),
            "policy": ("Policy permits sampled routes", "No deny match", "Policy branch cleared"),
            "routing": ("RIB state is consistent", "Next hops resolve", "Routing branch cleared"),
            "changes": ("No correlated recent change", "Diff is unrelated", "Change branch cleared"),
            "platform": ("Processes are healthy", "Resources are normal", "Platform branch cleared"),
        }
        return messages[branch][depth - 1]
