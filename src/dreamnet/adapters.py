from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import ClassVar, Protocol


@dataclass(frozen=True)
class ToolResult:
    tool: str
    device: str
    command: tuple[str, ...]
    stdout: str
    stderr: str
    returncode: int
    latency_ms: int


class ToolAdapter(Protocol):
    """Boundary between DreamNet orchestration and network tools/MCP servers."""

    def execute(
        self, tool: str, device: str, params: Mapping[str, str] | None = None
    ) -> ToolResult: ...


@dataclass
class RecordedAdapter:
    """Offline adapter for deterministic development from previously captured tool output."""

    fixture_dir: Path

    def execute(
        self, tool: str, device: str, params: Mapping[str, str] | None = None
    ) -> ToolResult:
        path = self.fixture_dir / f"{device}__{tool}.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing recorded tool fixture: {path}")
        value = json.loads(path.read_text(encoding="utf-8"))
        return ToolResult(
            tool=tool,
            device=device,
            command=tuple(value.get("command", [])),
            stdout=value.get("stdout", ""),
            stderr=value.get("stderr", ""),
            returncode=int(value.get("returncode", 0)),
            latency_ms=int(value.get("latency_ms", 0)),
        )


@dataclass
class ContainerlabFRRAdapter:
    """Read-only FRR command adapter; mutation is intentionally out of scope."""

    lab_prefix: str = "clab-dreamnet"
    timeout_seconds: int = 15

    COMMANDS: ClassVar[dict[str, tuple[str, ...]]] = {
        "show_bgp_summary": ("vtysh", "-c", "show bgp summary json"),
        "show_ospf_neighbor": ("vtysh", "-c", "show ip ospf neighbor json"),
        "show_ospf_database": ("vtysh", "-c", "show ip ospf database json"),
        "show_rib": ("vtysh", "-c", "show ip route json"),
        "show_fib": ("vtysh", "-c", "show ip route summary json"),
        "show_interface": ("vtysh", "-c", "show interface json"),
        "show_running_config": ("vtysh", "-c", "show running-config"),
        "show_firewall": ("iptables", "-S"),
    }

    def execute(
        self, tool: str, device: str, params: Mapping[str, str] | None = None
    ) -> ToolResult:
        import time

        params = params or {}
        if tool not in self.COMMANDS and tool not in {
            "show_bgp_route",
            "show_interface",
            "ping_peer",
        }:
            raise ValueError(f"tool is not allow-listed: {tool}")
        if not device.replace("-", "").isalnum():
            raise ValueError("device name contains unsupported characters")
        tool_command = self._build_tool_command(tool, params)
        command: Sequence[str] = (
            "docker",
            "exec",
            f"{self.lab_prefix}-{device}",
            *tool_command,
        )
        started = time.monotonic()
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        latency_ms = round((time.monotonic() - started) * 1000)
        return ToolResult(
            tool=tool,
            device=device,
            command=tuple(command),
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
            latency_ms=latency_ms,
        )

    def _build_tool_command(self, tool: str, params: Mapping[str, str]) -> tuple[str, ...]:
        if tool in self.COMMANDS and tool != "show_interface":
            return self.COMMANDS[tool]
        if tool == "show_interface":
            interface = params.get("interface", "")
            if re.fullmatch(r"[A-Za-z0-9_.:-]{1,32}", interface) is None:
                raise ValueError("invalid or missing interface parameter")
            return ("ip", "-j", "link", "show", "dev", interface)
        if tool == "ping_peer":
            peer_ip = str(ip_address(params.get("peer_ip", "")))
            return ("ping", "-c", "2", "-W", "1", peer_ip)
        if tool == "show_bgp_route":
            prefix = str(ip_network(params.get("prefix", ""), strict=False))
            return ("vtysh", "-c", f"show bgp ipv4 unicast {prefix} json")
        raise ValueError(f"tool is not allow-listed: {tool}")
