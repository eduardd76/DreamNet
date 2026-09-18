from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
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

    def execute(self, tool: str, device: str) -> ToolResult: ...


@dataclass
class RecordedAdapter:
    """Offline adapter for deterministic development from previously captured tool output."""

    fixture_dir: Path

    def execute(self, tool: str, device: str) -> ToolResult:
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
        "show_bgp_route": ("vtysh", "-c", "show bgp ipv4 unicast json"),
        "show_ospf_neighbor": ("vtysh", "-c", "show ip ospf neighbor json"),
        "show_ospf_database": ("vtysh", "-c", "show ip ospf database json"),
        "show_rib": ("vtysh", "-c", "show ip route json"),
        "show_fib": ("vtysh", "-c", "show ip route summary json"),
        "show_interface": ("vtysh", "-c", "show interface json"),
        "show_running_config": ("vtysh", "-c", "show running-config"),
    }

    def execute(self, tool: str, device: str) -> ToolResult:
        import time

        if tool not in self.COMMANDS:
            raise ValueError(f"tool is not allow-listed: {tool}")
        if not device.replace("-", "").isalnum():
            raise ValueError("device name contains unsupported characters")
        command: Sequence[str] = (
            "docker",
            "exec",
            f"{self.lab_prefix}-{device}",
            *self.COMMANDS[tool],
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
