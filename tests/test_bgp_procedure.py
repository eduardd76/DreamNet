from pathlib import Path

from dreamnet.adapters import ToolResult
from dreamnet.bgp_demo import SCENARIOS, fixture_suite
from dreamnet.bgp_procedure import (
    BGPEvidenceEvaluator,
    BGPIncidentContext,
    build_bgp_procedural_graph,
    build_lab_knowledge_graph,
)

ROOT = Path(__file__).parents[1]


def test_bgp_procedure_graph_is_valid():
    graph = build_bgp_procedural_graph()
    graph.validate()
    assert graph.start_step == "bgp_summary"
    assert graph.steps["diagnosed_asn_mismatch"].terminal


def test_fixture_suite_is_correct_and_experience_reduces_calls(tmp_path):
    result = fixture_suite(ROOT / "examples" / "fixtures", tmp_path)
    assert result["baseline"]["diagnostic_accuracy"] == 1.0
    assert result["experience_guided"]["diagnostic_accuracy"] == 1.0
    assert result["experience_guided"]["mean_tool_calls"] < result["baseline"]["mean_tool_calls"]
    for scenario, expected in SCENARIOS.items():
        assert result["scenarios"][scenario]["experience_guided"]["diagnosis"] == expected
    assert (tmp_path / "experience_graph.json").is_file()


def test_failed_firewall_collection_does_not_become_clear_evidence():
    procedure = build_bgp_procedural_graph()
    evaluation = BGPEvidenceEvaluator().evaluate(
        procedure.steps["firewall_policy"],
        ToolResult(
            tool="show_firewall",
            device="r1",
            command=("iptables", "-S"),
            stdout="",
            stderr="iptables not found",
            returncode=127,
            latency_ms=5,
        ),
        build_lab_knowledge_graph(),
        BGPIncidentContext("test", "bgp-session:r1:r2", "192.0.2.1/32"),
    )
    assert evaluation.outcome == "unavailable"
    assert evaluation.diagnosis is None
