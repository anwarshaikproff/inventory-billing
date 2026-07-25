import os
import unittest
from datetime import datetime

# Force Mock SQLite Mode for testing to prevent modifying production DB
os.environ['FORCE_MOCK'] = 'True'
if 'DATABASE_HOST' in os.environ:
    del os.environ['DATABASE_HOST']
if 'DATABASE_URL' in os.environ:
    del os.environ['DATABASE_URL']

from database.db import init_db, query_db
from models.user import User
from models.product import Product
from models.customer import Customer
from models.supplier import Supplier
from models.offer import Offer
from models.sale import Sale

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'database_test.db')

class TestInventorySystem(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Initialise clean database instance for verification tests."""
        print("Setting up automated verification database environment...")
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except:
                pass
        # Initialize SQLite database schemas & seed defaults on startup
        init_db()

    @classmethod
    def tearDownClass(cls):
        """Restore original user database state after validation."""
        print("\nCleaning up verification database sandbox...")
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except:
                pass

    def test_01_user_authentication(self):
        """Verify password hashing authentication logic & permission hierarchies."""
        print("Testing User Authentication & Permissions...")
        
        admin = User.authenticate('admin', 'admin123')
        self.assertIsNotNone(admin)
        self.assertEqual(admin.role, 'Admin')
        self.assertTrue(admin.has_permission('Employee'))
        self.assertTrue(admin.has_permission('Cashier'))

        emp = User.authenticate('employee', 'emp123')
        self.assertIsNotNone(emp)
        self.assertEqual(emp.role, 'Employee')
        self.assertTrue(emp.has_permission('Cashier'))
        self.assertFalse(emp.has_permission('Admin'))

    def test_02_product_creation(self):
        """Verify product properties, constraints, and unique indexes checks."""
        print("Testing Product Inventory Creation & SKU integrity...")
        
        supplier = Supplier.create("Prime Distributors", "+91 9000000001", "prime@dist.com")
        self.assertIsNotNone(supplier.id)

        p1 = Product.create(
            name="Wireless Mouse",
            product_id="ELE-MOU-01",
            barcode="1000000001",
            qrcode="1000000001",
            category="Electronics",
            brand="Logitech",
            supplier_id=supplier.id,
            purchase_price=400.0,
            mrp=999.0,
            selling_price=800.0,
            gst=18.0,
            discount=5.0,
            quantity=50.0,
            unit="pcs"
        )
        self.assertIsNotNone(p1.id)
        self.assertEqual(p1.selling_price, 800.0)

        with self.assertRaises(ValueError):
            Product.create(
                name="Duplicate SKU Mouse",
                product_id="ELE-MOU-01",
                purchase_price=500.0,
                mrp=999.0,
                selling_price=800.0,
                quantity=10.0
            )

    def test_03_discount_engine(self):
        """Verify calculations for BOGO, Percentage, Flat, and demographic coupons."""
        print("Testing Multi-tier Discount Engine Calculations...")
        
        # Seed test offers
        Offer.create("BOGO Bundle Sales", "BOGO", 100.0, 0.0, None, None, None, 1)
        Offer.create("PROMO10", "Percentage", 10.0, 500.0, "PROMO10", None, None, 1)

        cart_items = [
            {
                "product_id": 1,
                "selling_price": 800.0,
                "quantity": 2.0,
                "product_discount_pct": 5.0
            }
        ]

        res_bogo = Offer.calculate_bill_discount(cart_items)
        self.assertEqual(res_bogo["item_discounts"][1], 880.0)

        res_coupon = Offer.calculate_bill_discount(cart_items, coupon_code="PROMO10")
        self.assertEqual(res_coupon["coupon_discount"], 72.0)

    def test_04_pos_checkout_transaction(self):
        """Verify transaction checkouts, inventory stock reduction, and loyalty point increases."""
        print("Testing POS checkout transactional processing...")
        
        cust = Customer.create("Anwar Hossain", "+91 9888877777", "anwar@email.com")
        self.assertEqual(cust.reward_points, 0)
        
        # Check product stock of product ID 1
        p_before = Product.get_by_id(1)
        self.assertEqual(p_before.quantity, 50.0)

        cart = [{"product_id": 1, "quantity": 2.0}]
        
        # Get active cashier user ID from seeded users
        cashier = User.get_by_username('cashier')
        
        invoice_num = Sale.create_transaction(
            customer_id=cust.id,
            cashier_id=cashier.id,
            cart_items=cart,
            payment_mode="Cash",
            cash_received=2000.0,
            coupon_code=None
        )
        self.assertTrue(invoice_num.startswith("INV-"))

        p_after = Product.get_by_id(1)
        self.assertEqual(p_after.quantity, 48.0)

        cust_after = Customer.get_by_id(cust.id)
        self.assertEqual(cust_after.reward_points, 8)

    def test_05_admin_registration(self):
        """Verify new Admin registration validations and unique checks."""
        print("Testing Admin Registration & Unique constraints...")
        
        admin = User.create(
            username="new_admin",
            password="password123",
            role="Admin",
            email="new_admin@store.com",
            full_name="New Admin User",
            phone="+91 9999988888"
        )
        self.assertIsNotNone(admin)
        self.assertEqual(admin.username, "new_admin")
        self.assertEqual(admin.full_name, "New Admin User")
        
        with self.assertRaises(ValueError):
            User.create(
                username="new_admin",
                password="diffpassword",
                role="Admin",
                email="another@store.com"
            )
            
        with self.assertRaises(ValueError):
            User.create(
                username="another_admin",
                password="diffpassword",
                role="Admin",
                email="new_admin@store.com"
            )

    def test_06_cancel_transaction(self):
        """Verify transaction cancellation, stock restoration, and history logs."""
        print("Testing Invoice Cancellation & Stock Restoration...")
        
        # 1. Register a product with initial stock = 10
        p = Product.create(
            name="Test Mouse for Cancellation",
            product_id="TEST-MOU-09",
            barcode="9000000009",
            purchase_price=100.0,
            mrp=250.0,
            selling_price=200.0,
            quantity=10.0
        )
        self.assertEqual(p.quantity, 10.0)
        
        # 2. Make a sale of 3 units
        cart = [{"product_id": p.id, "quantity": 3.0}]
        cashier = User.get_by_username('cashier')
        
        invoice_num = Sale.create_transaction(
            customer_id=None,
            cashier_id=cashier.id,
            cart_items=cart,
            payment_mode="UPI",
            cash_received=0.0
        )
        
        p_sold = Product.get_by_id(p.id)
        self.assertEqual(p_sold.quantity, 7.0)
        
        # 3. Cancel the transaction
        success = Sale.cancel_transaction(invoice_num)
        self.assertTrue(success)
        
        p_restored = Product.get_by_id(p.id)
        self.assertEqual(p_restored.quantity, 10.0)
        
        sale_details = Sale.get_invoice_details(invoice_num)
        self.assertEqual(sale_details['sale']['status'], 'Cancelled')
        
        logs = query_db("SELECT action FROM inventory_history WHERE product_id = %s", (p.id,))
        actions = [log['action'] for log in logs]
        self.assertIn('Returned', actions)

    def test_07_api_endpoints(self):
        """Verify new Flask REST API endpoints return secure JSON and function correctly."""
        print("Testing Flask JSON REST API Endpoints...")
        from app import create_app
        flask_app = create_app()
        flask_app.config['TESTING'] = True
        client = flask_app.test_client()

        # 1. Test login
        resp = client.post('/api/auth/login', json={
            "username": "admin",
            "password": "admin123"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["role"], "Admin")

        # Session is now established in client context
        # 2. Test Get products
        resp = client.get('/api/products')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["products"], list)

        # 3. Test Add product
        resp = client.post('/api/products', json={
            "name": "API Bluetooth Speaker",
            "product_id": "API-SPK-99",
            "purchase_price": 500.0,
            "mrp": 1200.0,
            "selling_price": 1000.0,
            "quantity": 15.0
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertTrue(data["success"])

        # 4. Test Get Customers
        resp = client.get('/api/customers')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["customers"], list)

        # 5. Test POS Checkout
        resp = client.post('/api/pos/checkout', json={
            "cart_items": [{"product_id": 1, "quantity": 1.0}],
            "payment_mode": "UPI"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["invoice_number"].startswith("INV-"))

        # 6. Test Reports
        resp = client.get('/api/reports?type=sales')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["data"], list)

if __name__ == '__main__':
    unittest.main()
