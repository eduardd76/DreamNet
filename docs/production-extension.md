# From simulator to vExpertAI production evidence

The current repository proves the orchestration/replay mechanism end to end. It does not yet prove
that the learned policy works on a real network. The safest progression is below.

## Phase 1 — Recorded FRR fixtures

1. Run a controlled BGP/OSPF Containerlab topology.
2. Inject one known fault at a time.
3. Execute an allow-listed read-only tool catalog.
4. Store raw output, command, latency, device, topology version, and fault label.
5. Parse outputs into normalized facts.
6. Let deterministic rules score whether each observation supports or refutes a hypothesis.
7. Re-run the same replay optimizer on those recorded trees.

Use `RecordedAdapter` during this phase so development never depends on a live lab.

## Phase 2 — Live Containerlab rollouts

Replace only `NetworkEnvironment.expand` with a live discovery worker:

```text
selected node
  -> choose next allow-listed tool
  -> ContainerlabFRRAdapter.execute
  -> normalize JSON/text output
  -> deterministic evidence evaluator
  -> immutable child node
```

Keep the policy, discovery-tree schema, replay semantics, objective, train/holdout split, and reports
unchanged. This isolates whether a performance change comes from the environment or from policy logic.

## Phase 3 — vExpertAI components

| DreamNet boundary | vExpertAI component |
|---|---|
| Tool adapter | MCP servers for devices, Nautobot, telemetry, SIEM |
| Normalized observations | Fact Plane / Knowledge Graph |
| Frozen evaluator | Network invariants, reachability tests, intent and compliance checks |
| Online world | Containerlab/EVE-NG digital twin, then read-only production |
| Policy developer | Local approved LLM proposing policy code or constrained parameters |
| Replay store | Versioned incident/discovery-tree store |
| Approval boundary | Evidence Gate plus human approval |

## Required safeguards

- Split histories by topology, fault family, time, and customer—not random rows from the same incident.
- Never let evaluation labels leak into policy observations.
- Version device configuration, topology, tool implementation, parser, evaluator, and model with every node.
- Sign or hash immutable histories so replay cannot silently train on altered outcomes.
- Treat timeouts, missing telemetry, parser failures, and contradictory evidence as first-class observations.
- Cap concurrent reads per device and apply rate limits.
- Optimize tail latency and worst-case device load, not only averages.
- Require the learned policy to pass a fixed regression suite before deployment.
- Keep analysis autonomy separate from change authority. This layer should not acquire write permission.

## Promotion gates

| Gate | Minimum evidence |
|---|---|
| Synthetic -> recorded lab | Same replay code passes on real command fixtures |
| Recorded -> live lab | Learned policy beats fixed policy on held-out fault injections |
| Live lab -> shadow production | No write tools; bounded read load; parser/evaluator reliability measured |
| Shadow -> assisted operations | Expert accepts diagnostic evidence and policy regression results |
| Assisted -> limited action | Separate change engine, digital-twin validation, explicit approval and rollback |

The key anti-pattern is to replace the deterministic evaluator with an LLM judge and celebrate a
rising score. That would optimize agreement with the model, not network correctness.
