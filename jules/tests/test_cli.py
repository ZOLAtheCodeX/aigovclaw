"""
Tests for the Jules CLI.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from jules.cli import main  # noqa: E402


class TestCliMain(unittest.TestCase):
    @patch("jules.cli._DISPATCH")
    @patch("jules.cli._build_parser")
    def test_main_dispatch(self, mock_build_parser, mock_dispatch):
        mock_parser = MagicMock()
        mock_build_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.command = "enqueue"
        mock_parser.parse_args.return_value = mock_args

        mock_handler = MagicMock(return_value=0)
        mock_dispatch.get.return_value = mock_handler

        # Test successful handler dispatch
        result = main(
            [
                "enqueue",
                "--type",
                "test",
                "--playbook",
                "test",
                "--target-repo",
                "test",
            ]
        )

        self.assertEqual(result, 0)
        mock_build_parser.assert_called_once()
        mock_parser.parse_args.assert_called_once_with(
            [
                "enqueue",
                "--type",
                "test",
                "--playbook",
                "test",
                "--target-repo",
                "test",
            ]
        )
        mock_dispatch.get.assert_called_once_with("enqueue")
        mock_handler.assert_called_once_with(mock_args)

    @patch("jules.cli._DISPATCH")
    @patch("jules.cli._build_parser")
    def test_main_invalid_command_fallback(self, mock_build_parser, mock_dispatch):
        # Even if parse_args succeeds but the command is somehow not in _DISPATCH
        mock_parser = MagicMock()
        mock_build_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.command = "unknown_command"
        mock_parser.parse_args.return_value = mock_args

        mock_dispatch.get.return_value = None

        # Test missing handler returns 2 and prints help
        result = main(["unknown_command"])

        self.assertEqual(result, 2)
        mock_parser.print_help.assert_called_once()
        mock_dispatch.get.assert_called_once_with("unknown_command")


def _run_all() -> int:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(_run_all())
