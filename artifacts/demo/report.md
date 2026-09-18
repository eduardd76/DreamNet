# DreamNet evaluation report

This report compares the fixed exploration policy with the replay-optimized policy.

## Held-out online incidents (primary result)

| Metric | Fixed policy | Learned policy |
|---|---:|---:|
| Diagnostic accuracy | 100.0% | 100.0% |
| Mean diagnostic quality | 1.000 | 1.000 |
| Mean tool calls | 18.00 | 5.88 |
| Mean decision rounds | 8.00 | 5.88 |
| Mean objective | 0.573 | 0.863 |

Tool-call reduction: **67.3%**.

## Training-tree replay

| Metric | Fixed policy | Learned policy |
|---|---:|---:|
| Diagnostic accuracy | 100.0% | 100.0% |
| Mean tool calls | 18.00 | 5.74 |
| Mean objective | 0.573 | 0.867 |

## Selected policy

```json
{
  "name": "dreamnet_learned",
  "workers": 1,
  "min_branches": 1,
  "max_branches": 6,
  "max_nodes": 18,
  "refine_threshold": 0.55,
  "stop_threshold": 0.99,
  "root_priority": 0.45,
  "depth_penalty": 0.0,
  "evidence_weight": 1.25,
  "open_after_stall": false
}
```

## Interpretation

The learned result is valid only for this simulator distribution. It demonstrates that historical
discovery trees can improve an orchestration policy without changing the troubleshooting model or
the evaluator. It does **not** prove production generalization. The next validation gate is to replace
the synthetic environment with FRR/Containerlab observations while keeping the replay and selection
interfaces unchanged.
