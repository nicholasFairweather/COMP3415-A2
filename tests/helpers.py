"""Shared fixtures for the Campus Supply Desk test suite."""

from pathlib import Path
import json
import tempfile
import unittest

from supplydesk.service import OrderService


def item(product_id, quantity):
    return {"product_id": product_id, "quantity": quantity}


class ServiceTestCase(unittest.TestCase):
    """Gives every test its own temporary save file so tests never share state."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.json"
        self.service = OrderService(self.path)

    def stock_of(self, product_id, service=None):
        for product in (service or self.service).catalog():
            if product["product_id"] == product_id:
                return product["stock"]
        raise AssertionError("product not in catalog: " + product_id)

    def saved_bytes(self):
        return self.path.read_bytes() if self.path.exists() else None

    def saved_state(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def assertRejectedWithoutChange(self, operation, *args):
        """An invalid request raises ValueError and leaves the save file untouched."""
        before = self.saved_bytes()
        with self.assertRaises(ValueError):
            operation(*args)
        self.assertEqual(self.saved_bytes(), before)
