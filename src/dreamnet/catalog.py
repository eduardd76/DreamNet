from __future__ import annotations

from dataclasses import dataclass

BRANCHES = ("transport", "session", "policy", "routing", "changes", "platform")


@dataclass(frozen=True)
class Fault:
    protocol: str
    root_cause: str
    branch: str
    severity: str
    symptoms: tuple[str, ...]
    tools: tuple[str, str, str]
    observations: tuple[str, str, str]


FAULTS: tuple[Fault, ...] = (
    Fault("BGP", "interface_down", "transport", "critical",
          ("BGP neighbor down", "Loss of prefixes"),
          ("show_interface", "check_optics", "validate_link"),
          ("Physical state is down", "No receive light on peer-facing optic", "Interface failure proven")),
    Fault("BGP", "tcp_179_blocked", "transport", "high",
          ("BGP stuck Active", "ICMP reachability succeeds"),
          ("tcp_probe", "inspect_acl", "replay_flow"),
          ("TCP/179 handshake fails", "ACL denies peer traffic", "TCP/179 blocked by ACL")),
    Fault("BGP", "asn_mismatch", "session", "high",
          ("BGP notification received", "Session never establishes"),
          ("show_bgp_summary", "compare_neighbor_config", "validate_asn"),
          ("Peer rejects OPEN", "Configured remote AS differs", "BGP remote-AS mismatch")),
    Fault("BGP", "authentication_mismatch", "session", "high",
          ("BGP session reset", "TCP MD5 failure logged"),
          ("inspect_logs", "compare_auth_profile", "validate_auth"),
          ("Authentication failure present", "Peer key profiles differ", "BGP authentication mismatch")),
    Fault("BGP", "route_map_filter", "policy", "high",
          ("BGP session established", "Expected prefix absent"),
          ("show_advertised_routes", "trace_route_map", "validate_policy"),
          ("Peer does not receive prefix", "Deny sequence matches route", "Route-map filters expected prefix")),
    Fault("BGP", "next_hop_unreachable", "routing", "high",
          ("Prefix in BGP RIB", "Route missing from forwarding table"),
          ("show_bgp_route", "resolve_next_hop", "validate_fib"),
          ("Path is valid but not installed", "Next hop has no recursive route", "BGP next hop unreachable")),
    Fault("BGP", "mtu_mismatch", "transport", "medium",
          ("BGP flaps during update bursts", "Small pings succeed"),
          ("extended_ping", "compare_mtu", "validate_path_mtu"),
          ("Large DF ping fails", "Peer interfaces use different MTU", "Path MTU mismatch")),
    Fault("OSPF", "area_mismatch", "session", "high",
          ("OSPF neighbor stuck Down", "Hellos are visible"),
          ("capture_hellos", "compare_ospf_interface", "validate_area"),
          ("Hello received but rejected", "Area IDs differ", "OSPF area mismatch")),
    Fault("OSPF", "authentication_mismatch", "session", "high",
          ("OSPF neighbor down", "Authentication error logged"),
          ("inspect_logs", "compare_auth_profile", "validate_auth"),
          ("Hello authentication fails", "Key IDs or secrets differ", "OSPF authentication mismatch")),
    Fault("OSPF", "passive_interface", "platform", "high",
          ("No OSPF hellos transmitted", "Interface is operational"),
          ("capture_hellos", "show_protocol_config", "validate_passive"),
          ("No outbound hello packets", "Interface listed passive", "OSPF passive interface prevents adjacency")),
    Fault("OSPF", "duplicate_router_id", "routing", "medium",
          ("OSPF adjacency unstable", "Duplicate router ID event"),
          ("show_ospf_database", "compare_router_ids", "validate_router_id"),
          ("LSAs show identity collision", "Two nodes share router ID", "Duplicate OSPF router ID")),
    Fault("OSPF", "redistribution_missing", "policy", "medium",
          ("OSPF adjacency full", "External prefix absent"),
          ("show_route_source", "inspect_redistribution", "validate_export"),
          ("Source route exists locally", "No matching redistribute statement", "Route redistribution missing")),
    Fault("OSPF", "network_type_mismatch", "platform", "medium",
          ("OSPF neighbor stuck ExStart", "MTU is consistent"),
          ("show_ospf_neighbor", "compare_network_type", "validate_ospf_fsm"),
          ("Database exchange does not progress", "Network types differ", "OSPF network type mismatch")),
    Fault("OSPF", "acl_blocks_multicast", "transport", "high",
          ("OSPF neighbor down", "Local hellos transmitted"),
          ("packet_capture", "inspect_acl", "replay_multicast"),
          ("Peer hellos absent", "ACL denies 224.0.0.5", "ACL blocks OSPF multicast")),
)


GENERIC_TOOLS: dict[str, tuple[str, str, str]] = {
    "transport": ("ping_peer", "trace_path", "inspect_acl"),
    "session": ("show_neighbors", "inspect_protocol_logs", "compare_peer_config"),
    "policy": ("show_routes", "trace_policy", "validate_intent"),
    "routing": ("show_rib", "show_fib", "validate_reachability"),
    "changes": ("query_change_log", "diff_config", "correlate_timeline"),
    "platform": ("show_processes", "show_resource_state", "validate_platform_config"),
}
