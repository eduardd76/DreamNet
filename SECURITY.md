# Security policy

## Supported versions

DreamNet is an experimental pre-1.0 project. Security fixes are applied to the latest commit on the
default branch; older commits and generated artifacts are not separately supported.

## Reporting a vulnerability

Do not disclose vulnerabilities, exposed credentials, command-injection paths, or unsafe device
behavior in a public issue. Use GitHub's private vulnerability reporting for this repository. If that
feature is unavailable, contact the repository owner privately through the contact method on their
GitHub profile.

Include the affected commit, reproduction steps, impact, prerequisites, and any proposed mitigation.
Do not test against networks or systems you do not own or have explicit authorization to assess.

## Security boundary

The repository currently permits only allow-listed, read-only network commands. Contributions that
add configuration changes, arbitrary shell execution, credential handling, exploitation, or active
remediation require a separate threat model and maintainer approval before code is submitted.

Never commit secrets or real customer data. If a secret is committed, revoke it immediately; deleting
it from Git history is not sufficient.
