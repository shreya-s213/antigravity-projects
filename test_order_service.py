import unittest
from unittest.mock import Mock
from order_service import Order, InventoryService, PaymentGateway, InventoryShortageError, PaymentFailedError, InvalidOrderError

class TestOrder(unittest.TestCase):

    def setUp(self):
        self.inventory = Mock(spec=InventoryService)
        self.payment = Mock(spec=PaymentGateway)
        self.order = Order(self.inventory, self.payment, "test@example.com")

    def test_add_item_normal(self):
        self.order.add_item("prod1", 10.0, 2)
        self.assertEqual(self.order.items["prod1"], {"price": 10.0, "qty": 2})

    def test_add_item_existing_product(self):
        self.order.add_item("prod1", 10.0, 1)
        self.order.add_item("prod1", 10.0, 2)
        self.assertEqual(self.order.items["prod1"]["qty"], 3)

    def test_add_item_negative_price(self):
        with self.assertRaises(ValueError):
            self.order.add_item("prod1", -10.0, 1)

    def test_add_item_zero_quantity(self):
        with self.assertRaises(ValueError):
            self.order.add_item("prod1", 10.0, 0)

    def test_remove_item(self):
        self.order.add_item("prod1", 10.0, 1)
        self.order.remove_item("prod1")
        self.assertNotIn("prod1", self.order.items)

    def test_remove_item_nonexistent(self):
        self.order.remove_item("prod1")  # Should not raise error

    def test_total_price(self):
        self.order.add_item("prod1", 10.0, 2)
        self.order.add_item("prod2", 5.0, 3)
        self.assertEqual(self.order.total_price, 35.0)

    def test_apply_discount_vip(self):
        self.order.is_vip = True
        self.order.add_item("prod1", 100.0, 1)
        self.assertEqual(self.order.apply_discount(), 80.0)

    def test_apply_discount_regular_over_100(self):
        self.order.add_item("prod1", 50.0, 3)  # 150
        self.assertEqual(self.order.apply_discount(), 135.0)

    def test_apply_discount_regular_under_100(self):
        self.order.add_item("prod1", 50.0, 1)
        self.assertEqual(self.order.apply_discount(), 50.0)

    def test_checkout_empty_cart(self):
        with self.assertRaises(InvalidOrderError):
            self.order.checkout()

    def test_checkout_stock_shortage(self):
        self.order.add_item("prod1", 10.0, 5)
        self.inventory.get_stock.return_value = 3
        with self.assertRaises(InventoryShortageError):
            self.order.checkout()

    def test_checkout_payment_fail(self):
        self.order.add_item("prod1", 10.0, 1)
        self.inventory.get_stock.return_value = 5
        self.payment.charge.return_value = False
        with self.assertRaises(PaymentFailedError):
            self.order.checkout()

    def test_checkout_payment_exception(self):
        self.order.add_item("prod1", 10.0, 1)
        self.inventory.get_stock.return_value = 5
        self.payment.charge.side_effect = Exception("Network error")
        with self.assertRaises(PaymentFailedError):
            self.order.checkout()

    def test_checkout_success(self):
        self.order.add_item("prod1", 10.0, 2)
        self.inventory.get_stock.return_value = 5
        self.payment.charge.return_value = True
        result = self.order.checkout()
        self.assertEqual(result, {"status": "success", "charged_amount": 20.0})
        self.inventory.decrement_stock.assert_called_once_with("prod1", 2)
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.status, "COMPLETED")

    def test_checkout_success_with_discount(self):
        self.order.is_vip = True
        self.order.add_item("prod1", 100.0, 1)
        self.inventory.get_stock.return_value = 5
        self.payment.charge.return_value = True
        result = self.order.checkout()
        self.assertEqual(result, {"status": "success", "charged_amount": 80.0})
        self.inventory.decrement_stock.assert_called_once_with("prod1", 1)

if __name__ == '__main__':
    unittest.main()