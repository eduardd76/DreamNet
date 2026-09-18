import json

from dreamnet.bgp_procedure import build_lab_knowledge_graph
from dreamnet.graphs import ExperienceGraph


def test_knowledge_graph_connects_device_session_interface_and_policy():
    graph = build_lab_knowledge_graph()
    related = graph.related("bgp-session:r1:r2")
    kinds = {entity.kind for entity in related}
    assert kinds == {"device", "interface", "routing_policy"}


def test_experience_graph_stores_digest_not_raw_output():
    graph = ExperienceGraph()
    graph.record_execution(
        incident_id="incident-1",
        procedure_id="bgp-test",
        procedure_version="1",
        step_id="summary",
        device_id="r1",
        tool="show_bgp_summary",
        context_key="bgp:start",
        outcome="not_established",
        evidence="Peer is Active",
        raw_output="sensitive raw device output",
        confidence=0.9,
        latency_ms=10,
        cost=1.0,
        diagnosis=None,
    )
    serialized = json.dumps(graph.to_dict())
    assert "sensitive raw device output" not in serialized
    assert "raw_sha256" in serialized
