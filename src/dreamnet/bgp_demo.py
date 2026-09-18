from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from .adapters import ContainerlabFRRAdapter, RecordedAdapter
from .bgp_procedure import (
    BGPIncidentContext,
    BGPProcedureEngine,
    ExperienceNavigationPolicy,
    FixedNavigationPolicy,
    ProcedureRun,
    build_bgp_procedural_graph,
    build_lab_knowledge_graph,
)
from .graphs import ExperienceGraph

SCENARIOS = {
    "interface_down": "interface_down",
    "asn_mismatch": "asn_mismatch",
    "neighbor_shutdown": "neighbor_shutdown",
    "route_map_filter": "route_map_filter",
}


def fixture_suite(fixtures: Path, output: Path) -> dict[str, object]:
    procedure = build_bgp_procedural_graph()
    knowledge = build_lab_knowledge_graph()
    baseline_experience = ExperienceGraph()
    baseline_engine = BGPProcedureEngine(procedure, knowledge, baseline_experience)
    baseline_runs: dict[str, ProcedureRun] = {}

    for scenario in SCENARIOS:
        baseline_runs[scenario] = baseline_engine.run(
            _incident(f"baseline-{scenario}"),
            RecordedAdapter(fixtures / scenario),
            FixedNavigationPolicy(),
        )

    # The learned phase starts with only the completed baseline histories.
    learned_experience = ExperienceGraph.from_dict(baseline_experience.to_dict())
    learned_engine = BGPProcedureEngine(procedure, knowledge, learned_experience)
    learned_runs: dict[str, ProcedureRun] = {}
    for scenario in SCENARIOS:
        learned_runs[scenario] = learned_engine.run(
            _incident(f"learned-{scenario}"),
            RecordedAdapter(fixtures / scenario),
            ExperienceNavigationPolicy(),
        )

    summary = {
        "baseline": _metrics(baseline_runs),
        "experience_guided": _metrics(learned_runs),
        "scenarios": {
            scenario: {
                "expected": expected,
                "baseline": baseline_runs[scenario].to_dict(),
                "experience_guided": learned_runs[scenario].to_dict(),
            }
            for scenario, expected in SCENARIOS.items()
        },
        "limitations": [
            "Bundled outputs are deterministic fixtures, not live results from this runtime.",
            "The live Containerlab command must be used to validate the same engine against FRR.",
            "Four scenarios are insufficient evidence for production generalization.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "summary.json", summary)
    _write_json(output / "knowledge_graph.json", knowledge.to_dict())
    _write_json(output / "procedural_graph.json", procedure.to_dict())
    learned_experience.save(output / "experience_graph.json")
    return summary


def live_run(
    *,
    incident_id: str,
    expected_prefix: str,
    output: Path,
    lab_prefix: str = "clab-dreamnet-bgp",
) -> dict[str, object]:
    procedure = build_bgp_procedural_graph()
    knowledge = build_lab_knowledge_graph()
    experience_path = output / "experience_graph.json"
    experience = ExperienceGraph.load(experience_path)
    engine = BGPProcedureEngine(procedure, knowledge, experience)
    policy = ExperienceNavigationPolicy() if experience.vertices else FixedNavigationPolicy()
    run = engine.run(
        BGPIncidentContext(
            incident_id=incident_id,
            session_id="bgp-session:r1:r2",
            expected_prefix=expected_prefix,
        ),
        ContainerlabFRRAdapter(lab_prefix=lab_prefix),
        policy,
    )
    output.mkdir(parents=True, exist_ok=True)
    experience.save(experience_path)
    _write_json(output / "knowledge_graph.json", knowledge.to_dict())
    _write_json(output / "procedural_graph.json", procedure.to_dict())
    _write_json(output / f"run-{incident_id}.json", run.to_dict())
    return run.to_dict()


def _incident(incident_id: str) -> BGPIncidentContext:
    return BGPIncidentContext(
        incident_id=incident_id,
        session_id="bgp-session:r1:r2",
        expected_prefix="192.0.2.1/32",
    )


def _metrics(runs: dict[str, ProcedureRun]) -> dict[str, float]:
    return {
        "diagnostic_accuracy": mean(
            runs[scenario].diagnosis == expected for scenario, expected in SCENARIOS.items()
        ),
        "mean_tool_calls": mean(len(run.steps) for run in runs.values()),
        "mean_latency_ms": mean(
            sum(step.latency_ms for step in run.steps) for run in runs.values()
        ),
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
