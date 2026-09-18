#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence

LAB_PREFIX = "clab-dreamnet-bgp"


def docker_exec(device: str, command: Sequence[str]) -> None:
    completed = subprocess.run(
        ["docker", "exec", f"{LAB_PREFIX}-{device}", *command],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr or completed.stdout)
    if completed.stdout:
        print(completed.stdout, end="")


def vtysh(device: str, *commands: str) -> None:
    args: list[str] = ["vtysh"]
    for command in commands:
        args.extend(("-c", command))
    docker_exec(device, args)


def interface_down(apply: bool) -> None:
    docker_exec("r1", ["ip", "link", "set", "eth1", "down" if apply else "up"])


def asn_mismatch(apply: bool) -> None:
    remote_as = "65102" if apply else "65002"
    vtysh(
        "r1",
        "configure terminal",
        "router bgp 65001",
        f"neighbor 10.0.12.2 remote-as {remote_as}",
    )


def neighbor_shutdown(apply: bool) -> None:
    command = "neighbor 10.0.12.2 shutdown" if apply else "no neighbor 10.0.12.2 shutdown"
    vtysh("r1", "configure terminal", "router bgp 65001", command)


def route_map_filter(apply: bool) -> None:
    if apply:
        vtysh(
            "r1",
            "configure terminal",
            "ip prefix-list BLOCK-LOOPBACK seq 5 deny 192.0.2.1/32",
            "ip prefix-list BLOCK-LOOPBACK seq 10 permit 0.0.0.0/0 le 32",
            "route-map BLOCK-EXPORT deny 10",
            "match ip address prefix-list BLOCK-LOOPBACK",
            "route-map BLOCK-EXPORT permit 20",
            "router bgp 65001",
            "address-family ipv4 unicast",
            "neighbor 10.0.12.2 route-map BLOCK-EXPORT out",
        )
    else:
        vtysh(
            "r1",
            "configure terminal",
            "router bgp 65001",
            "address-family ipv4 unicast",
            "no neighbor 10.0.12.2 route-map BLOCK-EXPORT out",
            "exit-address-family",
            "exit",
            "no route-map BLOCK-EXPORT",
            "no ip prefix-list BLOCK-LOOPBACK",
        )
    vtysh("r1", "clear bgp 10.0.12.2 soft out")


SCENARIOS = {
    "interface_down": interface_down,
    "asn_mismatch": asn_mismatch,
    "neighbor_shutdown": neighbor_shutdown,
    "route_map_filter": route_map_filter,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply or reset a controlled DreamNet BGP fault")
    parser.add_argument("action", choices=("apply", "reset"))
    parser.add_argument("scenario", choices=tuple(SCENARIOS))
    args = parser.parse_args()
    SCENARIOS[args.scenario](args.action == "apply")
    print(f"{args.action}: {args.scenario}")


if __name__ == "__main__":
    main()
