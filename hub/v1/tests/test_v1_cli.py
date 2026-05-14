"""Tests for the AIGovClaw Hub v1 CLI main entry point.

Standalone runnable: python3 hub/v1/tests/test_v1_cli.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hub.v1 import cli  # noqa: E402


class MainTests(unittest.TestCase):
    @patch("hub.v1.cli._cmd_generate")
    def test_main_delegates_to_generate(self, mock_generate: MagicMock) -> None:
        mock_generate.return_value = 0
        rc = cli.main(["generate", "--output", "out.html"])
        self.assertEqual(rc, 0)
        mock_generate.assert_called_once()
        args = mock_generate.call_args[0][0]
        self.assertEqual(args.cmd, "generate")
        self.assertEqual(args.output, "out.html")

    @patch("hub.v1.cli._cmd_generate")
    def test_main_returns_generate_exit_code(self, mock_generate: MagicMock) -> None:
        mock_generate.return_value = 2
        rc = cli.main(["generate", "--output", "out.html"])
        self.assertEqual(rc, 2)

    @patch("hub.v1.cli._cmd_serve")
    def test_main_delegates_to_serve(self, mock_serve: MagicMock) -> None:
        mock_serve.return_value = 0
        rc = cli.main(["serve", "--port", "9090"])
        self.assertEqual(rc, 0)
        mock_serve.assert_called_once()
        args = mock_serve.call_args[0][0]
        self.assertEqual(args.cmd, "serve")
        self.assertEqual(args.port, 9090)

    @patch("hub.v1.cli._cmd_serve")
    def test_main_returns_serve_exit_code(self, mock_serve: MagicMock) -> None:
        mock_serve.return_value = 1
        rc = cli.main(["serve"])
        self.assertEqual(rc, 1)

    @patch("sys.stderr.write")
    def test_main_requires_subcommand(self, mock_stderr: MagicMock) -> None:
        with self.assertRaises(SystemExit) as cm:
            cli.main([])
        self.assertEqual(cm.exception.code, 2)


def _run_all() -> int:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(_run_all())
