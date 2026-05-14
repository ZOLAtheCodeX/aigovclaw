"""Tests for the AIGovClaw Hub v2 CLI.

Standalone runnable: python3 hub/v2/tests/test_cli.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hub.v2 import cli  # noqa: E402


class V2CliMainTests(unittest.TestCase):
    @patch("hub.v2.cli._cmd_generate")
    def test_main_generate_success(self, mock_generate) -> None:
        mock_generate.return_value = 0
        argv = ["generate", "--output", "dummy.html"]
        result = cli.main(argv)
        self.assertEqual(result, 0)
        mock_generate.assert_called_once()
        args = mock_generate.call_args[0][0]
        self.assertEqual(args.output, "dummy.html")

    @patch("hub.v2.cli._cmd_generate")
    def test_main_generate_failure(self, mock_generate) -> None:
        mock_generate.return_value = 2
        argv = ["generate", "--output", "dummy.html"]
        result = cli.main(argv)
        self.assertEqual(result, 2)
        mock_generate.assert_called_once()

    @patch("hub.v2.cli._cmd_serve")
    def test_main_serve_success(self, mock_serve) -> None:
        mock_serve.return_value = 0
        argv = ["serve", "--port", "9090"]
        result = cli.main(argv)
        self.assertEqual(result, 0)
        mock_serve.assert_called_once()
        args = mock_serve.call_args[0][0]
        self.assertEqual(args.port, 9090)

    @patch("hub.v2.cli._cmd_serve")
    def test_main_implicit_zero_fallback(self, mock_serve) -> None:
        # If the invoked command returns None, main() should fallback to 0.
        mock_serve.return_value = None
        argv = ["serve", "--port", "9090"]
        result = cli.main(argv)
        self.assertEqual(result, 0)
        mock_serve.assert_called_once()

    @patch("sys.stderr", new_callable=unittest.mock.MagicMock)
    def test_main_missing_required_args(self, mock_stderr) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli.main([])
        # argparse default exit code for missing arguments is 2
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
