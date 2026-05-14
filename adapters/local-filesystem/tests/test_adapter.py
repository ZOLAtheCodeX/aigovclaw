"""Tests for the local-filesystem adapter."""

from __future__ import annotations

import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

# Add the local-filesystem directory to sys.path so we can import adapter directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import adapter  # noqa: E402
from adapter import LocalFilesystemAdapter, SUPPORTED_ARTIFACT_TYPES # noqa: E402


def test_push_artifact_unsupported_type():
    adapter_instance = LocalFilesystemAdapter()
    result = adapter_instance.push_artifact({}, "unsupported-type")
    assert result["status"] == "error"
    assert result["destination_ref"] is None
    assert "unsupported artifact_type" in result["error"]
    assert "pushed_at" in result


def test_push_artifact_not_dict():
    adapter_instance = LocalFilesystemAdapter()
    result = adapter_instance.push_artifact("not a dict", SUPPORTED_ARTIFACT_TYPES[0])
    assert result["status"] == "error"
    assert result["destination_ref"] is None
    assert result["error"] == "artifact must be a dict"
    assert "pushed_at" in result


def test_push_artifact_success():
    with tempfile.TemporaryDirectory() as tmpdirname:
        adapter_instance = LocalFilesystemAdapter({"base_path": tmpdirname})
        artifact = {"key": "value"}
        artifact_type = SUPPORTED_ARTIFACT_TYPES[0]
        result = adapter_instance.push_artifact(artifact, artifact_type)

        assert result["status"] == "ok"
        assert result["error"] is None
        assert "destination_ref" in result
        assert "pushed_at" in result
        assert "action_tag" in result
        assert "adapter_name" in result
        assert "adapter_version" in result

        # Check if the file was actually written
        import os
        assert os.path.exists(result["destination_ref"])

        with open(result["destination_ref"], "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["key"] == "value"


def test_push_artifact_write_failure():
    with tempfile.TemporaryDirectory() as tmpdirname:
        adapter_instance = LocalFilesystemAdapter({"base_path": tmpdirname})
        artifact = {"key": "value"}
        artifact_type = SUPPORTED_ARTIFACT_TYPES[0]

        # Force a write error by mocking the Path.write_text method
        def mock_write_text(self, *args, **kwargs):
            raise OSError("mocked write error")

        with patch.object(Path, "write_text", new=mock_write_text):
            result = adapter_instance.push_artifact(artifact, artifact_type)

        assert result["status"] == "error"
        assert result["destination_ref"] is None
        assert "write failed: mocked write error" in result["error"]
        assert "pushed_at" in result


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
            import traceback
            traceback.print_exc()

    print(f"Ran {len(tests)} tests: {len(tests) - len(failures)} passed, {len(failures)} failed")
    for name, reason in failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    _run_all()
