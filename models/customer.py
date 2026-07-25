from datetime import datetime
from database.db import query_db, execute_db

class Customer:
    def __init__(self, id, name, phone, email=None, address=None, reward_points=0, created_at=None):
        self.id = id
        self.name = name
        self.phone = phone
        self.email = email
        self.address = address
        self.reward_points = int(reward_points)
        self.created_at = created_at

    @classmethod
    def get_by_id(cls, customer_id):
        """Fetch customer by primary key from database."""
        row = query_db("SELECT * FROM customers WHERE id = %s", (customer_id,), one=True)
        if row:
            return cls(
                id=row['id'],
                name=row['name'],
                phone=row['phone'],
                email=row['email'],
                address=row['address'],
                reward_points=row['reward_points'],
                created_at=row.get('created_at')
            )
        return None

    @classmethod
    def get_by_phone(cls, phone):
        """Fetch customer by unique phone number from database."""
        row = query_db("SELECT * FROM customers WHERE phone = %s", (phone,), one=True)
        if row:
            return cls(
                id=row['id'],
                name=row['name'],
                phone=row['phone'],
                email=row['email'],
                address=row['address'],
                reward_points=row['reward_points'],
                created_at=row.get('created_at')
            )
        return None

    @classmethod
    def get_all(cls):
        """Fetch list of all customers ordered by name."""
        rows = query_db("SELECT * FROM customers ORDER BY name ASC")
        return [cls(
            id=r['id'],
            name=r['name'],
            phone=r['phone'],
            email=r['email'],
            address=r['address'],
            reward_points=r['reward_points'],
            created_at=r.get('created_at')
        ) for r in rows]

    @classmethod
    def create(cls, name, phone, email=None, address=None, reward_points=0):
        """Creates customer record in database."""
        if cls.get_by_phone(phone):
            raise ValueError(f"Customer with phone number '{phone}' already registered.")

        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c_id = execute_db(
            "INSERT INTO customers (name, phone, email, address, reward_points, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, phone, email, address, int(reward_points), created_at)
        )
        if not c_id:
            row = query_db("SELECT id FROM customers WHERE phone = %s", (phone,), one=True)
            if row:
                c_id = row['id']
        return cls(c_id, name, phone, email, address, int(reward_points), created_at)

    def update(self, name, phone, email=None, address=None, reward_points=None):
        """Update customer details with uniqueness check on phone."""
        if phone != self.phone:
            existing = self.get_by_phone(phone)
            if existing:
                raise ValueError(f"Phone number '{phone}' is already registered to another customer.")

        rp = self.reward_points if reward_points is None else int(reward_points)
        execute_db(
            "UPDATE customers SET name = %s, phone = %s, email = %s, address = %s, reward_points = %s WHERE id = %s",
            (name, phone, email, address, rp, self.id)
        )
        self.name = name
        self.phone = phone
        self.email = email
        self.address = address
        self.reward_points = rp

    def add_reward_points(self, points):
        """Increments reward points upon successful sales billing."""
        new_pts = self.reward_points + int(points)
        execute_db("UPDATE customers SET reward_points = %s WHERE id = %s", (new_pts, self.id))
        self.reward_points = new_pts

    def deduct_reward_points(self, points):
        """Deducts reward points if redeemed during a sale transaction."""
        new_pts = max(0, self.reward_points - int(points))
        execute_db("UPDATE customers SET reward_points = %s WHERE id = %s", (new_pts, self.id))
        self.reward_points = new_pts

    def get_purchase_history(self):
        """Fetch all invoices corresponding to this customer."""
        return query_db("SELECT * FROM sales WHERE customer_id = %s ORDER BY date DESC", (self.id,))

    def delete(self):
        """Removes the customer from the store registry."""
        execute_db("UPDATE sales SET customer_id = NULL WHERE customer_id = %s", (self.id,))
        execute_db("DELETE FROM customers WHERE id = %s", (self.id,))
