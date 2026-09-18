# DreamNet graph model

DreamNet separates network facts, approved procedures and observed experience. These graphs have
different lifecycles and trust requirements and must not be collapsed into one undifferentiated
store.

## Knowledge Graph

The Knowledge Graph describes the network and its intended state.

Example vertices:

- `device:r1`
- `interface:r1:eth1`
- `bgp-session:r1:r2`
- `policy:r1:export`

Example relationships:

```text
device:r1 --------HAS_INTERFACE-------> interface:r1:eth1
device:r1 --------HAS_BGP_SESSION-----> bgp-session:r1:r2
bgp-session:r1:r2 USES_INTERFACE------> interface:r1:eth1
bgp-session:r1:r2 GOVERNED_BY----------> policy:r1:export
bgp-session:r1:r2 REMOTE_DEVICE--------> device:r2
```

The Knowledge Graph supplies intended ASN, peer address, local interface and applicable policy to the
evidence evaluator. It does not decide what diagnostic command to execute.

## Procedural Graph

The Procedural Graph is a versioned, executable troubleshooting playbook.

An action step specifies:

- stable step identifier;
- human-readable purpose;
- diagnostic branch;
- allow-listed tool;
- device role;
- estimated cost.

A transition specifies:

- source step;
- normalized evidence outcome;
- eligible target step;
- authored priority.

Terminal steps produce a diagnosis or escalation. The navigator may rank multiple eligible targets,
but cannot create a step, command or transition that is absent from the approved graph.

## Experience Graph

The Experience Graph is a property graph of what was actually executed. It is append-oriented and
links every diagnostic action to its incident, procedure version, target, normalized evidence and
validated result.

```text
incident --HAS_EXECUTION--> execution
execution --USED_STEP-----> procedure_step
execution --TARGETED------> device
execution --PRODUCED------> evidence
evidence  --SUPPORTS------> diagnosis
```

An execution carries:

- context signature representing evidence already known before the action;
- tool name;
- latency and estimated cost;
- normalized outcome and confidence;
- resolution flag and diagnosis, when proven;
- SHA-256 digest of raw output.

Raw device output is not copied into the Experience Graph by default. Production integrations should
retain raw evidence in an access-controlled evidence store and use the digest to link the graph event
to the immutable source artifact.

## How experience changes navigation

Suppose the procedural graph permits both firewall inspection and BGP peer-configuration comparison
after the system proves that the interface is up and the peer responds to ICMP.

The fixed navigator uses the authored priorities. The experience navigator combines those priorities
with historical resolution rate, latency and cost for each eligible step. If peer-configuration
comparison repeatedly proves ASN mismatches while firewall inspection repeatedly returns clear, the
configuration step moves earlier for similar future investigations.

This is not unconstrained reinforcement learning. The learned component ranks only approved actions,
and deterministic evidence evaluation controls the transitions.

## Trust boundaries

- Knowledge must be versioned and sourced from an authoritative system such as Nautobot or validated
  configuration state.
- Procedures require code review and regression tests.
- Experience must distinguish proposed, observed, validated and operator-accepted conclusions.
- Raw output may contain sensitive operational data and requires separate retention controls.
- A diagnosis must not be marked validated merely because an LLM agrees with it.
