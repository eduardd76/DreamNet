# Contributing to DreamNet

Thank you for helping make replay-based network troubleshooting more rigorous and useful.

## Before opening a pull request

1. Search existing issues and pull requests.
2. For a substantial feature, open a proposal issue before implementation.
3. Keep device integrations read-only unless a maintainer has explicitly approved a separate,
   safety-reviewed design discussion.
4. Never include customer configurations, credentials, production telemetry, personal data, or
   proprietary vendor material.
5. Add tests and evidence for behavioral changes.

## Development setup

```bash
git clone https://github.com/eduardd76/DreamNet.git
cd DreamNet
make install
make test
make lint
```

Run the reproducible demonstration with `make demo`.

## Contribution standards

- Prefer small pull requests with one clear purpose.
- Preserve the shared online/replay decision interface.
- Replay must reveal only recorded outcomes; it must not fabricate counterfactual observations.
- Keep the discovery environment and evaluator frozen during a policy-comparison experiment.
- Use incident-level or topology-level train/test separation and document possible leakage.
- Report accuracy, quality, calls, decision rounds, parallelism, seed, and objective coefficients.
- Mark synthetic, lab, and production-derived results unambiguously.
- Fail closed when a parser, tool, validator, or evidence source is unavailable.
- Do not add arbitrary shell execution or write-capable device commands.

## Pull-request checklist

- [ ] Tests pass locally.
- [ ] Lint passes locally.
- [ ] New behavior has tests.
- [ ] Documentation describes assumptions and limitations.
- [ ] No secrets, customer data, or generated environment artifacts are committed.
- [ ] Any benchmark claim includes configuration, seed, and raw metrics.

By contributing, you agree that your contribution is licensed under Apache-2.0.
