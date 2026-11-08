"""Command-line and interactive-menu tests.

The menu tests feed scripted input and check printed output and saved data. They are the
safety net for refactoring run_menu, which had no tests before.
"""

import contextlib
import io
import json
import unittest
from unittest import mock

from supplydesk import cli
from supplydesk.menu import run_menu
from tests.helpers import ServiceTestCase, item


class CliTests(ServiceTestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                status = cli.main(["--data", str(self.path), *args])
            except SystemExit as exit_:  # argparse rejects bad options with SystemExit
                status = exit_.code
        return status, out.getvalue(), err.getvalue()

    def test_quote_command_prints_json_in_cents(self):
        status, out, _ = self.run_cli("quote", "--customer", "student",
                                      "--fulfillment", "delivery", "--item", "hoodie:2")
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out)["total_cents"], 7800)

    def test_rejected_command_exits_with_status_2(self):
        status, out, err = self.run_cli("place", "--item", "laptop:1")
        self.assertEqual(status, 2)
        self.assertEqual(out, "")
        self.assertIn("Error:", err)
        self.assertFalse(self.path.exists())


class MenuTests(ServiceTestCase):
    def run_menu_with(self, *lines):
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=list(lines)), \
                contextlib.redirect_stdout(out):
            status = run_menu(self.service)
        return status, out.getvalue()

    def test_readme_first_quote_shows_ten_dollars_and_saves_nothing(self):
        status, out = self.run_menu_with("2", "regular", "notebook", "2", "", "", "0")
        self.assertEqual(status, 0)
        self.assertIn("Total: $10.00", out)
        self.assertFalse(self.path.exists())

    def test_blank_prompts_default_to_regular_and_pickup(self):
        _, out = self.run_menu_with("2", "", "hoodie", "2", "", "", "0")
        self.assertIn("Customer: regular | Fulfillment: pickup", out)

    def test_place_order_after_confirming(self):
        _, out = self.run_menu_with("3", "student", "hoodie", "2", "", "delivery", "y", "0")
        self.assertIn("ORD-0001 - placed", out)
        self.assertIn("Total: $78.00", out)
        self.assertEqual(self.stock_of("hoodie"), 3)

    def test_declining_placement_saves_nothing(self):
        _, out = self.run_menu_with("3", "", "mug", "1", "", "", "n", "0")
        self.assertIn("Order not placed.", out)
        self.assertFalse(self.path.exists())

    def test_history_find_and_cancel(self):
        self.service.place_order("regular", [item("mug", 2)])
        _, out = self.run_menu_with("4", "5", "ORD-0001", "6", "ORD-0001", "y", "0")
        self.assertEqual(out.count("ORD-0001 - placed"), 2)
        self.assertIn("ORD-0001 - cancelled", out)
        self.assertEqual(self.stock_of("mug"), 8)

    def test_invalid_request_shows_error_and_returns_to_menu(self):
        _, out = self.run_menu_with("3", "", "laptop", "1", "", "", "1", "0")
        self.assertIn("Error: Unknown product.", out)
        self.assertIn("Campus hoodie", out)  # option 1 still worked afterwards
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
