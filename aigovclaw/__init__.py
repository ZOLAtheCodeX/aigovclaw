"""AIGovClaw runtime package.

Hosts the runtime layers that turn AIGovOps plugin artifacts into operational
actions: action-executor, cascade handling, PDCA orchestration.

The aigovclaw runtime is distinct from the aigovops catalogue. Plugins in
aigovops generate artifacts (audit logs, risk registers, etc). Modules in
aigovclaw decide what to do with those artifacts, ask for approval when
required, take action, record audit entries, and roll back on failure.
"""
