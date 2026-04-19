"""AIGovClaw Hub v2 local HTTP API and task runner.

This package turns Hub v2 from a static dashboard into a command center. A
stdlib-only HTTP server exposes a small JSON API for enqueueing subprocess
tasks, inspecting their status, handling approvals, and computing composite
health. The Hub v2 React UI polls these endpoints to render a live task queue,
health strip, approval queue, and activity log.

No external Python dependencies. Binds 127.0.0.1 by default. No auth.
"""
