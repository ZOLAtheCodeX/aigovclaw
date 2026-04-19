# Demos

Each subdirectory here is a canonical end-to-end demonstration of one governance workflow. Every demo has the same four files:

- `input.json`: the input fixture. Realistic, not minimal.
- `run.py`: stdlib-only runner that builds a TaskEnvelope, invokes the aigovops plugin, persists outputs, and writes AuditEvents.
- `README.md`: what the demo proves, prerequisites, invocation, output shape, what the demo does not cover.
- `test_<workflow>_demo.py`: replay test that runs `run.py` in place and asserts output shape. Gated in CI via the `pytest-suite` job. Unique basenames (not `test_demo.py`) so pytest can collect multiple demos in one session.

Demos share a convention: outputs land in `demos/<workflow>/output/`, which is gitignored for locally-generated timestamped files. A single set of reference outputs is committed per demo so reviewers can see the last known good result without running the demo.

## Available demos

| Demo | Workflow | Target framework | What it exercises |
|---|---|---|---|
| [audit-log](audit-log/README.md) | audit-log | ISO/IEC 42001 | Plugin output with Annex A control mapping for a high-risk clinical AI system. |
| [gap-assessment](gap-assessment/README.md) | gap-assessment | ISO/IEC 42001 | Full Annex A control sweep against a two-system AIMS, producing covered, partially-covered, not-covered, and not-applicable classifications with a coverage score. |

## Run a demo

```bash
cd /path/to/aigovclaw
python demos/audit-log/run.py
python demos/gap-assessment/run.py
```

Each demo searches for the sibling aigovops plugins in order: `$AIGOVOPS_PLUGINS_PATH`, `../aigovops/plugins/`, `~/Documents/CODING/aigovops/plugins/`.

## Run the replay tests

```bash
python -m pytest demos/ -v
```

These tests skip automatically when the aigovops plugins path is not available.
