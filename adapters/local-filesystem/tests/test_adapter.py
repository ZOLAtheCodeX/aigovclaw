"""Tests for the LocalFilesystemAdapter."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import adapter  # noqa: E402


def test_health_check_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {"base_path": tmpdir}
        a = adapter.LocalFilesystemAdapter(config)
        result = a.health_check()

        assert result["status"] == "ok"
        assert result["detail"] == f"writing to {tmpdir}"
        assert a.base_path.exists()
        assert not (a.base_path / ".health-probe").exists()  # Ensure probe is unlinked


def test_health_check_failure():
    # Simulate a failure when creating the directory
    with patch.object(Path, 'mkdir', side_effect=Exception('Mocked mkdir error')):
        a = adapter.LocalFilesystemAdapter({"base_path": "/mocked/path"})
        result = a.health_check()

        assert result["status"] == "error"
        assert "Mocked mkdir error" in result["detail"]


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
