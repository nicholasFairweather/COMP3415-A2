"""CR-01: express delivery. Each test names the CR-01 acceptance requirement it checks."""

import contextlib
import io
import json
import unittest
from unittest import mock

from supplydesk import cli
from supplydesk.menu import run_menu
from supplydesk.service import OrderService
from tests.helpers import ServiceTestCase, item


def money_parts(order):
    return (order["subtotal_cents"], order["discount_cents"],
            order["delivery_cents"], order["total_cents"])


class ExpressTests(ServiceTestCase):
    def test_cr_example_regular_two_notebooks(self):  # R2
        quote = self.service.quote("regular", [item("notebook", 2)], "express")
        self.assertEqual(money_parts(quote), (1000, 0, 1200, 2200))

    def test_cr_example_student_two_hoodies(self):  # R2, R3
        quote = self.service.quote("student", [item("hoodie", 2)], "express")
        self.assertEqual(money_parts(quote), (8000, 800, 1200, 8400))

    def test_cr_example_three_hoodies_standard_vs_express(self):  # R2, R4
        standard = self.service.quote("regular", [item("hoodie", 3)], "delivery")
        express = self.service.quote("regular", [item("hoodie", 3)], "express")
        self.assertEqual(standard["total_cents"], 12000)  # standard still free over $100
        self.assertEqual(express["total_cents"], 13200)  # express fee never waived

    def test_discount_is_on_merchandise_not_express_fee(self):  # R3
        # 2 bags = 5000 -> discount 500. If the fee were discounted it would be 620.
        quote = self.service.quote("student", [item("bag", 2)], "express")
        self.assertEqual(money_parts(quote), (5000, 500, 1200, 5700))

    def test_express_order_kept_when_retrieved_reopened_and_cancelled(self):  # R5
        quote = self.service.quote("student", [item("hoodie", 2)], "express")
        order = self.service.place_order("student", [item("hoodie", 2)], "express")
        for key, value in quote.items():
            self.assertEqual(order[key], value)
        reopened = OrderService(self.path)
        self.assertEqual(reopened.get_order(order["order_id"]), order)
        cancelled = reopened.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        for key in ("fulfillment", "items", "delivery_cents", "discount_cents", "total_cents"):
            self.assertEqual(cancelled[key], order[key], key)
        self.assertEqual(self.stock_of("hoodie"), 5)

    def test_other_fulfillment_values_still_invalid(self):  # R6
        self.service.place_order("regular", [item("mug", 1)])
        for bad in ("Express", "overnight", ""):
            with self.subTest(fulfillment=bad):
                self.assertRejectedWithoutChange(self.service.place_order, "regular",
                                                 [item("mug", 1)], bad)


class ExpressInterfaceTests(ServiceTestCase):
    def test_cr_command_example_total_8400(self):  # R1
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = cli.main(["--data", str(self.path), "quote", "--customer", "student",
                               "--fulfillment", "express", "--item", "hoodie:2"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out.getvalue())["total_cents"], 8400)

    def test_command_help_mentions_express(self):  # R7
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            cli.main(["quote", "--help"])
        self.assertIn("express", out.getvalue())

    def test_menu_prompt_offers_express_and_places_order(self):  # R1, R7
        out = io.StringIO()
        inputs = ["3", "student", "hoodie", "2", "", "express", "y", "0"]
        with mock.patch("builtins.input", side_effect=inputs) as fake_input, \
                contextlib.redirect_stdout(out):
            run_menu(self.service)
        prompts = [call.args[0] for call in fake_input.call_args_list]
        self.assertTrue(any("express" in p and "Enter = pickup" in p for p in prompts))
        self.assertIn("Delivery: $12.00", out.getvalue())
        self.assertIn("Total: $84.00", out.getvalue())


if __name__ == "__main__":
    unittest.main()
