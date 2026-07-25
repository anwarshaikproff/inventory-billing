from datetime import datetime
from utils.security import check_password, hash_password
from database.db import query_db, execute_db

class User:
    def __init__(self, id, username, role, email, status='active', full_name=None, phone=None, last_login=None, created_at=None):
        self.id = id
        self.username = username
        self.role = role
        self.email = email
        self.status = status
        self.full_name = full_name
        self.phone = phone
        self.last_login = last_login
        self.created_at = created_at

    @classmethod
    def get_by_id(cls, user_id):
        """Fetch user by primary key ID from database."""
        u = query_db("SELECT * FROM users WHERE id = %s", (user_id,), one=True)
        if u:
            return cls(
                id=u['id'],
                username=u['username'],
                role=u['role'],
                email=u['email'],
                status=u['status'],
                full_name=u['full_name'],
                phone=u['phone'],
                last_login=u['last_login'],
                created_at=u.get('created_at')
            )
        return None

    @classmethod
    def get_by_username(cls, username):
        """Fetch user by username from database."""
        u = query_db("SELECT * FROM users WHERE username = %s", (username,), one=True)
        if u:
            return cls(
                id=u['id'],
                username=u['username'],
                role=u['role'],
                email=u['email'],
                status=u['status'],
                full_name=u['full_name'],
                phone=u['phone'],
                last_login=u['last_login'],
                created_at=u.get('created_at')
            )
        return None

    @classmethod
    def get_by_email(cls, email):
        """Fetch user by email address."""
        u = query_db("SELECT * FROM users WHERE email = %s", (email,), one=True)
        if u:
            return cls(
                id=u['id'],
                username=u['username'],
                role=u['role'],
                email=u['email'],
                status=u['status'],
                full_name=u['full_name'],
                phone=u['phone'],
                last_login=u['last_login'],
                created_at=u.get('created_at')
            )
        return None

    @classmethod
    def authenticate(cls, username, password):
        """
        Authenticate a user by username and password against database records.
        Logs the attempt to login_history and updates last_login timestamp.
        """
        u = query_db("SELECT * FROM users WHERE username = %s", (username,), one=True)
        try:
            from flask import request
            ip = request.remote_addr if request else 'Unknown'
        except:
            ip = 'Unknown'

        if not u:
            return None

        if check_password(password, u['password_hash']):
            if u['status'] == 'active':
                execute_db(
                    "INSERT INTO login_history (user_id, ip_address, status) VALUES (%s, %s, %s)",
                    (u['id'], ip, 'Success')
                )
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                execute_db("UPDATE users SET last_login = %s WHERE id = %s", (now_str, u['id']))
                return cls(
                    id=u['id'],
                    username=u['username'],
                    role=u['role'],
                    email=u['email'],
                    status=u['status'],
                    full_name=u['full_name'],
                    phone=u['phone'],
                    last_login=now_str,
                    created_at=u.get('created_at')
                )
            else:
                execute_db(
                    "INSERT INTO login_history (user_id, ip_address, status) VALUES (%s, %s, %s)",
                    (u['id'], ip, 'Inactive Account')
                )
        else:
            execute_db(
                "INSERT INTO login_history (user_id, ip_address, status) VALUES (%s, %s, %s)",
                (u['id'], ip, 'Failed Password')
            )
        return None

    @classmethod
    def create(cls, username, password, role, email, full_name=None, phone=None):
        """Create a new user in database with hashed password."""
        if cls.get_by_username(username):
            raise ValueError("Username already exists.")
        if email and cls.get_by_email(email):
            raise ValueError("Email already exists.")

        password_hash = hash_password(password)
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        u_id = execute_db(
            "INSERT INTO users (username, password_hash, role, email, status, full_name, phone, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (username, password_hash, role, email, 'active', full_name, phone, now_str)
        )
        # Fallback if execution doesn't return ID directly
        if not u_id:
            db_user = cls.get_by_username(username)
            if db_user:
                u_id = db_user.id
                
        return cls(u_id, username, role, email, 'active', full_name, phone, None, now_str)

    @classmethod
    def get_all(cls):
        """Retrieve all users in the system."""
        rows = query_db("SELECT * FROM users ORDER BY id ASC")
        return [cls(
            id=r['id'],
            username=r['username'],
            role=r['role'],
            email=r['email'],
            status=r['status'],
            full_name=r['full_name'],
            phone=r['phone'],
            last_login=r['last_login'],
            created_at=r.get('created_at')
        ) for r in rows]

    def update_password(self, new_password):
        """Update user's password securely."""
        new_hash = hash_password(new_password)
        execute_db("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, self.id))

    def update_details(self, role, email, status, full_name=None, phone=None):
        """Update role, email, active status, full name, and phone number."""
        execute_db(
            "UPDATE users SET role = %s, email = %s, status = %s, full_name = %s, phone = %s WHERE id = %s",
            (role, email, status, full_name, phone, self.id)
        )
        self.role = role
        self.email = email
        self.status = status
        self.full_name = full_name
        self.phone = phone

    def delete(self):
        """Remove a user from the system."""
        execute_db("DELETE FROM users WHERE id = %s", (self.id,))

    def has_permission(self, required_role):
        """
        Role-based Access Control checks:
        Admin has all permissions.
        Employee has access to Employee and Cashier level duties.
        Cashier only has access to Cashier duties.
        """
        role_hierarchy = {
            'Admin': ['Admin', 'Employee', 'Cashier'],
            'Employee': ['Employee', 'Cashier'],
            'Cashier': ['Cashier']
        }
        user_allowed_roles = role_hierarchy.get(self.role, [])
        return required_role in user_allowed_roles
