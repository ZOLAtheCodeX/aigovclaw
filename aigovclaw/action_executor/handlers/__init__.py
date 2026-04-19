"""Action-type handlers.

Each handler module exposes a handle(request, dry_run) callable that returns
an output dict. Handlers MUST NOT write audit entries themselves; the
executor does that symmetrically before and after every call.
"""
