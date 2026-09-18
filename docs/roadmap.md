# Roadmap

DreamNet's target is an adaptive, evidence-driven troubleshooting procedure engine for network
operations. Expansion should follow evidence, not protocol count.

## v0.2 — BGP vertical slice

- [x] Executable BGP Procedural Graph
- [x] Minimal device, interface, peer and policy Knowledge Graph
- [x] Append-oriented Experience Graph
- [x] Deterministic evidence evaluators
- [x] Recorded-fixture and live-FRR adapters
- [x] Three-router Containerlab topology
- [x] Controlled interface, ASN, shutdown and export-policy scenarios
- [x] Experience-guided action ranking
- [ ] Execute and publish results from the live lab on a Docker/Containerlab host

## v0.3 — credible BGP evaluation

- Add at least 20 independently injected BGP failure scenarios.
- Split evaluation by topology and fault family, not random execution rows.
- Add authentication, next-hop, update-source, MTU and import-policy procedures.
- Prove specific route-policy matches instead of treating any attached deny path as sufficient.
- Measure diagnostic accuracy, tool calls, elapsed time, device load and escalation quality.
- Compare fixed playbook, experience-guided policy and an LLM-only baseline.

## v0.4 — production-shaped context

- Import topology and intended state from Nautobot.
- Add configuration version and change-event entities.
- Store raw evidence in an access-controlled immutable evidence store.
- Add schema migration and provenance support for all three graphs.
- Run read-only in shadow mode against replayed or approved operational incidents.

## Later protocol packs

Add a new domain only after the preceding BGP evaluation is credible:

1. OSPF adjacency and route propagation
2. EVPN/VXLAN control-plane and data-plane correlation
3. Firewall policy and application reachability
4. DNS and Linux service dependencies
5. Application dependency and end-to-end service procedures

Every pack must provide a versioned procedural graph, deterministic evidence evaluators, controlled
lab scenarios, held-out tests and clear escalation behavior.
