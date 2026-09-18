import json

import pytest

from dreamnet.adapters import ContainerlabFRRAdapter, RecordedAdapter


def test_recorded_adapter_loads_fixture(tmp_path):
    fixture = tmp_path / "r1__show_bgp_summary.json"
    fixture.write_text(json.dumps({"stdout": "{}", "latency_ms": 12}), encoding="utf-8")
    result = RecordedAdapter(tmp_path).execute("show_bgp_summary", "r1")
    assert result.stdout == "{}"
    assert result.latency_ms == 12


def test_containerlab_adapter_rejects_non_allowlisted_tools():
    with pytest.raises(ValueError, match="allow-listed"):
        ContainerlabFRRAdapter().execute("configure_terminal", "r1")


def test_containerlab_adapter_rejects_unsafe_device_name():
    with pytest.raises(ValueError, match="device name"):
        ContainerlabFRRAdapter().execute("show_rib", "r1;whoami")


def test_containerlab_adapter_validates_dynamic_parameters():
    adapter = ContainerlabFRRAdapter()
    with pytest.raises(ValueError, match="interface"):
        adapter._build_tool_command("show_interface", {"interface": "eth1;id"})
    with pytest.raises(ValueError):
        adapter._build_tool_command("ping_peer", {"peer_ip": "10.0.0.1;id"})
