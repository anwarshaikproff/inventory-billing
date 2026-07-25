import random
from datetime import datetime, timedelta
from database.db import query_db, execute_db
from models.product import Product, get_stock_status
from models.customer import Customer
from models.offer import Offer

class Sale:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.invoice_number = kwargs.get('invoice_number')
        self.customer_id = kwargs.get('customer_id')
        self.cashier_id = kwargs.get('cashier_id')
        self.date = kwargs.get('date')
        self.subtotal = float(kwargs.get('subtotal', 0.0))
        self.discount = float(kwargs.get('discount', 0.0))
        self.gst = float(kwargs.get('gst', 0.0))
        self.grand_total = float(kwargs.get('grand_total', 0.0))
        self.payment_mode = kwargs.get('payment_mode')
        self.cash_received = float(kwargs.get('cash_received', 0.0))
        self.balance = float(kwargs.get('balance', 0.0))
        self.status = kwargs.get('status', 'Active')

    @classmethod
    def get_by_id(cls, sale_id):
        """Fetch sale by primary key ID from database."""
        row = query_db("SELECT * FROM sales WHERE id = %s", (sale_id,), one=True)
        if row:
            return cls(**row)
        return None

    @classmethod
    def get_by_invoice(cls, invoice_num):
        """Fetch sale by invoice number from database."""
        row = query_db("SELECT * FROM sales WHERE invoice_number = %s", (invoice_num,), one=True)
        if row:
            return cls(**row)
        return None

    @classmethod
    def create_transaction(cls, customer_id, cashier_id, cart_items, payment_mode, cash_received, coupon_code=None, is_student=False):
        """
        Processes a full POS sale transaction.
        Checks stock availability, calculates discounts, computes GST, creates invoice records, 
        updates inventory quantities, creates audit logs, and adds loyalty reward points.
        """
        if not cart_items:
            raise ValueError("Cart is empty.")

        # 1. Validate stock and gather item prices
        discount_payload = []
        validated_items = []
        
        for item in cart_items:
            p_id = int(item['product_id'])
            qty = float(item['quantity'])
            
            product = Product.get_by_id(p_id)
            if not product:
                raise ValueError(f"Product with ID '{p_id}' not found.")
            
            if product.quantity < qty:
                raise ValueError(f"Insufficient stock for '{product.name}'. Available: {product.quantity} {product.unit}, Requested: {qty}.")
            
            discount_payload.append({
                "product_id": product.id,
                "selling_price": product.selling_price,
                "quantity": qty,
                "product_discount_pct": product.discount
            })
            validated_items.append((product, qty))

        # 2. Get customer (for loyalty tier)
        cust = None
        customer_membership = None
        customer_age = None
        if customer_id:
            cust = Customer.get_by_id(customer_id)
            if cust:
                if cust.reward_points > 500:
                    customer_membership = 'Gold'
                elif cust.reward_points > 200:
                    customer_membership = 'Silver'

        # 3. Calculate discounts using the Offer engine
        disc_results = Offer.calculate_bill_discount(
            cart_items=discount_payload,
            coupon_code=coupon_code,
            customer_membership=customer_membership,
            customer_age=customer_age,
            is_student=is_student
        )

        # 4. Calculate Subtotals, Item Discounts, and GST taxes
        invoice_subtotal = 0.0
        invoice_discount = 0.0
        invoice_gst = 0.0
        
        sales_items_payload = []
        
        for product, qty in validated_items:
            base_price = product.selling_price
            item_base_total = base_price * qty
            invoice_subtotal += item_base_total
            
            item_disc = disc_results["item_discounts"].get(product.id, 0.0)
            item_sub = item_base_total - item_disc
            
            overall_subtotal_before_global_disc = sum(
                (float(p.selling_price) * q) - disc_results["item_discounts"].get(p.id, 0.0)
                for p, q in validated_items
            )
            
            global_disc_ratio = item_sub / overall_subtotal_before_global_disc if overall_subtotal_before_global_disc > 0 else 0.0
            global_item_disc = (
                disc_results["coupon_discount"] +
                disc_results["membership_discount"] +
                disc_results["special_demographic_discount"]
            ) * global_disc_ratio
            
            final_item_disc = item_disc + global_item_disc
            invoice_discount += final_item_disc
            
            final_item_subtotal = item_base_total - final_item_disc
            
            gst_rate = product.gst
            item_gst = final_item_subtotal * (gst_rate / 100.0)
            invoice_gst += item_gst
            
            sales_items_payload.append({
                "product_id": product.id,
                "quantity": qty,
                "mrp": product.mrp,
                "selling_price": base_price,
                "discount": final_item_disc,
                "gst": item_gst,
                "subtotal": final_item_subtotal
            })

        # Calculate Totals
        grand_total = invoice_subtotal - invoice_discount + invoice_gst
        final_grand_total = round(grand_total)
        
        balance = 0.0
        if payment_mode == 'Cash':
            balance = float(cash_received) - final_grand_total
            if balance < 0:
                raise ValueError(f"Insufficient cash received. Grand Total: {final_grand_total}, Received: {cash_received}")

        # 5. Generate Unique Invoice ID
        date_str = datetime.now().strftime('%Y%m%d')
        rand_suffix = "".join(random.choices("0123456789", k=4))
        invoice_number = f"INV-{date_str}-{rand_suffix}"

        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 6. Execute transactions (Insert sale)
        sale_id = execute_db(
            """INSERT INTO sales (
                invoice_number, customer_id, cashier_id, date, subtotal, discount, gst, grand_total, payment_mode, cash_received, balance, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                invoice_number, customer_id, cashier_id, created_at,
                invoice_subtotal, invoice_discount, invoice_gst, final_grand_total,
                payment_mode, float(cash_received), balance, 'Active'
            )
        )

        if not sale_id:
            row = query_db("SELECT id FROM sales WHERE invoice_number = %s", (invoice_number,), one=True)
            if row:
                sale_id = row['id']

        # 7. Insert sale items, update stock, and log inventory history
        for s_item in sales_items_payload:
            execute_db(
                """INSERT INTO sales_items (
                    sale_id, product_id, quantity, mrp, selling_price, discount, gst, subtotal
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    sale_id, s_item["product_id"], s_item["quantity"], s_item["mrp"],
                    s_item["selling_price"], s_item["discount"], s_item["gst"], s_item["subtotal"]
                )
            )
            
            # Reduce inventory stock
            execute_db(
                "UPDATE products SET quantity = quantity - %s WHERE id = %s",
                (s_item["quantity"], s_item["product_id"])
            )
            
            # Update stock status
            p_ref = query_db("SELECT quantity FROM products WHERE id = %s", (s_item["product_id"],), one=True)
            if p_ref:
                new_status = get_stock_status(p_ref['quantity'])
                execute_db("UPDATE products SET stock_status = %s WHERE id = %s", (new_status, s_item["product_id"]))
            
            # Log to history
            execute_db(
                "INSERT INTO inventory_history (product_id, action, quantity, source_dest, notes, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
                (s_item["product_id"], 'Sale', s_item["quantity"], 'Store', f"Invoice: {invoice_number}", created_at)
            )

        # 8. Add Reward Points
        if cust:
            earned_points = int(final_grand_total // 100)
            cust.add_reward_points(earned_points)

        return invoice_number

    @classmethod
    def get_invoice_details(cls, invoice_num):
        """Fetch invoice main and item details from database."""
        sale_data = query_db("SELECT * FROM sales WHERE invoice_number = %s", (invoice_num,), one=True)
        if not sale_data:
            return None
            
        sale_id = sale_data['id']
        
        # Fetch items
        items = query_db(
            """SELECT si.*, COALESCE(p.name, 'Deleted Product') AS product_name, p.unit, p.product_id AS custom_product_id, p.gst AS gst_rate
               FROM sales_items si
               LEFT JOIN products p ON si.product_id = p.id
               WHERE si.sale_id = %s""",
            (sale_id,)
        )
        
        # Fetch cashier username
        cashier_row = query_db("SELECT username FROM users WHERE id = %s", (sale_data['cashier_id'],), one=True)
        cashier_name = cashier_row['username'] if cashier_row else 'Unknown'
        
        # Fetch customer details
        customer = None
        cust_id = sale_data.get('customer_id')
        if cust_id:
            customer = query_db("SELECT * FROM customers WHERE id = %s", (cust_id,), one=True)

        return {
            "sale": sale_data,
            "items": items,
            "cashier": cashier_name,
            "customer": customer
        }

    @classmethod
    def get_dashboard_stats(cls):
        """Calculate and compile metrics for the dashboard view."""
        # 1. Product Stock Metrics
        total_products_row = query_db("SELECT COUNT(*) AS count FROM products", one=True)
        total_products = total_products_row['count'] if total_products_row else 0

        total_stock_row = query_db("SELECT SUM(quantity) AS sum FROM products", one=True)
        total_stock = total_stock_row['sum'] if total_stock_row and total_stock_row['sum'] is not None else 0.0

        low_stock_row = query_db("SELECT COUNT(*) AS count FROM products WHERE quantity <= 10 AND quantity > 0", one=True)
        low_stock_count = low_stock_row['count'] if low_stock_row else 0

        out_of_stock_row = query_db("SELECT COUNT(*) AS count FROM products WHERE quantity <= 0", one=True)
        out_of_stock_count = out_of_stock_row['count'] if out_of_stock_row else 0

        # Load purchase prices
        products_prices = query_db("SELECT id, purchase_price FROM products")
        products_cache = {r['id']: float(r['purchase_price']) for r in products_prices}

        # 2. Sales Metrics
        today = datetime.now().strftime('%Y-%m-%d')
        start_of_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        start_of_month = datetime.now().strftime('%Y-%m-01')

        today_sales = 0.0
        weekly_sales = 0.0
        monthly_sales = 0.0
        total_revenue = 0.0
        today_profit = 0.0

        # Fetch all sales
        sales = query_db("SELECT * FROM sales WHERE status != 'Cancelled'")
        for s in sales:
            s_date = s.get('date')
            # Extract date string
            if isinstance(s_date, datetime):
                s_date_str = s_date.strftime('%Y-%m-%d')
            else:
                s_date_str = str(s_date)[:10]

            grand_total = float(s.get('grand_total', 0.0))
            total_revenue += grand_total
            
            if s_date_str == today:
                today_sales += grand_total
            if s_date_str >= start_of_week:
                weekly_sales += grand_total
            if s_date_str >= start_of_month:
                monthly_sales += grand_total

            # Today's profit calculation
            if s_date_str == today:
                sale_items = query_db("SELECT product_id, quantity, subtotal FROM sales_items WHERE sale_id = %s", (s['id'],))
                for si in sale_items:
                    qty = float(si['quantity'])
                    subtotal = float(si['subtotal'])
                    p_purchase = products_cache.get(si['product_id'], 0.0)
                    today_profit += (subtotal - (p_purchase * qty))

        # Total Admin counts
        total_admins_row = query_db("SELECT COUNT(*) AS count FROM users WHERE role = 'Admin'", one=True)
        total_admins = total_admins_row['count'] if total_admins_row else 0

        # Total Bills (invoice records) count
        total_bills_row = query_db("SELECT COUNT(*) AS count FROM sales", one=True)
        total_bills = total_bills_row['count'] if total_bills_row else 0

        return {
            "total_products": total_products,
            "total_stock": total_stock,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "today_sales": today_sales,
            "today_profit": today_profit,
            "weekly_sales": weekly_sales,
            "monthly_sales": monthly_sales,
            "total_revenue": total_revenue,
            "total_admins": total_admins,
            "total_bills": total_bills
        }

    @classmethod
    def get_sales_charts_data(cls):
        """Fetch weekly and monthly time-series sales/profit charts data."""
        dates = []
        sales_amounts = []
        profits_amounts = []
        
        day_dates = []
        for i in range(6, -1, -1):
            day_dt = datetime.now() - timedelta(days=i)
            day_dates.append(day_dt.strftime('%Y-%m-%d'))
            dates.append(day_dt.strftime('%a'))
            
        sales_by_day = {d: 0.0 for d in day_dates}
        profit_by_day = {d: 0.0 for d in day_dates}
        
        products_prices = query_db("SELECT id, purchase_price FROM products")
        products_cache = {r['id']: float(r['purchase_price']) for r in products_prices}
        
        start_date_str = day_dates[0] + " 00:00:00"
        sales = query_db("SELECT * FROM sales WHERE date >= %s AND status != 'Cancelled'", (start_date_str,))
        
        for s in sales:
            s_date = s.get('date')
            if isinstance(s_date, datetime):
                s_date_str = s_date.strftime('%Y-%m-%d')
            else:
                s_date_str = str(s_date)[:10]

            if s_date_str in sales_by_day:
                grand_total = float(s.get('grand_total', 0.0))
                sales_by_day[s_date_str] += grand_total
                
                # Fetch items
                items = query_db("SELECT product_id, quantity, subtotal FROM sales_items WHERE sale_id = %s", (s['id'],))
                for si in items:
                    qty = float(si['quantity'])
                    subtotal = float(si['subtotal'])
                    p_purchase = products_cache.get(si['product_id'], 0.0)
                    profit_by_day[s_date_str] += (subtotal - (p_purchase * qty))

        for d in day_dates:
            sales_amounts.append(sales_by_day[d])
            profits_amounts.append(profit_by_day[d])

        return {
            "labels": dates,
            "sales": sales_amounts,
            "profits": profits_amounts
        }

    @classmethod
    def get_top_selling_products(cls, limit=5):
        """Find best selling products based on quantity sold."""
        rows = query_db(
            """SELECT p.name, SUM(si.quantity) AS total_qty, SUM(si.subtotal) AS total_rev
               FROM sales_items si
               JOIN products p ON si.product_id = p.id
               JOIN sales s ON si.sale_id = s.id
               WHERE s.status != 'Cancelled'
               GROUP BY p.name
               ORDER BY total_qty DESC
               LIMIT %s""",
            (limit,)
        )
        return [dict(r) for r in rows]

    @classmethod
    def get_least_selling_products(cls, limit=5):
        """Find slow moving products based on quantity sold."""
        rows = query_db(
            """SELECT p.name, COALESCE(SUM(si.quantity), 0) AS total_qty, COALESCE(SUM(si.subtotal), 0) AS total_rev
               FROM products p
               LEFT JOIN sales_items si ON p.id = si.product_id
               LEFT JOIN sales s ON si.sale_id = s.id AND s.status != 'Cancelled'
               GROUP BY p.name
               ORDER BY total_qty ASC
               LIMIT %s""",
            (limit,)
        )
        return [dict(r) for r in rows]

    @classmethod
    def get_all(cls):
        """Fetch all sales from database, including customer names and cashier usernames."""
        rows = query_db("SELECT * FROM sales ORDER BY date DESC")
        res = []
        for r in rows:
            d = dict(r)
            
            cashier_row = query_db("SELECT username FROM users WHERE id = %s", (d['cashier_id'],), one=True)
            d['cashier_username'] = cashier_row['username'] if cashier_row else 'Unknown'
            
            cust_id = d.get('customer_id')
            if cust_id:
                cust_row = query_db("SELECT name FROM customers WHERE id = %s", (cust_id,), one=True)
                d['customer_name'] = cust_row['name'] if cust_row else 'Walk-in'
            else:
                d['customer_name'] = 'Walk-in'
                
            res.append(d)
        return res

    @classmethod
    def cancel_transaction(cls, invoice_num):
        """Cancels a sale, restores stock, and logs inventory change."""
        sale = query_db("SELECT * FROM sales WHERE invoice_number = %s", (invoice_num,), one=True)
        if not sale:
            raise ValueError("Invoice not found.")
            
        if sale.get('status') == 'Cancelled':
            raise ValueError("Invoice is already cancelled.")
            
        sale_id = sale['id']
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 1. Fetch sale items to restore stock
        items = query_db("SELECT * FROM sales_items WHERE sale_id = %s", (sale_id,))
        for si in items:
            p_id = si['product_id']
            qty = float(si['quantity'])
            
            # Increment stock back
            execute_db("UPDATE products SET quantity = quantity + %s WHERE id = %s", (qty, p_id))
            
            # Update stock status
            p_ref = query_db("SELECT quantity FROM products WHERE id = %s", (p_id,), one=True)
            if p_ref:
                new_status = get_stock_status(p_ref['quantity'])
                execute_db("UPDATE products SET stock_status = %s WHERE id = %s", (new_status, p_id))
            
            # Log return to inventory history
            execute_db(
                "INSERT INTO inventory_history (product_id, action, quantity, source_dest, notes, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
                (p_id, 'Returned', qty, 'Customer Return', f"Cancelled Invoice: {invoice_num}", created_at)
            )
            
        # 2. Update sale status to Cancelled
        execute_db("UPDATE sales SET status = 'Cancelled' WHERE id = %s", (sale_id,))
        
        # Deduct loyalty points if customer is linked
        cust_id = sale.get('customer_id')
        if cust_id:
            cust = Customer.get_by_id(cust_id)
            if cust:
                grand_total = float(sale.get('grand_total', 0.0))
                deducted_points = int(grand_total // 100)
                cust.deduct_reward_points(deducted_points)
                
        return True
