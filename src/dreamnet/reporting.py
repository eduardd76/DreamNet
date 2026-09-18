from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from .models import PolicyConfig, RunResult, Score


def aggregate(scores: list[Score]) -> dict[str, float]:
    return {
        "objective": mean(s.value for s in scores),
        "accuracy": mean(s.correct for s in scores),
        "quality": mean(s.quality for s in scores),
        "requests": mean(s.requests for s in scores),
        "rounds": mean(s.rounds for s in scores),
        "parallelism": mean(s.parallelism for s in scores),
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_demo_report(
    path: Path,
    baseline: PolicyConfig,
    learned: PolicyConfig,
    replay_baseline: dict[str, float],
    replay_learned: dict[str, float],
    online_baseline: dict[str, float],
    online_learned: dict[str, float],
) -> None:
    request_reduction = 100 * (
        1 - online_learned["requests"] / max(online_baseline["requests"], 1e-9)
    )
    text = f"""# DreamNet evaluation report

This report compares the fixed exploration policy with the replay-optimized policy.

## Held-out online incidents (primary result)

| Metric | Fixed policy | Learned policy |
|---|---:|---:|
| Diagnostic accuracy | {online_baseline['accuracy']:.1%} | {online_learned['accuracy']:.1%} |
| Mean diagnostic quality | {online_baseline['quality']:.3f} | {online_learned['quality']:.3f} |
| Mean tool calls | {online_baseline['requests']:.2f} | {online_learned['requests']:.2f} |
| Mean decision rounds | {online_baseline['rounds']:.2f} | {online_learned['rounds']:.2f} |
| Mean objective | {online_baseline['objective']:.3f} | {online_learned['objective']:.3f} |

Tool-call reduction: **{request_reduction:.1f}%**.

## Training-tree replay

| Metric | Fixed policy | Learned policy |
|---|---:|---:|
| Diagnostic accuracy | {replay_baseline['accuracy']:.1%} | {replay_learned['accuracy']:.1%} |
| Mean tool calls | {replay_baseline['requests']:.2f} | {replay_learned['requests']:.2f} |
| Mean objective | {replay_baseline['objective']:.3f} | {replay_learned['objective']:.3f} |

## Selected policy

```json
{json.dumps(learned.to_dict(), indent=2)}
```

## Interpretation

The learned result is valid only for this simulator distribution. It demonstrates that historical
discovery trees can improve an orchestration policy without changing the troubleshooting model or
the evaluator. It does **not** prove production generalization. The next validation gate is to replace
the synthetic environment with FRR/Containerlab observations while keeping the replay and selection
interfaces unchanged.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def result_trace(result: RunResult) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    for round_index, node_ids in enumerate(result.tree.rounds, start=1):
        trace.append({
            "round": round_index,
            "nodes": [result.tree.nodes[node_id].to_dict() for node_id in node_ids],
        })
    return trace
