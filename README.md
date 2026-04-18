[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/hermes--agent-compatible-blue.svg)](https://github.com/NousResearch/hermes-agent)

# AIGovClaw

**AIGovOps running as an autonomous governance agent. Powered by Hermes Agent.**

AIGovClaw is the runtime configuration package for AIGovOps. Clone this repository, run the installer, and you have a working AI governance operations agent on your machine. The agent loads the [aigovops](https://github.com/ZOLAtheCodeX/aigovops) skills catalogue and operates against AI governance frameworks (NIST AI RMF, ISO/IEC 42001, EU AI Act, and others).

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

