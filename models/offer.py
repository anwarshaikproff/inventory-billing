from datetime import datetime
from database.db import query_db, execute_db

class Offer:
    def __init__(self, id, name, type, value, min_purchase=0.0, code=None, start_date=None, end_date=None, active=1):
        self.id = id
        self.name = name
        self.type = type  # 'Percentage', 'Flat', 'BOGO', 'Combo', 'Membership', 'Student', 'Senior Citizen'
        self.value = float(value)
        self.min_purchase = float(min_purchase or 0.0)
        self.code = code
        self.start_date = start_date
        self.end_date = end_date
        self.active = int(active)

    @classmethod
    def get_by_id(cls, offer_id):
        """Fetch offer by primary key ID from database."""
        row = query_db("SELECT * FROM offers WHERE id = %s", (offer_id,), one=True)
        if row:
            return cls(
                id=row['id'],
                name=row['name'],
                type=row['type'],
                value=row['value'],
                min_purchase=row['min_purchase'],
                code=row['code'],
                start_date=row['start_date'],
                end_date=row['end_date'],
                active=row['active']
            )
        return None

    @classmethod
    def get_by_code(cls, code):
        """Fetch discount offer by coupon code from database."""
        row = query_db("SELECT * FROM offers WHERE code = %s AND active = 1", (code,), one=True)
        if row:
            return cls(
                id=row['id'],
                name=row['name'],
                type=row['type'],
                value=row['value'],
                min_purchase=row['min_purchase'],
                code=row['code'],
                start_date=row['start_date'],
                end_date=row['end_date'],
                active=row['active']
            )
        return None

    @classmethod
    def get_active_offers(cls):
        """Fetch all active offers where today's date falls within range."""
        rows = query_db("SELECT * FROM offers WHERE active = 1")
        today = datetime.today().strftime('%Y-%m-%d')
        res = []
        for r in rows:
            start_date = r.get('start_date')
            end_date = r.get('end_date')
            if (not start_date or start_date <= today) and (not end_date or end_date >= today):
                res.append(cls(
                    id=r['id'],
                    name=r['name'],
                    type=r['type'],
                    value=r['value'],
                    min_purchase=r['min_purchase'],
                    code=r['code'],
                    start_date=r['start_date'],
                    end_date=r['end_date'],
                    active=r['active']
                ))
        return res

    @classmethod
    def get_all(cls):
        """Fetch all offers from database."""
        rows = query_db("SELECT * FROM offers ORDER BY id DESC")
        return [cls(
            id=r['id'],
            name=r['name'],
            type=r['type'],
            value=r['value'],
            min_purchase=r['min_purchase'],
            code=r['code'],
            start_date=r['start_date'],
            end_date=r['end_date'],
            active=r['active']
        ) for r in rows]

    @classmethod
    def create(cls, name, type, value, min_purchase=0.0, code=None, start_date=None, end_date=None, active=1):
        """Register a new offer."""
        if code:
            existing = cls.get_by_code(code)
            if existing:
                raise ValueError(f"Offer coupon code '{code}' already exists.")

        o_id = execute_db(
            "INSERT INTO offers (name, type, value, min_purchase, code, start_date, end_date, active) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (name, type, float(value), float(min_purchase), code, start_date, end_date, int(active))
        )
        if not o_id and code:
            row = query_db("SELECT id FROM offers WHERE code = %s", (code,), one=True)
            if row:
                o_id = row['id']
        return cls.get_by_id(o_id)

    def update(self, name, type, value, min_purchase=0.0, code=None, start_date=None, end_date=None, active=1):
        """Update offer properties in database."""
        if code and code != self.code:
            existing = self.get_by_code(code)
            if existing and existing.id != self.id:
                raise ValueError(f"Offer coupon code '{code}' is already registered to another offer.")

        execute_db(
            "UPDATE offers SET name = %s, type = %s, value = %s, min_purchase = %s, code = %s, start_date = %s, end_date = %s, active = %s WHERE id = %s",
            (name, type, float(value), float(min_purchase), code, start_date, end_date, int(active), self.id)
        )
        self.name = name
        self.type = type
        self.value = float(value)
        self.min_purchase = float(min_purchase)
        self.code = code
        self.start_date = start_date
        self.end_date = end_date
        self.active = int(active)

    def delete(self):
        """Delete offer from database."""
        execute_db("DELETE FROM offers WHERE id = %s", (self.id,))

    @classmethod
    def calculate_bill_discount(cls, cart_items, coupon_code=None, customer_membership=None, customer_age=None, is_student=False):
        """
        Automatically computes discount on the cart.
        """
        results = {
            "item_discounts": {},
            "coupon_discount": 0.0,
            "membership_discount": 0.0,
            "special_demographic_discount": 0.0,
            "applied_offers": []
        }
        
        subtotal = 0.0
        for item in cart_items:
            qty = float(item['quantity'])
            price = float(item['selling_price'])
            prod_disc_pct = float(item.get('product_discount_pct', 0.0))
            base_disc = price * (prod_disc_pct / 100.0) * qty
            results["item_discounts"][item['product_id']] = base_disc
            subtotal += (price * qty) - base_disc

        active_offers = cls.get_active_offers()
        
        # 1. BOGO (Buy One Get One)
        bogo_offers = [o for o in active_offers if o.type == 'BOGO']
        if bogo_offers:
            bogo = bogo_offers[0]
            for item in cart_items:
                qty = float(item['quantity'])
                if qty >= 2:
                    free_units = int(qty // 2)
                    price = float(item['selling_price'])
                    bogo_disc = free_units * price
                    results["item_discounts"][item['product_id']] += bogo_disc
                    subtotal -= bogo_disc
                    results["applied_offers"].append(f"BOGO: {bogo.name}")

        # 2. Coupon discount
        if coupon_code:
            coupon = cls.get_by_code(coupon_code)
            if coupon and subtotal >= coupon.min_purchase:
                if coupon.type == 'Percentage':
                    coupon_amt = subtotal * (coupon.value / 100.0)
                elif coupon.type == 'Flat':
                    coupon_amt = min(coupon.value, subtotal)
                else:
                    coupon_amt = 0.0
                
                results["coupon_discount"] = coupon_amt
                subtotal -= coupon_amt
                results["applied_offers"].append(f"Coupon: {coupon.name}")

        # 3. Membership Discount
        if customer_membership:
            memb_offers = [o for o in active_offers if o.type == 'Membership']
            if memb_offers:
                memb = memb_offers[0]
                memb_amt = subtotal * (memb.value / 100.0)
                results["membership_discount"] = memb_amt
                subtotal -= memb_amt
                results["applied_offers"].append(f"Membership ({customer_membership}): {memb.name}")

        # 4. Demographic discounts (Student / Senior Citizen)
        demo_disc_pct = 0.0
        demo_name = ""
        
        if customer_age and int(customer_age) >= 60:
            senior_offers = [o for o in active_offers if o.type == 'Senior Citizen']
            if senior_offers:
                demo_disc_pct = max(demo_disc_pct, senior_offers[0].value)
                demo_name = senior_offers[0].name
                
        if is_student:
            student_offers = [o for o in active_offers if o.type == 'Student']
            if student_offers:
                demo_disc_pct = max(demo_disc_pct, student_offers[0].value)
                demo_name = student_offers[0].name

        if demo_disc_pct > 0:
            demo_amt = subtotal * (demo_disc_pct / 100.0)
            results["special_demographic_discount"] = demo_amt
            subtotal -= demo_amt
            results["applied_offers"].append(f"Demographic: {demo_name}")

        return results
