"""Service tests, grouped by the four Task 2 categories.

Based on the Checkpoint A testing strategy. Expected values come from FUNCTIONAL_SPEC.md,
not from the current implementation.
"""

import unittest

from supplydesk.service import OrderService
from tests.helpers import ServiceTestCase, item


class NormalBehaviourTests(ServiceTestCase):
    """Category 1: expected operations with valid input."""

    def test_view_catalog_shows_products_prices_and_stock(self):
        catalog = {p["product_id"]: (p["name"], p["unit_price_cents"], p["stock"])
                   for p in self.service.catalog()}
        self.assertEqual(catalog, {
            "notebook": ("Notebook", 500, 20),
            "pen-pack": ("Pen pack", 750, 10),
            "hoodie": ("Campus hoodie", 4000, 5),
            "mug": ("Campus mug", 1500, 8),
            "bag": ("Canvas bag", 2500, 4),
        })

    def test_place_order_saves_order_and_reduces_stock(self):
        order = self.service.place_order("regular", [item("notebook", 3), item("mug", 2)])
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(order["total_cents"], 3 * 500 + 2 * 1500)
        self.assertEqual(self.stock_of("notebook"), 17)
        self.assertEqual(self.stock_of("mug"), 6)

    def test_get_order_returns_the_matching_order(self):
        self.service.place_order("regular", [item("mug", 1)])
        second = self.service.place_order("student", [item("bag", 1)], "delivery")
        self.assertEqual(self.service.get_order("ORD-0002"), second)

    def test_cancel_order_restores_stock_and_keeps_history(self):
        order = self.service.place_order("regular", [item("hoodie", 2)])
        cancelled = self.service.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(self.stock_of("hoodie"), 5)
        self.assertEqual(cancelled["total_cents"], order["total_cents"])
        self.assertEqual(len(self.service.list_orders()), 1)


class BoundaryTests(ServiceTestCase):
    """Category 2: limits and edge cases."""

    def setUp(self):
        super().setUp()
        # Create a save file first so "unchanged" is checked against real saved data.
        self.service.place_order("regular", [item("notebook", 1)])

    def test_zero_quantity_is_rejected(self):
        self.assertRejectedWithoutChange(self.service.place_order, "regular", [item("mug", 0)])

    def test_negative_quantity_is_rejected(self):
        self.assertRejectedWithoutChange(self.service.place_order, "regular", [item("mug", -1)])

    def test_order_with_no_items_is_rejected(self):
        self.assertRejectedWithoutChange(self.service.place_order, "regular", [])

    def test_ordering_exactly_the_available_stock_is_allowed(self):
        self.service.place_order("regular", [item("bag", 4)])
        self.assertEqual(self.stock_of("bag"), 0)

    def test_ordering_more_than_available_stock_is_rejected(self):
        self.assertRejectedWithoutChange(self.service.place_order, "regular", [item("bag", 5)])

    def test_student_discount_applies_at_exactly_5000_cents(self):
        # Spec: 10% discount when the subtotal is AT LEAST 5,000 cents.
        quote = self.service.quote("student", [item("bag", 2)])  # 2 x 2500 = 5000
        self.assertEqual(quote["discount_cents"], 500)
        self.assertEqual(quote["total_cents"], 4500)


class InvalidInputTests(ServiceTestCase):
    """Category 3: invalid requests raise ValueError and do not change saved data."""

    def setUp(self):
        super().setUp()
        self.service.place_order("regular", [item("notebook", 1)])

    def test_unknown_product_is_rejected(self):
        self.assertRejectedWithoutChange(self.service.place_order, "regular", [item("laptop", 1)])

    def test_unknown_order_id_is_rejected(self):
        self.assertRejectedWithoutChange(self.service.get_order, "ORD-9999")

    def test_cancelling_an_already_cancelled_order_does_not_restore_stock_again(self):
        order = self.service.place_order("regular", [item("hoodie", 2)])
        self.service.cancel_order(order["order_id"])
        again = self.service.cancel_order(order["order_id"])
        self.assertEqual(again["status"], "cancelled")
        self.assertEqual(self.stock_of("hoodie"), 5)

    def test_duplicate_lines_cannot_exceed_stock_together(self):
        # Checkpoint A diagnosis 5: 19 notebooks left, two lines of 15 must be rejected.
        self.assertRejectedWithoutChange(self.service.place_order, "regular",
                                         [item("notebook", 15), item("notebook", 15)])


class PreservedBehaviourTests(ServiceTestCase):
    """Category 4: behaviour the planned refactorings must not change."""

    def test_order_ids_are_unique_sequential_and_not_reused(self):
        first = self.service.place_order("regular", [item("mug", 1)])
        self.service.cancel_order(first["order_id"])
        second = self.service.place_order("regular", [item("mug", 1)])
        self.assertEqual([first["order_id"], second["order_id"]], ["ORD-0001", "ORD-0002"])

    def test_quote_and_placed_order_agree(self):
        # Covers the regular pickup and student delivery quotes from Checkpoint A, and protects
        # refactoring of the duplicated quote()/place_order() logic.
        cases = [
            ("regular", [item("notebook", 2)], "pickup", 1000),
            ("student", [item("hoodie", 2)], "delivery", 7800),
            ("regular", [item("hoodie", 3)], "delivery", 12000),
        ]
        for customer, items, fulfillment, total in cases:
            with self.subTest(customer=customer, fulfillment=fulfillment):
                quote = self.service.quote(customer, items, fulfillment)
                order = self.service.place_order(customer, items, fulfillment)
                self.assertEqual(quote["total_cents"], total)
                for key, value in quote.items():
                    self.assertEqual(order[key], value)

    def test_quote_does_not_save_anything(self):
        self.service.quote("student", [item("hoodie", 2)], "delivery")
        self.assertFalse(self.path.exists())

    def test_orders_and_stock_survive_reopening(self):
        order = self.service.place_order("student", [item("hoodie", 2)], "delivery")
        reopened = OrderService(self.path)
        self.assertEqual(reopened.list_orders(), [order])
        self.assertEqual(self.stock_of("hoodie", reopened), 3)


if __name__ == "__main__":
    unittest.main()
