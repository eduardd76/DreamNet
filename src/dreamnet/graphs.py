from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class GraphEntity:
    entity_id: str
    kind: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphRelationship:
    source: str
    relation: str
    target: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeGraph:
    """Small in-memory property graph for network context and intended state."""

    entities: dict[str, GraphEntity] = field(default_factory=dict)
    relationships: list[GraphRelationship] = field(default_factory=list)

    def add_entity(self, entity: GraphEntity) -> None:
        existing = self.entities.get(entity.entity_id)
        if existing is not None and existing != entity:
            raise ValueError(f"conflicting entity: {entity.entity_id}")
        self.entities[entity.entity_id] = entity

    def add_relationship(self, relationship: GraphRelationship) -> None:
        if relationship.source not in self.entities:
            raise ValueError(f"unknown source: {relationship.source}")
        if relationship.target not in self.entities:
            raise ValueError(f"unknown target: {relationship.target}")
        if relationship not in self.relationships:
            self.relationships.append(relationship)

    def get(self, entity_id: str) -> GraphEntity:
        try:
            return self.entities[entity_id]
        except KeyError as error:
            raise KeyError(f"unknown knowledge-graph entity: {entity_id}") from error

    def related(self, source: str, relation: str | None = None) -> list[GraphEntity]:
        edges = [
            edge
            for edge in self.relationships
            if edge.source == source and (relation is None or edge.relation == relation)
        ]
        return [self.entities[edge.target] for edge in edges]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entities": [asdict(self.entities[key]) for key in sorted(self.entities)],
            "relationships": [asdict(edge) for edge in self.relationships],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> KnowledgeGraph:
        graph = cls()
        for raw in value.get("entities", []):
            graph.add_entity(GraphEntity(**raw))
        for raw in value.get("relationships", []):
            graph.add_relationship(GraphRelationship(**raw))
        return graph


@dataclass(frozen=True)
class ProcedureStep:
    step_id: str
    title: str
    branch: str
    tool: str | None
    device_role: str = "local"
    terminal_diagnosis: str | None = None
    estimated_cost: float = 1.0

    @property
    def terminal(self) -> bool:
        return self.terminal_diagnosis is not None


@dataclass(frozen=True)
class ProcedureTransition:
    source: str
    outcome: str
    target: str
    priority: float = 0.5


@dataclass
class ProceduralGraph:
    """Executable troubleshooting playbook with conditional transitions."""

    graph_id: str
    version: str
    start_step: str
    steps: dict[str, ProcedureStep] = field(default_factory=dict)
    transitions: list[ProcedureTransition] = field(default_factory=list)

    def add_step(self, step: ProcedureStep) -> None:
        if step.step_id in self.steps and self.steps[step.step_id] != step:
            raise ValueError(f"conflicting procedure step: {step.step_id}")
        self.steps[step.step_id] = step

    def add_transition(self, transition: ProcedureTransition) -> None:
        self.transitions.append(transition)

    def candidates(self, source: str, outcome: str) -> list[ProcedureTransition]:
        result = [
            edge for edge in self.transitions if edge.source == source and edge.outcome == outcome
        ]
        return sorted(result, key=lambda edge: edge.priority, reverse=True)

    def validate(self) -> None:
        if self.start_step not in self.steps:
            raise ValueError("start step is missing")
        for edge in self.transitions:
            if edge.source not in self.steps or edge.target not in self.steps:
                raise ValueError(f"transition references an unknown step: {edge}")
        for step in self.steps.values():
            if not step.terminal and step.tool is None:
                raise ValueError(f"non-terminal step has no tool: {step.step_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "version": self.version,
            "start_step": self.start_step,
            "steps": [asdict(self.steps[key]) for key in sorted(self.steps)],
            "transitions": [asdict(edge) for edge in self.transitions],
        }


@dataclass
class ExperienceGraph:
    """Property graph of executed diagnostic actions and validated outcomes."""

    vertices: dict[str, GraphEntity] = field(default_factory=dict)
    edges: list[GraphRelationship] = field(default_factory=list)
    _sequence: int = 0

    def record_execution(
        self,
        *,
        incident_id: str,
        procedure_id: str,
        procedure_version: str,
        step_id: str,
        device_id: str,
        tool: str,
        context_key: str,
        outcome: str,
        evidence: str,
        raw_output: str,
        confidence: float,
        latency_ms: int,
        cost: float,
        diagnosis: str | None,
    ) -> str:
        self._sequence += 1
        execution_id = f"execution:{incident_id}:{self._sequence:04d}"
        incident_vertex = f"incident:{incident_id}"
        step_vertex = f"procedure-step:{procedure_id}:{procedure_version}:{step_id}"
        device_vertex = f"device:{device_id}"
        evidence_vertex = f"evidence:{incident_id}:{self._sequence:04d}"
        raw_digest = hashlib.sha256(raw_output.encode("utf-8")).hexdigest()

        self._upsert(GraphEntity(incident_vertex, "incident", {"incident_id": incident_id}))
        self._upsert(GraphEntity(step_vertex, "procedure_step", {"step_id": step_id}))
        self._upsert(GraphEntity(device_vertex, "device", {"name": device_id}))
        self._upsert(
            GraphEntity(
                evidence_vertex,
                "evidence",
                {
                    "summary": evidence,
                    "outcome": outcome,
                    "confidence": confidence,
                    "raw_sha256": raw_digest,
                },
            )
        )
        self._upsert(
            GraphEntity(
                execution_id,
                "execution",
                {
                    "tool": tool,
                    "context_key": context_key,
                    "latency_ms": latency_ms,
                    "cost": cost,
                    "diagnosis": diagnosis,
                    "resolved": diagnosis is not None,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
        )
        self._link(incident_vertex, "HAS_EXECUTION", execution_id)
        self._link(execution_id, "USED_STEP", step_vertex)
        self._link(execution_id, "TARGETED", device_vertex)
        self._link(execution_id, "PRODUCED", evidence_vertex)
        if diagnosis is not None:
            diagnosis_id = f"diagnosis:{diagnosis}"
            self._upsert(GraphEntity(diagnosis_id, "diagnosis", {"name": diagnosis}))
            self._link(evidence_vertex, "SUPPORTS", diagnosis_id)
        return execution_id

    def step_statistics(self, step_id: str, context_key: str | None = None) -> dict[str, float]:
        executions: list[GraphEntity] = []
        for edge in self.edges:
            if edge.relation != "USED_STEP":
                continue
            step = self.vertices[edge.target]
            if step.properties.get("step_id") != step_id:
                continue
            execution = self.vertices[edge.source]
            if context_key is not None and execution.properties.get("context_key") != context_key:
                continue
            executions.append(execution)
        if not executions and context_key is not None:
            return self.step_statistics(step_id)
        if not executions:
            return {"count": 0.0, "resolution_rate": 0.0, "mean_latency_ms": 0.0, "mean_cost": 0.0}
        return {
            "count": float(len(executions)),
            "resolution_rate": mean(bool(e.properties["resolved"]) for e in executions),
            "mean_latency_ms": mean(float(e.properties["latency_ms"]) for e in executions),
            "mean_cost": mean(float(e.properties["cost"]) for e in executions),
        }

    def _upsert(self, entity: GraphEntity) -> None:
        existing = self.vertices.get(entity.entity_id)
        if existing is not None and existing != entity:
            if existing.kind in {"incident", "procedure_step", "device", "diagnosis"}:
                return
            raise ValueError(f"conflicting experience vertex: {entity.entity_id}")
        self.vertices[entity.entity_id] = entity

    def _link(self, source: str, relation: str, target: str) -> None:
        edge = GraphRelationship(source, relation, target)
        if edge not in self.edges:
            self.edges.append(edge)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vertices": [asdict(self.vertices[key]) for key in sorted(self.vertices)],
            "edges": [asdict(edge) for edge in self.edges],
            "sequence": self._sequence,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ExperienceGraph:
        graph = cls(_sequence=int(value.get("sequence", 0)))
        graph.vertices = {raw["entity_id"]: GraphEntity(**raw) for raw in value.get("vertices", [])}
        graph.edges = [GraphRelationship(**raw) for raw in value.get("edges", [])]
        return graph

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> ExperienceGraph:
        if not path.exists():
            return cls()
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
