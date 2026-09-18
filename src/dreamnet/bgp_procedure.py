from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Protocol

from .adapters import ToolAdapter, ToolResult
from .graphs import (
    ExperienceGraph,
    GraphEntity,
    GraphRelationship,
    KnowledgeGraph,
    ProceduralGraph,
    ProcedureStep,
    ProcedureTransition,
)


@dataclass(frozen=True)
class BGPIncidentContext:
    incident_id: str
    session_id: str
    expected_prefix: str
    symptoms: tuple[str, ...] = ()


@dataclass(frozen=True)
class StepEvaluation:
    outcome: str
    evidence: str
    confidence: float
    hypothesis: str
    diagnosis: str | None = None


@dataclass(frozen=True)
class ExecutedStep:
    step_id: str
    title: str
    device: str
    tool: str
    params: dict[str, str]
    outcome: str
    evidence: str
    confidence: float
    latency_ms: int
    diagnosis: str | None


@dataclass(frozen=True)
class ProcedureRun:
    incident_id: str
    diagnosis: str | None
    status: str
    steps: tuple[ExecutedStep, ...]
    context_key: str

    def to_dict(self) -> dict[str, object]:
        return {
            "incident_id": self.incident_id,
            "diagnosis": self.diagnosis,
            "status": self.status,
            "context_key": self.context_key,
            "steps": [asdict(step) for step in self.steps],
        }


class NavigationPolicy(Protocol):
    def choose(
        self,
        transitions: Sequence[ProcedureTransition],
        procedure: ProceduralGraph,
        experience: ExperienceGraph,
        context_key: str,
        visited: set[str],
    ) -> ProcedureTransition: ...


class FixedNavigationPolicy:
    def choose(
        self,
        transitions: Sequence[ProcedureTransition],
        procedure: ProceduralGraph,
        experience: ExperienceGraph,
        context_key: str,
        visited: set[str],
    ) -> ProcedureTransition:
        del procedure, experience, context_key, visited
        return max(transitions, key=lambda edge: edge.priority)


class ExperienceNavigationPolicy:
    """Prefer historically useful steps while retaining the authored graph priority."""

    def choose(
        self,
        transitions: Sequence[ProcedureTransition],
        procedure: ProceduralGraph,
        experience: ExperienceGraph,
        context_key: str,
        visited: set[str],
    ) -> ProcedureTransition:
        del visited

        def score(edge: ProcedureTransition) -> tuple[float, float]:
            step = procedure.steps[edge.target]
            stats = experience.step_statistics(step.step_id, context_key)
            learned_value = (
                1.5 * stats["resolution_rate"]
                - 0.05 * stats["mean_cost"]
                - 0.0001 * stats["mean_latency_ms"]
            )
            evidence_weight = min(1.0, stats["count"] / 5.0)
            return edge.priority + evidence_weight * learned_value, edge.priority

        return max(transitions, key=score)


def build_bgp_procedural_graph() -> ProceduralGraph:
    graph = ProceduralGraph(
        graph_id="bgp-session-and-route-troubleshooting",
        version="0.2.0",
        start_step="bgp_summary",
    )
    steps = (
        ProcedureStep("bgp_summary", "Inspect BGP session state", "session", "show_bgp_summary"),
        ProcedureStep(
            "interface_state", "Inspect peer-facing interface", "transport", "show_interface"
        ),
        ProcedureStep("peer_reachability", "Test peer reachability", "transport", "ping_peer"),
        ProcedureStep("firewall_policy", "Inspect TCP/179 filtering", "security", "show_firewall"),
        ProcedureStep(
            "peer_configuration",
            "Compare BGP peer configuration",
            "configuration",
            "show_running_config",
        ),
        ProcedureStep(
            "route_presence",
            "Check expected BGP prefix",
            "routing",
            "show_bgp_route",
            device_role="remote",
        ),
        ProcedureStep(
            "export_policy", "Inspect outbound BGP policy", "policy", "show_running_config"
        ),
        ProcedureStep(
            "diagnosed_interface_down",
            "Interface failure proven",
            "terminal",
            None,
            terminal_diagnosis="interface_down",
        ),
        ProcedureStep(
            "diagnosed_peer_unreachable",
            "Peer transport failure proven",
            "terminal",
            None,
            terminal_diagnosis="peer_unreachable",
        ),
        ProcedureStep(
            "diagnosed_tcp_blocked",
            "TCP/179 filtering proven",
            "terminal",
            None,
            terminal_diagnosis="tcp_179_blocked",
        ),
        ProcedureStep(
            "diagnosed_asn_mismatch",
            "Remote AS mismatch proven",
            "terminal",
            None,
            terminal_diagnosis="asn_mismatch",
        ),
        ProcedureStep(
            "diagnosed_neighbor_shutdown",
            "Administrative shutdown proven",
            "terminal",
            None,
            terminal_diagnosis="neighbor_shutdown",
        ),
        ProcedureStep(
            "diagnosed_route_filter",
            "Export policy filtering proven",
            "terminal",
            None,
            terminal_diagnosis="route_map_filter",
        ),
        ProcedureStep(
            "healthy",
            "Expected BGP state verified",
            "terminal",
            None,
            terminal_diagnosis="no_fault_detected",
        ),
        ProcedureStep(
            "escalate", "Evidence is insufficient", "terminal", None, terminal_diagnosis="escalate"
        ),
    )
    for step in steps:
        graph.add_step(step)
    transitions = (
        ProcedureTransition("bgp_summary", "not_established", "interface_state", 1.0),
        ProcedureTransition("bgp_summary", "established", "route_presence", 1.0),
        ProcedureTransition("bgp_summary", "unavailable", "escalate", 1.0),
        ProcedureTransition("interface_state", "down", "diagnosed_interface_down", 1.0),
        ProcedureTransition("interface_state", "up", "peer_reachability", 1.0),
        ProcedureTransition("interface_state", "unavailable", "escalate", 1.0),
        ProcedureTransition("peer_reachability", "unreachable", "diagnosed_peer_unreachable", 1.0),
        ProcedureTransition("peer_reachability", "reachable", "firewall_policy", 0.60),
        ProcedureTransition("peer_reachability", "reachable", "peer_configuration", 0.55),
        ProcedureTransition("firewall_policy", "blocked", "diagnosed_tcp_blocked", 1.0),
        ProcedureTransition("firewall_policy", "clear", "peer_configuration", 0.9),
        ProcedureTransition("firewall_policy", "clear", "escalate", 0.1),
        ProcedureTransition("firewall_policy", "unavailable", "peer_configuration", 0.9),
        ProcedureTransition("firewall_policy", "unavailable", "escalate", 0.1),
        ProcedureTransition("peer_configuration", "asn_mismatch", "diagnosed_asn_mismatch", 1.0),
        ProcedureTransition("peer_configuration", "shutdown", "diagnosed_neighbor_shutdown", 1.0),
        ProcedureTransition("peer_configuration", "matched", "firewall_policy", 0.8),
        ProcedureTransition("peer_configuration", "matched", "escalate", 0.1),
        ProcedureTransition("peer_configuration", "unavailable", "firewall_policy", 0.8),
        ProcedureTransition("peer_configuration", "unavailable", "escalate", 0.1),
        ProcedureTransition("route_presence", "present", "healthy", 1.0),
        ProcedureTransition("route_presence", "missing", "export_policy", 1.0),
        ProcedureTransition("route_presence", "unavailable", "escalate", 1.0),
        ProcedureTransition("export_policy", "filtering", "diagnosed_route_filter", 1.0),
        ProcedureTransition("export_policy", "clear", "escalate", 1.0),
    )
    for transition in transitions:
        graph.add_transition(transition)
    graph.validate()
    return graph


def build_lab_knowledge_graph() -> KnowledgeGraph:
    graph = KnowledgeGraph()
    entities = (
        GraphEntity("device:r1", "device", {"name": "r1", "asn": 65001, "router_id": "1.1.1.1"}),
        GraphEntity("device:r2", "device", {"name": "r2", "asn": 65002, "router_id": "2.2.2.2"}),
        GraphEntity("device:r3", "device", {"name": "r3", "asn": 65003, "router_id": "3.3.3.3"}),
        GraphEntity("interface:r1:eth1", "interface", {"name": "eth1", "ipv4": "10.0.12.1/30"}),
        GraphEntity("interface:r2:eth1", "interface", {"name": "eth1", "ipv4": "10.0.12.2/30"}),
        GraphEntity("interface:r2:eth2", "interface", {"name": "eth2", "ipv4": "10.0.23.1/30"}),
        GraphEntity("interface:r3:eth1", "interface", {"name": "eth1", "ipv4": "10.0.23.2/30"}),
        GraphEntity(
            "bgp-session:r1:r2",
            "bgp_session",
            {
                "local_device": "r1",
                "remote_device": "r2",
                "local_as": 65001,
                "remote_as": 65002,
                "peer_ip": "10.0.12.2",
                "local_interface": "eth1",
            },
        ),
        GraphEntity(
            "policy:r1:export",
            "routing_policy",
            {"name": "r1-export", "direction": "out", "recently_changed": False},
        ),
    )
    for entity in entities:
        graph.add_entity(entity)
    relationships = (
        GraphRelationship("device:r1", "HAS_INTERFACE", "interface:r1:eth1"),
        GraphRelationship("device:r2", "HAS_INTERFACE", "interface:r2:eth1"),
        GraphRelationship("device:r2", "HAS_INTERFACE", "interface:r2:eth2"),
        GraphRelationship("device:r3", "HAS_INTERFACE", "interface:r3:eth1"),
        GraphRelationship("device:r1", "HAS_BGP_SESSION", "bgp-session:r1:r2"),
        GraphRelationship("bgp-session:r1:r2", "REMOTE_DEVICE", "device:r2"),
        GraphRelationship("bgp-session:r1:r2", "USES_INTERFACE", "interface:r1:eth1"),
        GraphRelationship("bgp-session:r1:r2", "GOVERNED_BY", "policy:r1:export"),
    )
    for relationship in relationships:
        graph.add_relationship(relationship)
    return graph


class BGPEvidenceEvaluator:
    def evaluate(
        self,
        step: ProcedureStep,
        result: ToolResult,
        knowledge: KnowledgeGraph,
        incident: BGPIncidentContext,
    ) -> StepEvaluation:
        session = knowledge.get(incident.session_id).properties
        evaluators = {
            "bgp_summary": self._summary,
            "interface_state": self._interface,
            "peer_reachability": self._reachability,
            "firewall_policy": self._firewall,
            "peer_configuration": self._peer_config,
            "route_presence": self._route_presence,
            "export_policy": self._export_policy,
        }
        return evaluators[step.step_id](result, session, incident)

    @staticmethod
    def _summary(
        result: ToolResult, session: Mapping[str, object], incident: BGPIncidentContext
    ) -> StepEvaluation:
        del incident
        if result.returncode != 0:
            return StepEvaluation(
                "unavailable", "BGP summary command failed", 0.0, "No reliable session evidence"
            )
        state = _find_peer_state(result.stdout, str(session["peer_ip"]))
        if not state:
            return StepEvaluation(
                "unavailable",
                "Peer state was absent or unparseable",
                0.0,
                "No reliable session evidence",
            )
        if state.lower() == "established":
            return StepEvaluation(
                "established", "BGP session is Established", 0.99, "Session is operational"
            )
        return StepEvaluation(
            "not_established",
            f"BGP peer state is {state or 'unknown'}",
            0.95 if state else 0.4,
            "The failure is in session establishment",
        )

    @staticmethod
    def _interface(
        result: ToolResult, session: Mapping[str, object], incident: BGPIncidentContext
    ) -> StepEvaluation:
        del session, incident
        operstate = "unknown"
        try:
            value = json.loads(result.stdout)
            record = value[0] if isinstance(value, list) else value
            operstate = str(record.get("operstate", "unknown")).lower()
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        if result.returncode != 0 or operstate == "unknown":
            return StepEvaluation(
                "unavailable",
                "Interface state command failed or was unparseable",
                0.0,
                "No reliable interface evidence",
            )
        if operstate in {"down", "lowerlayerdown", "notpresent"}:
            return StepEvaluation(
                "down",
                f"Interface operstate is {operstate}",
                1.0,
                "Physical/interface failure",
                "interface_down",
            )
        return StepEvaluation(
            "up", f"Interface operstate is {operstate}", 0.95, "Interface is not the root cause"
        )

    @staticmethod
    def _reachability(
        result: ToolResult, session: Mapping[str, object], incident: BGPIncidentContext
    ) -> StepEvaluation:
        del session, incident
        if result.returncode == 0:
            return StepEvaluation(
                "reachable", "Peer responds to ICMP", 0.95, "IP transport is available"
            )
        return StepEvaluation(
            "unreachable",
            "Peer does not respond to ICMP",
            0.8,
            "Peer transport failure",
            "peer_unreachable",
        )

    @staticmethod
    def _firewall(
        result: ToolResult, session: Mapping[str, object], incident: BGPIncidentContext
    ) -> StepEvaluation:
        del session, incident
        if result.returncode != 0:
            return StepEvaluation(
                "unavailable",
                "Firewall state could not be collected",
                0.0,
                "Firewall evidence is unavailable",
            )
        blocked = bool(
            re.search(r"(?:--dport|dpt:)\s*179.*(?:DROP|REJECT)", result.stdout, re.IGNORECASE)
        )
        if blocked:
            return StepEvaluation(
                "blocked",
                "A firewall rule blocks TCP/179",
                0.98,
                "BGP transport is filtered",
                "tcp_179_blocked",
            )
        return StepEvaluation(
            "clear", "No TCP/179 deny rule was found", 0.75, "Firewall policy is not yet implicated"
        )

    @staticmethod
    def _peer_config(
        result: ToolResult, session: Mapping[str, object], incident: BGPIncidentContext
    ) -> StepEvaluation:
        del incident
        if result.returncode != 0:
            return StepEvaluation(
                "unavailable",
                "Running configuration could not be collected",
                0.0,
                "Peer configuration evidence is unavailable",
            )
        peer_ip = re.escape(str(session["peer_ip"]))
        expected_as = int(session["remote_as"])
        shutdown = re.search(rf"neighbor\s+{peer_ip}\s+shutdown", result.stdout) is not None
        if shutdown:
            return StepEvaluation(
                "shutdown",
                "Neighbor is administratively shut down",
                1.0,
                "BGP neighbor is disabled",
                "neighbor_shutdown",
            )
        match = re.search(rf"neighbor\s+{peer_ip}\s+remote-as\s+(\d+)", result.stdout)
        configured_as = int(match.group(1)) if match else None
        if configured_as is None:
            return StepEvaluation(
                "unavailable",
                "Expected neighbor remote-AS statement was not found",
                0.2,
                "Peer configuration is incomplete or unparseable",
            )
        if configured_as is not None and configured_as != expected_as:
            return StepEvaluation(
                "asn_mismatch",
                f"Configured remote AS {configured_as} differs from intended AS {expected_as}",
                1.0,
                "BGP OPEN messages use inconsistent ASNs",
                "asn_mismatch",
            )
        return StepEvaluation(
            "matched",
            "Peer ASN and administrative state match intent",
            0.9,
            "Peer configuration is consistent",
        )

    @staticmethod
    def _route_presence(
        result: ToolResult, session: Mapping[str, object], incident: BGPIncidentContext
    ) -> StepEvaluation:
        del session
        if result.returncode != 0:
            return StepEvaluation(
                "unavailable",
                "BGP route query failed",
                0.0,
                "Route presence cannot be determined",
            )
        if incident.expected_prefix in result.stdout and result.returncode == 0:
            return StepEvaluation(
                "present",
                f"Prefix {incident.expected_prefix} is present",
                0.98,
                "Expected route is available",
            )
        return StepEvaluation(
            "missing",
            f"Prefix {incident.expected_prefix} is absent",
            0.95,
            "Export or import policy may filter the route",
        )

    @staticmethod
    def _export_policy(
        result: ToolResult, session: Mapping[str, object], incident: BGPIncidentContext
    ) -> StepEvaluation:
        peer_ip = re.escape(str(session["peer_ip"]))
        attached = re.search(rf"neighbor\s+{peer_ip}\s+route-map\s+(\S+)\s+out", result.stdout)
        if attached:
            route_map = re.escape(attached.group(1))
            deny = re.search(rf"route-map\s+{route_map}\s+deny", result.stdout)
            if deny:
                return StepEvaluation(
                    "filtering",
                    f"Outbound route-map {attached.group(1)} contains a deny path",
                    0.9,
                    f"Export policy filters {incident.expected_prefix}",
                    "route_map_filter",
                )
        return StepEvaluation(
            "clear",
            "No deterministic export-policy denial was proven",
            0.5,
            "Policy evidence is insufficient",
        )


@dataclass
class BGPProcedureEngine:
    procedure: ProceduralGraph
    knowledge: KnowledgeGraph
    experience: ExperienceGraph
    evaluator: BGPEvidenceEvaluator = field(default_factory=BGPEvidenceEvaluator)

    def run(
        self,
        incident: BGPIncidentContext,
        adapter: ToolAdapter,
        policy: NavigationPolicy | None = None,
        max_steps: int = 12,
    ) -> ProcedureRun:
        navigator = policy or FixedNavigationPolicy()
        current = self.procedure.start_step
        visited: set[str] = set()
        outcomes: list[tuple[str, str]] = []
        executed: list[ExecutedStep] = []
        diagnosis: str | None = None
        status = "step_limit"

        for _ in range(max_steps):
            step = self.procedure.steps[current]
            if step.terminal:
                diagnosis = step.terminal_diagnosis
                status = "escalated" if diagnosis == "escalate" else "diagnosed"
                break
            visited.add(step.step_id)
            device, params = self._resolve_action(step, incident)
            result = adapter.execute(step.tool or "", device, params)
            evaluation = self.evaluator.evaluate(step, result, self.knowledge, incident)
            outcomes.append((step.step_id, evaluation.outcome))
            context_key = _context_key(outcomes[:-1])
            self.experience.record_execution(
                incident_id=incident.incident_id,
                procedure_id=self.procedure.graph_id,
                procedure_version=self.procedure.version,
                step_id=step.step_id,
                device_id=device,
                tool=step.tool or "",
                context_key=context_key,
                outcome=evaluation.outcome,
                evidence=evaluation.evidence,
                raw_output=result.stdout,
                confidence=evaluation.confidence,
                latency_ms=result.latency_ms,
                cost=step.estimated_cost,
                diagnosis=evaluation.diagnosis,
            )
            executed.append(
                ExecutedStep(
                    step_id=step.step_id,
                    title=step.title,
                    device=device,
                    tool=step.tool or "",
                    params=params,
                    outcome=evaluation.outcome,
                    evidence=evaluation.evidence,
                    confidence=evaluation.confidence,
                    latency_ms=result.latency_ms,
                    diagnosis=evaluation.diagnosis,
                )
            )
            candidates = [
                edge
                for edge in self.procedure.candidates(step.step_id, evaluation.outcome)
                if edge.target not in visited
            ]
            if not candidates:
                status = "no_transition"
                diagnosis = evaluation.diagnosis
                break
            context_key = _context_key(outcomes)
            current = navigator.choose(
                candidates, self.procedure, self.experience, context_key, visited
            ).target

        return ProcedureRun(
            incident_id=incident.incident_id,
            diagnosis=diagnosis,
            status=status,
            steps=tuple(executed),
            context_key=_context_key(outcomes),
        )

    def _resolve_action(
        self, step: ProcedureStep, incident: BGPIncidentContext
    ) -> tuple[str, dict[str, str]]:
        session = self.knowledge.get(incident.session_id).properties
        device_key = "remote_device" if step.device_role == "remote" else "local_device"
        device = str(session[device_key])
        params: dict[str, str] = {}
        if step.tool == "show_interface":
            params["interface"] = str(session["local_interface"])
        elif step.tool == "ping_peer":
            params["peer_ip"] = str(session["peer_ip"])
        elif step.tool == "show_bgp_route":
            params["prefix"] = incident.expected_prefix
        return device, params


def _context_key(outcomes: Sequence[tuple[str, str]]) -> str:
    if not outcomes:
        return "bgp:start"
    return "bgp:" + "|".join(f"{step}={outcome}" for step, outcome in outcomes)


def _find_peer_state(raw: str, peer_ip: str) -> str:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return ""

    def walk(node: object) -> str:
        if isinstance(node, dict):
            peers = node.get("peers")
            if isinstance(peers, dict) and peer_ip in peers:
                peer = peers[peer_ip]
                if isinstance(peer, dict):
                    return str(peer.get("state", peer.get("peerState", "")))
            if peer_ip in node and isinstance(node[peer_ip], dict):
                peer = node[peer_ip]
                return str(peer.get("state", peer.get("peerState", "")))
            for child in node.values():
                result = walk(child)
                if result:
                    return result
        elif isinstance(node, list):
            for child in node:
                result = walk(child)
                if result:
                    return result
        return ""

    return walk(value)
