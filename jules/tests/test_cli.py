"""
Tests for the Jules CLI.
"""

from __future__ import annotations

import argparse
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = __file__.rsplit("jules", 1)[0]
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from jules.cli import main


class TestCliMain(unittest.TestCase):
    def test_main_dispatch_success(self):
        """Test that main delegates to the correct handler."""
        with patch("jules.cli._DISPATCH") as mock_dispatch, \
             patch("jules.cli._build_parser") as mock_build_parser:

            mock_parser = mock_build_parser.return_value
            mock_args = argparse.Namespace(command="dummy_cmd")
            mock_parser.parse_args.return_value = mock_args

            mock_handler = mock_dispatch.get.return_value
            mock_handler.return_value = 0

            result = main(["dummy_cmd"])

            self.assertEqual(result, 0)
            mock_parser.parse_args.assert_called_once_with(["dummy_cmd"])
            mock_dispatch.get.assert_called_once_with("dummy_cmd")
            mock_handler.assert_called_once_with(mock_args)

    def test_main_handler_not_found(self):
        """Test that main returns 2 if the handler is not found in _DISPATCH."""
        with patch("jules.cli._DISPATCH") as mock_dispatch, \
             patch("jules.cli._build_parser") as mock_build_parser:

            mock_parser = mock_build_parser.return_value
            mock_args = argparse.Namespace(command="unknown_cmd")
            mock_parser.parse_args.return_value = mock_args

            mock_dispatch.get.return_value = None

            result = main(["unknown_cmd"])

            self.assertEqual(result, 2)
            mock_parser.print_help.assert_called_once()

    def test_main_argv_none(self):
        """Test that main passes None to parse_args if argv is not provided."""
        with patch("jules.cli._DISPATCH") as mock_dispatch, \
             patch("jules.cli._build_parser") as mock_build_parser:

            mock_parser = mock_build_parser.return_value
            mock_args = argparse.Namespace(command="dummy_cmd")
            mock_parser.parse_args.return_value = mock_args

            mock_handler = mock_dispatch.get.return_value
            mock_handler.return_value = 0

            result = main()
            self.assertEqual(result, 0)
            mock_parser.parse_args.assert_called_once_with(None)


def _run_all() -> int:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(_run_all())
