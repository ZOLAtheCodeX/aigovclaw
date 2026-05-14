"""Tests for the local-filesystem adapter."""

from __future__ import annotations

import sys
from pathlib import Path

# Add the repository root to sys.path so we can import adapters
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import importlib.util
import os

# Load adapter.py directly since its path contains a hyphen
adapter_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'adapter.py'))
spec = importlib.util.spec_from_file_location("adapter", adapter_path)
adapter_module = importlib.util.module_from_spec(spec)
sys.modules["adapter"] = adapter_module
spec.loader.exec_module(adapter_module)

LocalFilesystemAdapter = adapter_module.LocalFilesystemAdapter
SUPPORTED_ARTIFACT_TYPES = adapter_module.SUPPORTED_ARTIFACT_TYPES

def test_supported_artifact_types():
    adapter = LocalFilesystemAdapter()
    supported_types = adapter.supported_artifact_types()

    assert isinstance(supported_types, list)
    assert len(supported_types) == len(SUPPORTED_ARTIFACT_TYPES)

    for expected_type in SUPPORTED_ARTIFACT_TYPES:
        assert expected_type in supported_types

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
