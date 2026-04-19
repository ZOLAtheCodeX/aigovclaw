[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/hermes--agent-compatible-blue.svg)](https://github.com/NousResearch/hermes-agent)

# AIGovClaw

**Local-first AI governance runtime for audit-grade artifact production.**

AIGovClaw is the Hermes Agent runtime configuration package for AIGovOps. Clone this repository, run the installer, and you have a working local agent that takes an AI system description and produces audit-grade artifacts: ISO/IEC 42001 audit log entries, NIST AI RMF gap assessments, risk registers, and AI System Impact Assessments. Every output is acceptable as audit evidence, every consequential action is approved or declined by the operator, and every decision leaves a traceable audit entry.

See the [audit-log demo](demos/audit-log/README.md) for an end-to-end example: input fixture, exact command, captured JSON and Markdown output, and replayable test.

## Architecture at a glance

```
+-----------------------------------------------------------------------+
|                         Operator surfaces                             |
|   Hub v2 UI | Hub v2 HTTP API | CLI | Slack | Discord | Telegram      |
+-----------------------------------+-----------------------------------+
                                    |
                                    v                    TaskEnvelope
+-----------------------------------------------------------------------+
|                         Hermes Agent runtime                          |
|         gateway/platforms/*  |  tool registry  |  persona             |
+-----------------------------------+-----------------------------------+
                                    |
                                    v                    ActionRequest
+-----------------------------------------------------------------------+
|                        AIGovClaw domain layer                         |
|   action_executor  |  agent_loop (PDCA)  |  workflows/  |  audit log  |
+-----------------------------------+-----------------------------------+
                                    |
                                    v                    plugin invocation
+-----------------------------------------------------------------------+
|                      AIGovOps plugin catalogue                        |
|   audit-log-generator | gap-assessment | risk-register | aisia | ...  |
+-----------------------------------+-----------------------------------+
                                    |
                                    v
                          Local memory and evidence store
                        ~/.hermes/memory/aigovclaw/
```

Four layers, four responsibilities. Hermes Agent handles channels, session ingress, and tool registration. AIGovClaw is the domain layer: workflow semantics, action authority, audit trail, evidence production. AIGovOps is the framework-agnostic plugin catalogue (skills, plugins, bundles, evals). The local memory store holds audit evidence, approvals, and action snapshots under four named classes; see [docs/memory-model.md](docs/memory-model.md).

## Status

| Layer | State |
|---|---|
| Hermes gateway and channels | Works. 18 upstream adapters inherited; notification handler wired through `hermes.gateway.delivery.deliver` in-process and via `HERMES_API_URL` out-of-process. |
| Action executor (6 action types, authority policy, audit trail, snapshot and rollback, rate limiting) | Works. 27 tests pass. |
| Task envelope schema (`aigovclaw.task_envelope`) | Works. 9 tests pass. Wired to Hub v2 `/api/tasks` ingress in a follow-up commit. |
| Audit event schema (`aigovclaw.action_executor.audit_event`) | Works. 7 tests pass. Legacy flat writer retained for backward compatibility. |
| Risk-tier classification on the action registry | Works. Every action carries an explicit tier; surfaced in audit intent and pending-approval output. |
| PDCA agent loop (gap-resolution, cascade, validation) | Works. Orchestrator + gap-resolution tests pass. |
| Hub v2 Command Centre (HTTP API, task queue, approvals, PDCA routes) | Works. Generator, server, and route tests pass. |
| AIGovOps plugin catalogue | Works, dependent on `aigovops` sibling repo. 32 plugins and 24 skills registered via `tools/aigovops_tools.py`. |
| Audit-log workflow end-to-end demo | Works. See [demos/audit-log/](demos/audit-log/). |
| gap-assessment, risk-register, aisia-runner workflows end-to-end demos | Planned. Underlying plugins ship with tests; integration demos tracked as follow-up work. |
| HMAC audit-event signing | Works when `AIGOVCLAW_AUDIT_SIGNING_KEY` is set. Signing-key provisioning process is not yet production hardened. |
| Approval UI in Command Centre chat surfaces | Works for Hub v2 UI. Channel-based reply approval (Slack and friends) is planned. |

See the [operational action layer](AGENTS.md#8-operational-action-layer) for the enforced contracts.

## Three-step install

```bash
git clone https://github.com/ZOLAtheCodeX/aigovclaw
cd aigovclaw
./install.sh
```

The installer detects an existing Hermes Agent installation, installs Hermes if missing, copies the AIGovOps skills into the Hermes workspace, applies the AIGovClaw persona and security configuration, and runs `hermes doctor` to verify the setup.

## What the agent does out of the box

Once installed, AIGovClaw runs four governance workflows:

| Workflow | What it does |
|---|---|
| [audit-log](workflows/audit-log.md) | Generates ISO 42001-compliant audit log entries from AI system descriptions and governance events. |
| [gap-assessment](workflows/gap-assessment.md) | Runs a gap assessment of an AI Management System against ISO 42001 Annex A controls or NIST AI RMF subcategories. |
| [risk-register](workflows/risk-register.md) | Produces and maintains an AI risk register with framework-mapped controls. |
| [aisia-runner](workflows/aisia-runner.md) | Executes an AI System Impact Assessment per ISO 42001 Clause 6.1.4. |

## Security posture

AIGovClaw is configured for security-first defaults out of the box.

- **Scoped permissions**: filesystem write, shell execution, email, and calendar are disabled by default. They are enabled only by explicit user action and only for workflows that require them.
- **No ClawHub or marketplace dependencies**: every component is sourced from this repository or [aigovops](https://github.com/ZOLAtheCodeX/aigovops). Nothing is fetched from third-party plugin marketplaces at runtime.
- **Hermes security model**: AIGovClaw inherits the Hermes Agent security model. No CVEs have been reported against the Hermes Agent core at the time of this release.
- **Local-first memory**: agent memory is stored in the local filesystem under `~/.hermes/memory/aigovclaw/`. No memory data leaves the host unless the user explicitly enables a remote backend.

## Requirements

- Hermes Agent (installed automatically by `install.sh` if missing).
- Any OpenAI-compatible LLM. Local (Ollama, llama.cpp) or hosted (OpenAI, Anthropic, Together, Groq, Vercel AI Gateway, and others). No vendor lock-in.
- Linux, macOS, or WSL2.

## Skills catalogue

AIGovClaw consumes the [aigovops](https://github.com/ZOLAtheCodeX/aigovops) skills catalogue. The installer copies the catalogue into the Hermes workspace at install time. To update skills, re-run `./install.sh`.

## Configuration

The Hermes runtime configuration lives in [config/hermes.yaml](config/hermes.yaml). Defaults are restrictive. Read the comments before relaxing any permissions.

The agent persona lives in [persona/SOUL.md](persona/SOUL.md). The persona defines the agent's identity, expertise domains, operating mandate, and security constraints.

## Quality bar

All workflows in this repository, and all skill outputs they consume, are held to the certification-grade standard defined in [aigovops/STYLE.md](https://github.com/ZOLAtheCodeX/aigovops/blob/main/STYLE.md). Outputs must be acceptable as audit evidence by a practicing ISO 42001 Lead Auditor or NIST AI RMF practitioner.

## Security

See [SECURITY.md](SECURITY.md).

## Maintainer tooling (not a product feature)

The following subdirectories exist for repository maintenance only. They are not invoked by end-users and not registered as Hermes tools. Treat them the way you would treat CI workflows or dependabot configuration.

- [jules/](jules/): Google Jules dispatcher + 8 playbook prompt templates. Used by the maintainers to automate low-judgment repo maintenance (framework text drift, test coverage gaps, dependency bumps, citation drift fixes, markdown lint regressions). See [docs/jules-integration-design.md](docs/jules-integration-design.md) for the rationale.
- [.github/workflows/jules-*.yml](.github/workflows/): GitHub Actions that invoke Jules via `google-labs-code/jules-invoke@v1` on cron or event triggers. Require `JULES_API_KEY` in repo secrets; fail fast with a clear message if missing.
