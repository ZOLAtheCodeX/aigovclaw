"""Tests for the AIGovClaw Hub CLI."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from unittest import mock

# Allow running the file directly from inside the hub/tests/ directory.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hub.cli import main  # noqa: E402


def test_main_success_returns_zero() -> None:
    with mock.patch("hub.cli.build_parser") as mock_build_parser:
        mock_parser = mock.Mock()
        mock_build_parser.return_value = mock_parser
        mock_args = mock.Mock()
        mock_args.func.return_value = 0
        mock_parser.parse_args.return_value = mock_args

        result = main(["generate", "--output", "foo"])
        assert result == 0
        mock_parser.parse_args.assert_called_once_with(["generate", "--output", "foo"])
        mock_args.func.assert_called_once_with(mock_args)


def test_main_failure_returns_nonzero() -> None:
    with mock.patch("hub.cli.build_parser") as mock_build_parser:
        mock_parser = mock.Mock()
        mock_build_parser.return_value = mock_parser
        mock_args = mock.Mock()
        mock_args.func.return_value = 1
        mock_parser.parse_args.return_value = mock_args

        result = main(["serve"])
        assert result == 1


def test_main_none_returns_zero() -> None:
    with mock.patch("hub.cli.build_parser") as mock_build_parser:
        mock_parser = mock.Mock()
        mock_build_parser.return_value = mock_parser
        mock_args = mock.Mock()
        mock_args.func.return_value = None
        mock_parser.parse_args.return_value = mock_args

        result = main()
        assert result == 0
        mock_parser.parse_args.assert_called_once_with(None)


def test_main_parse_args_exit() -> None:
    with mock.patch("hub.cli.build_parser") as mock_build_parser:
        mock_parser = mock.Mock()
        mock_build_parser.return_value = mock_parser
        mock_parser.parse_args.side_effect = SystemExit(2)

        try:
            main(["--help"])
            assert False, "Should raise SystemExit"
        except SystemExit as e:
            assert e.code == 2


def _run_all() -> int:
    tests = [
        test_main_success_returns_zero,
        test_main_failure_returns_nonzero,
        test_main_none_returns_zero,
        test_main_parse_args_exit,
    ]
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {fn.__name__}: {exc}")
        except Exception as exc:
            failures += 1
            print(f"ERROR {fn.__name__}: {exc}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
