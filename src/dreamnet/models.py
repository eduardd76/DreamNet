from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Incident:
    incident_id: str
    protocol: str
    root_cause: str
    target_branch: str
    severity: str
    symptoms: tuple[str, ...]
    branch_order: tuple[str, ...]


@dataclass(frozen=True)
class Node:
    node_id: str
    parent_id: str | None
    branch: str
    depth: int
    tool: str
    observation: str
    hypothesis: str
    diagnosis: str | None
    score: float
    cost: float = 1.0
    latency_ms: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Node:
        return cls(**value)


@dataclass
class DiscoveryTree:
    incident: Incident
    nodes: dict[str, Node] = field(default_factory=dict)
    children: dict[str, list[str]] = field(default_factory=dict)
    rounds: list[list[str]] = field(default_factory=list)

    ROOT_ID = "root"

    def __post_init__(self) -> None:
        if not self.nodes:
            self.nodes[self.ROOT_ID] = Node(
                node_id=self.ROOT_ID,
                parent_id=None,
                branch="root",
                depth=0,
                tool="incident_intake",
                observation="; ".join(self.incident.symptoms),
                hypothesis="Initial incident",
                diagnosis=None,
                score=0.0,
                cost=0.0,
                latency_ms=0,
            )
        self.children.setdefault(self.ROOT_ID, [])

    def add(self, node: Node) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"duplicate node: {node.node_id}")
        if node.parent_id not in self.nodes:
            raise ValueError(f"unknown parent: {node.parent_id}")
        self.nodes[node.node_id] = node
        self.children.setdefault(node.parent_id, []).append(node.node_id)
        self.children.setdefault(node.node_id, [])

    def leaves(self, revealed: set[str] | None = None) -> list[str]:
        visible = revealed if revealed is not None else set(self.nodes)
        result: list[str] = []
        for node_id in visible:
            if node_id == self.ROOT_ID:
                continue
            visible_children = [c for c in self.children.get(node_id, []) if c in visible]
            if not visible_children:
                result.append(node_id)
        return sorted(result)

    def eligible(self, revealed: set[str] | None = None) -> list[str]:
        return [self.ROOT_ID, *self.leaves(revealed)]

    def best_node(self, revealed: set[str] | None = None) -> Node:
        visible = revealed if revealed is not None else set(self.nodes)
        return max((self.nodes[n] for n in visible), key=lambda node: node.score)

    def non_root_count(self, revealed: set[str] | None = None) -> int:
        visible = revealed if revealed is not None else set(self.nodes)
        return len(visible - {self.ROOT_ID})

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident": {
                **asdict(self.incident),
                "symptoms": list(self.incident.symptoms),
                "branch_order": list(self.incident.branch_order),
            },
            "nodes": [self.nodes[k].to_dict() for k in sorted(self.nodes)],
            "rounds": self.rounds,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> DiscoveryTree:
        raw_incident = value["incident"]
        incident = Incident(
            **{
                **raw_incident,
                "symptoms": tuple(raw_incident["symptoms"]),
                "branch_order": tuple(raw_incident["branch_order"]),
            }
        )
        tree = cls(incident=incident)
        for raw_node in value["nodes"]:
            node = Node.from_dict(raw_node)
            if node.node_id != cls.ROOT_ID:
                tree.add(node)
        tree.rounds = value.get("rounds", [])
        return tree


@dataclass(frozen=True)
class PolicyConfig:
    name: str
    workers: int = 3
    min_branches: int = 3
    max_branches: int = 6
    max_nodes: int = 16
    refine_threshold: float = 0.30
    stop_threshold: float = 0.92
    root_priority: float = 0.40
    depth_penalty: float = 0.04
    evidence_weight: float = 1.0
    open_after_stall: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PolicyConfig:
        return cls(**value)


@dataclass(frozen=True)
class RunResult:
    tree: DiscoveryTree
    revealed: frozenset[str]
    rounds: int
    stopped_reason: str


@dataclass(frozen=True)
class Score:
    value: float
    quality: float
    requests: int
    rounds: int
    parallelism: float
    correct: bool
    diagnosis: str | None
