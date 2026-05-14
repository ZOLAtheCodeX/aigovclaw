"""Tests for the AIGovClaw Hub v2 CLI main function."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hub.v2.cli import main  # noqa: E402


class TestCliMain(unittest.TestCase):
    @patch("hub.v2.cli.build_parser")
    def test_main_with_explicit_argv(self, mock_build_parser):
        """Test main passes provided argv to parse_args and returns func result."""
        mock_parser = MagicMock()
        mock_build_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.func.return_value = 42
        mock_parser.parse_args.return_value = mock_args

        argv = ["generate", "--output", "test.html"]
        result = main(argv)

        mock_parser.parse_args.assert_called_once_with(argv)
        mock_args.func.assert_called_once_with(mock_args)
        self.assertEqual(result, 42)

    @patch("hub.v2.cli.build_parser")
    def test_main_with_none_argv(self, mock_build_parser):
        """Test main passes None to parse_args when no argv provided."""
        mock_parser = MagicMock()
        mock_build_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.func.return_value = 0
        mock_parser.parse_args.return_value = mock_args

        result = main()

        mock_parser.parse_args.assert_called_once_with(None)
        mock_args.func.assert_called_once_with(mock_args)
        self.assertEqual(result, 0)

    @patch("hub.v2.cli.build_parser")
    def test_main_func_returns_none(self, mock_build_parser):
        """Test main returns 0 when func returns None."""
        mock_parser = MagicMock()
        mock_build_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.func.return_value = None
        mock_parser.parse_args.return_value = mock_args

        result = main(["serve"])

        mock_parser.parse_args.assert_called_once_with(["serve"])
        mock_args.func.assert_called_once_with(mock_args)
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
