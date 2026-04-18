# Security Policy

## Scope

This policy covers the AIGovClaw runtime (this repository) and the AIGovOps catalogue (https://github.com/ZOLAtheCodeX/aigovops). Vulnerabilities in either repository should be reported through the channel described below.

Vulnerabilities in upstream Hermes Agent core are out of scope for this policy. Report those directly to Nous Research at the Hermes Agent repository.

## Reporting a vulnerability

Use GitHub Security Advisories for private disclosure before any public discussion of the vulnerability. To report:

1. Navigate to the Security tab of this repository.
2. Click "Report a vulnerability."
3. Complete the advisory form with the details listed below.

Do not open a public GitHub issue, post to social media, or discuss the vulnerability in any public forum until the maintainers have acknowledged the report and coordinated a disclosure timeline.

## What to include in a report

A complete report contains:

- A clear description of the vulnerability and the affected component (installer, workflow, persona, configuration file, or skill loading path).
- The version, commit SHA, or release tag in which the vulnerability is present.
- Reproduction steps, including any input data, configuration, or environment details required to trigger the issue.
- The expected behavior and the observed behavior.
- An assessment of impact: confidentiality, integrity, availability, and any specific governance or compliance implications. Examples of governance-specific impact: a configuration change that allows the agent to execute shell commands without user confirmation; a workflow that emits framework citations not grounded in the loaded skill; a persona modification that bypasses the operating mandate.
- Any suggested mitigation or fix.
- Your preferred attribution name and contact channel for follow-up.

## Response SLA

Maintainers will acknowledge a report within 72 hours of submission. The acknowledgment will include an initial assessment of severity and a target timeline for triage.

For confirmed vulnerabilities:

- Critical and High severity issues will receive a fix or mitigation within 14 days of confirmation.
- Medium severity issues will receive a fix or mitigation within 30 days of confirmation.
- Low severity issues will be addressed in the next regular release cycle.

These timelines are targets, not guarantees. Complex issues or those requiring upstream coordination may take longer. Reporters will be kept informed of progress.

## Disclosure

After a fix is released, the maintainers will publish a security advisory describing the vulnerability, the affected versions, the fix, and any mitigations available to users of older versions. The reporter will be credited in the advisory unless they request otherwise.

## Permission posture

AIGovClaw ships with restrictive defaults in `config/hermes.yaml`. Filesystem writes, shell execution, email, and calendar are disabled by default. Reports of misconfigurations that effectively grant broader permissions than documented are in scope for this policy and will be treated as security issues.

## Out of scope

The following are not considered security vulnerabilities for this repository:

- Vulnerabilities in Hermes Agent core. Report to Nous Research.
- Vulnerabilities in third-party LLM providers used by AIGovClaw. Report to the relevant provider.
- Disagreements about framework interpretation. These should be raised as issues, not security advisories.
- Feature requests and enhancement suggestions. Use regular issues.
