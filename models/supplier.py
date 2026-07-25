from datetime import datetime
from database.db import query_db, execute_db

class Supplier:
    def __init__(self, id, name, phone, email=None, gst_number=None, balance=0.0, created_at=None):
        self.id = id
        self.name = name
        self.phone = phone
        self.email = email
        self.gst_number = gst_number
        self.balance = float(balance)
        self.created_at = created_at

    @classmethod
    def get_by_id(cls, supplier_id):
        """Fetch supplier by primary key ID from database."""
        row = query_db("SELECT * FROM suppliers WHERE id = %s", (supplier_id,), one=True)
        if row:
            return cls(
                id=row['id'],
                name=row['name'],
                phone=row['phone'],
                email=row['email'],
                gst_number=row['gst_number'],
                balance=row['balance'],
                created_at=row.get('created_at')
            )
        return None

    @classmethod
    def get_all(cls):
        """Fetch list of all suppliers ordered by name."""
        rows = query_db("SELECT * FROM suppliers ORDER BY name ASC")
        return [cls(
            id=r['id'],
            name=r['name'],
            phone=r['phone'],
            email=r['email'],
            gst_number=r['gst_number'],
            balance=r['balance'],
            created_at=r.get('created_at')
        ) for r in rows]

    @classmethod
    def create(cls, name, phone, email=None, gst_number=None, balance=0.0):
        """Creates a supplier entry in database."""
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        s_id = execute_db(
            "INSERT INTO suppliers (name, phone, email, gst_number, balance, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, phone, email, gst_number, float(balance), created_at)
        )
        if not s_id:
            # Fallback
            rows = query_db("SELECT id FROM suppliers WHERE name = %s AND phone = %s ORDER BY id DESC", (name, phone))
            if rows:
                s_id = rows[0]['id']
        return cls(s_id, name, phone, email, gst_number, float(balance), created_at)

    def update(self, name, phone, email=None, gst_number=None, balance=None):
        """Updates supplier record properties in database."""
        b = self.balance if balance is None else float(balance)
        execute_db(
            "UPDATE suppliers SET name = %s, phone = %s, email = %s, gst_number = %s, balance = %s WHERE id = %s",
            (name, phone, email, gst_number, b, self.id)
        )
        self.name = name
        self.phone = phone
        self.email = email
        self.gst_number = gst_number
        self.balance = b

    def update_balance(self, amount):
        """Adjusts the outstanding balance."""
        new_balance = self.balance + float(amount)
        execute_db("UPDATE suppliers SET balance = %s WHERE id = %s", (new_balance, self.id))
        self.balance = new_balance

    def get_supplied_products(self):
        """Fetch all products associated with this supplier."""
        return query_db("SELECT * FROM products WHERE supplier_id = %s ORDER BY name ASC", (self.id,))

    def delete(self):
        """Delete supplier and dissociate from products."""
        execute_db("UPDATE products SET supplier_id = NULL WHERE supplier_id = %s", (self.id,))
        execute_db("DELETE FROM suppliers WHERE id = %s", (self.id,))
