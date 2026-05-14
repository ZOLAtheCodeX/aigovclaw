"""Tests for the Local Filesystem Adapter."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import adapter  # noqa: E402


def test_supported_artifact_types():
    """Test that supported_artifact_types returns the expected list of types."""
    a = adapter.LocalFilesystemAdapter()
    types = a.supported_artifact_types()
    assert isinstance(types, list), "supported_artifact_types should return a list"
    assert types == list(adapter.SUPPORTED_ARTIFACT_TYPES), "Returned types should match the constant"


def _run_all():
    import inspect
    tests = [(n, o) for n, o in inspect.getmembers(sys.modules[__name__])
             if n.startswith("test_") and callable(o)]
    failures = []
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:
            failures.append((name, f"{type(exc).__name__}: {exc}"))
    print(f"Ran {len(tests)} tests: {len(tests) - len(failures)} passed, {len(failures)} failed")
    for name, reason in failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    _run_all()
