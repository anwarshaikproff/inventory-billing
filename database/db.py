import os
import json
import sqlite3
import pymysql
import pymysql.cursors
from datetime import datetime
from flask import g
from utils.security import hash_password

# Load environment variables from .env file if it exists
def load_env():
    """Loads environment variables from a .env file if it exists."""
    db_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(db_dir)
    env_path = os.path.join(root_dir, '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, val = line.split('=', 1)
                        key = key.strip()
                        val = val.strip()
                        if val.startswith('"') and val.endswith('"'):
                            val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"):
                            val = val[1:-1]
                        os.environ[key] = val
        except Exception as e:
            print(f"Warning: Failed to load .env file: {e}")

load_env()

# Configurable database status tracker
DB_STATUS = {
    'status': 'Disconnected',
    'last_sync_time': 'N/A',
    'db_type': 'Unknown'
}

def get_db_status():
    """Returns the current database connection statistics."""
    return DB_STATUS

def translate_query(query, is_sqlite):
    """Translates SQL parameter placeholders between SQLite (?) and MySQL (%s)."""
    if is_sqlite:
        return query.replace('%s', '?')
    return query

_CHOSEN_DB_TYPE = None

def parse_mysql_url(url):
    """Parses a mysql:// connection URL into dictionary of parameters."""
    # mysql://user:password@host:port/dbname
    try:
        if url.startswith("mysql://"):
            url = url[8:]
        elif url.startswith("mysql+pymysql://"):
            url = url[16:]
        else:
            return None
        
        user_pass, host_port_db = url.split("@", 1)
        user, password = user_pass.split(":", 1)
        
        if "/" in host_port_db:
            host_port, dbname = host_port_db.split("/", 1)
        else:
            host_port = host_port_db
            dbname = ""
            
        if ":" in host_port:
            host, port = host_port.split(":", 1)
            port = int(port)
        else:
            host = host_port
            port = 3306
            
        return {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": dbname
        }
    except Exception as e:
        print(f"Error parsing MYSQL connection URL: {e}")
        return None

def get_connection():
    """Creates a connection to MySQL (primary) or falls back to SQLite."""
    global DB_STATUS, _CHOSEN_DB_TYPE
    
    # 1. Respect FORCE_MOCK immediately
    if os.environ.get('FORCE_MOCK') == 'True':
        _CHOSEN_DB_TYPE = 'SQLite'
        try:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database_test.db')
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            DB_STATUS['status'] = 'Connected'
            DB_STATUS['db_type'] = 'SQLite (Fallback)'
            DB_STATUS['last_sync_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return conn
        except Exception as e:
            DB_STATUS['status'] = 'Disconnected'
            DB_STATUS['db_type'] = 'Unknown'
            print(f"SQLite fallback connection failed: {e}")
            raise e

    # 2. Try connection parameters from environment variables
    mysql_host = os.environ.get('MYSQL_HOST') or os.environ.get('DATABASE_HOST')
    mysql_port = os.environ.get('MYSQL_PORT') or os.environ.get('DATABASE_PORT', '3306')
    mysql_user = os.environ.get('MYSQL_USER') or os.environ.get('DATABASE_USER')
    mysql_password = os.environ.get('MYSQL_PASSWORD') or os.environ.get('DATABASE_PASSWORD')
    mysql_db = os.environ.get('MYSQL_DB') or os.environ.get('DATABASE_NAME')
    database_url = os.environ.get('DATABASE_URL')

    # Check if DATABASE_URL is a PostgreSQL URL
    if database_url and (database_url.startswith("postgresql://") or database_url.startswith("postgres://")):
        try:
            import psycopg2
            conn = psycopg2.connect(database_url, connect_timeout=15)
            _CHOSEN_DB_TYPE = 'PostgreSQL'
            DB_STATUS['status'] = 'Connected'
            DB_STATUS['db_type'] = 'PostgreSQL'
            DB_STATUS['last_sync_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return conn
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}. Falling back to SQLite.")

    mysql_params = None

    # Check if DATABASE_URL is a MySQL URL
    if database_url and (database_url.startswith("mysql://") or database_url.startswith("mysql+pymysql://")):
        mysql_params = parse_mysql_url(database_url)
    elif mysql_host:
        mysql_params = {
            "host": mysql_host,
            "port": int(mysql_port),
            "user": mysql_user,
            "password": mysql_password,
            "database": mysql_db
        }

    if mysql_params:
        try:
            conn = pymysql.connect(
                host=mysql_params["host"],
                port=mysql_params["port"],
                user=mysql_params["user"],
                password=mysql_params["password"],
                database=mysql_params["database"],
                connect_timeout=10
            )
            _CHOSEN_DB_TYPE = 'MySQL'
            DB_STATUS['status'] = 'Connected'
            DB_STATUS['db_type'] = 'MySQL'
            DB_STATUS['last_sync_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return conn
        except Exception as e:
            print(f"MySQL connection failed: {e}. Falling back to SQLite.")

    # Fall back to SQLite and set it as the chosen database type
    try:
        _CHOSEN_DB_TYPE = 'SQLite'
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        DB_STATUS['status'] = 'Connected'
        DB_STATUS['db_type'] = 'SQLite (Fallback)'
        DB_STATUS['last_sync_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return conn
    except Exception as e:
        DB_STATUS['status'] = 'Disconnected'
        DB_STATUS['db_type'] = 'Unknown'
        print(f"SQLite fallback connection failed: {e}")
        raise e

def get_db():
    """Returns database connection from Flask request context g."""
    db_conn = getattr(g, '_database', None)
    if db_conn is None:
        db_conn = g._database = get_connection()
    return db_conn

def close_db(exception=None):
    """Closes request database connection."""
    db_conn = getattr(g, '_database', None)
    if db_conn is not None:
        db_conn.close()
        g._database = None

def query_db(query, args=(), one=False):
    """Executes SELECT queries and returns rows as list of standard dictionaries."""
    conn = get_connection()
    is_sqlite = (_CHOSEN_DB_TYPE == 'SQLite')
    query = translate_query(query, is_sqlite)

    if is_sqlite:
        cur = conn.cursor()
    elif _CHOSEN_DB_TYPE == 'PostgreSQL':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cur = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cur.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        conn.close()

        if is_sqlite or _CHOSEN_DB_TYPE == 'PostgreSQL':
            res = [dict(row) for row in rv]
        else:
            res = list(rv)
            
        return (res[0] if res else None) if one else res
    except Exception as e:
        cur.close()
        conn.close()
        raise e

def execute_db(query, args=(), commit=True):
    """Executes INSERT, UPDATE, or DELETE operations and returns inserted primary keys."""
    conn = get_connection()
    is_sqlite = (_CHOSEN_DB_TYPE == 'SQLite')
    query = translate_query(query, is_sqlite)

    cur = conn.cursor()
    last_id = None
    try:
        if _CHOSEN_DB_TYPE == 'PostgreSQL' and query.strip().upper().startswith('INSERT INTO') and 'RETURNING' not in query.strip().upper() and 'INSERT INTO SETTINGS' not in query.strip().upper():
            query = query.rstrip(';') + ' RETURNING id'
            cur.execute(query, args)
            try:
                last_id = cur.fetchone()[0]
            except Exception:
                pass
        else:
            cur.execute(query, args)
            if is_sqlite or _CHOSEN_DB_TYPE == 'MySQL':
                last_id = cur.lastrowid
            
        if commit:
            conn.commit()

        cur.close()
        conn.close()
        return last_id
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        raise e

def init_db(app=None):
    """Registers standard SQL table structures and seeds defaults on system startup."""
    conn = get_connection()
    is_sqlite = (_CHOSEN_DB_TYPE == 'SQLite')
    cur = conn.cursor()

    if is_sqlite:
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT CHECK(role IN ('Admin', 'Employee', 'Cashier')) NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive')),
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                status TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT,
                address TEXT,
                reward_points INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                gst_number TEXT,
                balance REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                product_id TEXT UNIQUE NOT NULL,
                barcode TEXT UNIQUE,
                qrcode TEXT UNIQUE,
                category TEXT,
                brand TEXT,
                supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
                purchase_price REAL NOT NULL,
                mrp REAL NOT NULL,
                selling_price REAL NOT NULL,
                gst REAL DEFAULT 0.0,
                discount REAL DEFAULT 0.0,
                quantity REAL NOT NULL DEFAULT 0.0,
                unit TEXT DEFAULT 'pcs',
                weight REAL,
                expiry_date TEXT,
                mfg_date TEXT,
                description TEXT,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stock_status TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT CHECK(type IN ('Percentage', 'Flat', 'BOGO', 'Combo', 'Membership', 'Student', 'Senior Citizen')) NOT NULL,
                value REAL NOT NULL DEFAULT 0.0,
                min_purchase REAL DEFAULT 0.0,
                code TEXT UNIQUE,
                start_date TEXT,
                end_date TEXT,
                active INTEGER DEFAULT 1 CHECK(active IN (0, 1))
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT UNIQUE NOT NULL,
                customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
                cashier_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subtotal REAL NOT NULL,
                discount REAL DEFAULT 0.0,
                gst REAL DEFAULT 0.0,
                grand_total REAL NOT NULL,
                payment_mode TEXT CHECK(payment_mode IN ('Cash', 'UPI', 'Credit Card', 'Debit Card', 'Wallet')) NOT NULL,
                cash_received REAL DEFAULT 0.0,
                balance REAL DEFAULT 0.0,
                status TEXT DEFAULT 'Active'
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS sales_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER REFERENCES sales(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
                quantity REAL NOT NULL,
                mrp REAL NOT NULL,
                selling_price REAL NOT NULL,
                discount REAL DEFAULT 0.0,
                gst REAL DEFAULT 0.0,
                subtotal REAL NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS inventory_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                action TEXT CHECK(action IN ('Stock In', 'Sale', 'Damaged', 'Returned', 'Adjustment')) NOT NULL,
                quantity REAL NOT NULL,
                source_dest TEXT,
                notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS deletion_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                deleted_by TEXT NOT NULL,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                record_details TEXT
            );
            """
        ]
    elif _CHOSEN_DB_TYPE == 'PostgreSQL':
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                full_name VARCHAR(255),
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                email VARCHAR(255) UNIQUE,
                phone VARCHAR(50),
                status VARCHAR(50) DEFAULT 'active',
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_role CHECK (role IN ('Admin', 'Employee', 'Cashier')),
                CONSTRAINT chk_user_status CHECK (status IN ('active', 'inactive'))
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS login_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(255),
                status VARCHAR(50)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                "key" VARCHAR(255) PRIMARY KEY,
                "value" TEXT NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255),
                address TEXT,
                reward_points INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                gst_number VARCHAR(255),
                balance DOUBLE PRECISION DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                product_id VARCHAR(255) UNIQUE NOT NULL,
                barcode VARCHAR(255) UNIQUE,
                qrcode VARCHAR(255) UNIQUE,
                category VARCHAR(255),
                brand VARCHAR(255),
                supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
                purchase_price DOUBLE PRECISION NOT NULL,
                mrp DOUBLE PRECISION NOT NULL,
                selling_price DOUBLE PRECISION NOT NULL,
                gst DOUBLE PRECISION DEFAULT 0.0,
                discount DOUBLE PRECISION DEFAULT 0.0,
                quantity DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                unit VARCHAR(50) DEFAULT 'pcs',
                weight DOUBLE PRECISION,
                expiry_date VARCHAR(50),
                mfg_date VARCHAR(50),
                description TEXT,
                image_path VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stock_status VARCHAR(50)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS offers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(50) CHECK(type IN ('Percentage', 'Flat', 'BOGO', 'Combo', 'Membership', 'Student', 'Senior Citizen')) NOT NULL,
                value DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                min_purchase DOUBLE PRECISION DEFAULT 0.0,
                code VARCHAR(255) UNIQUE,
                start_date VARCHAR(50),
                end_date VARCHAR(50),
                active INTEGER DEFAULT 1 CHECK(active IN (0, 1))
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS sales (
                id SERIAL PRIMARY KEY,
                invoice_number VARCHAR(255) UNIQUE NOT NULL,
                customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
                cashier_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subtotal DOUBLE PRECISION NOT NULL,
                discount DOUBLE PRECISION DEFAULT 0.0,
                gst DOUBLE PRECISION DEFAULT 0.0,
                grand_total DOUBLE PRECISION NOT NULL,
                payment_mode VARCHAR(50) NOT NULL,
                cash_received DOUBLE PRECISION DEFAULT 0.0,
                balance DOUBLE PRECISION DEFAULT 0.0,
                status VARCHAR(50) DEFAULT 'Active',
                CONSTRAINT chk_payment_mode CHECK (payment_mode IN ('Cash', 'UPI', 'Credit Card', 'Debit Card', 'Wallet'))
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS sales_items (
                id SERIAL PRIMARY KEY,
                sale_id INTEGER REFERENCES sales(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
                quantity DOUBLE PRECISION NOT NULL,
                mrp DOUBLE PRECISION NOT NULL,
                selling_price DOUBLE PRECISION NOT NULL,
                discount DOUBLE PRECISION DEFAULT 0.0,
                gst DOUBLE PRECISION DEFAULT 0.0,
                subtotal DOUBLE PRECISION NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS inventory_history (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                action VARCHAR(50) NOT NULL,
                quantity DOUBLE PRECISION NOT NULL,
                source_dest VARCHAR(255),
                notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_inv_action CHECK (action IN ('Stock In', 'Sale', 'Damaged', 'Returned', 'Adjustment'))
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS backups (
                id SERIAL PRIMARY KEY,
                filepath VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS deletion_logs (
                id SERIAL PRIMARY KEY,
                table_name VARCHAR(255) NOT NULL,
                record_id VARCHAR(255) NOT NULL,
                deleted_by VARCHAR(255) NOT NULL,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                record_details TEXT
            );
            """
        ]
    else:
        # MySQL schema queries
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(255),
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                email VARCHAR(255) UNIQUE,
                phone VARCHAR(50),
                status VARCHAR(50) DEFAULT 'active',
                last_login DATETIME,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_role CHECK (role IN ('Admin', 'Employee', 'Cashier')),
                CONSTRAINT chk_user_status CHECK (status IN ('active', 'inactive'))
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS login_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(255),
                status VARCHAR(50),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                `key` VARCHAR(255) PRIMARY KEY,
                `value` TEXT NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255),
                address TEXT,
                reward_points INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                gst_number VARCHAR(255),
                balance DOUBLE DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                product_id VARCHAR(255) UNIQUE NOT NULL,
                barcode VARCHAR(255) UNIQUE,
                qrcode VARCHAR(255) UNIQUE,
                category VARCHAR(255),
                brand VARCHAR(255),
                supplier_id INT,
                purchase_price DOUBLE NOT NULL,
                mrp DOUBLE NOT NULL,
                selling_price DOUBLE NOT NULL,
                gst DOUBLE DEFAULT 0.0,
                discount DOUBLE DEFAULT 0.0,
                quantity DOUBLE NOT NULL DEFAULT 0.0,
                unit VARCHAR(50) DEFAULT 'pcs',
                weight DOUBLE,
                expiry_date VARCHAR(50),
                mfg_date VARCHAR(50),
                description TEXT,
                image_path VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                stock_status VARCHAR(50),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS offers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(50) NOT NULL,
                value DOUBLE NOT NULL DEFAULT 0.0,
                min_purchase DOUBLE DEFAULT 0.0,
                code VARCHAR(255) UNIQUE,
                start_date VARCHAR(50),
                end_date VARCHAR(50),
                active INT DEFAULT 1,
                CONSTRAINT chk_offer_type CHECK (type IN ('Percentage', 'Flat', 'BOGO', 'Combo', 'Membership', 'Student', 'Senior Citizen')),
                CONSTRAINT chk_offer_active CHECK (active IN (0, 1))
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_number VARCHAR(255) UNIQUE NOT NULL,
                customer_id INT,
                cashier_id INT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subtotal DOUBLE NOT NULL,
                discount DOUBLE DEFAULT 0.0,
                gst DOUBLE DEFAULT 0.0,
                grand_total DOUBLE NOT NULL,
                payment_mode VARCHAR(50) NOT NULL,
                cash_received DOUBLE DEFAULT 0.0,
                balance DOUBLE DEFAULT 0.0,
                status VARCHAR(50) DEFAULT 'Active',
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
                FOREIGN KEY (cashier_id) REFERENCES users(id) ON DELETE SET NULL,
                CONSTRAINT chk_payment_mode CHECK (payment_mode IN ('Cash', 'UPI', 'Credit Card', 'Debit Card', 'Wallet'))
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS sales_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sale_id INT,
                product_id INT,
                quantity DOUBLE NOT NULL,
                mrp DOUBLE NOT NULL,
                selling_price DOUBLE NOT NULL,
                discount DOUBLE DEFAULT 0.0,
                gst DOUBLE DEFAULT 0.0,
                subtotal DOUBLE NOT NULL,
                FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS inventory_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT,
                action VARCHAR(50) NOT NULL,
                quantity DOUBLE NOT NULL,
                source_dest VARCHAR(255),
                notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                CONSTRAINT chk_inv_action CHECK (action IN ('Stock In', 'Sale', 'Damaged', 'Returned', 'Adjustment'))
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS backups (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filepath VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS deletion_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                table_name VARCHAR(255) NOT NULL,
                record_id VARCHAR(255) NOT NULL,
                deleted_by VARCHAR(255) NOT NULL,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                record_details TEXT
            );
            """
        ]

    try:
        for q in schema_queries:
            cur.execute(q)
        conn.commit()
    except Exception as e:
        print(f"Error creating database schemas: {e}")
        cur.close()
        conn.close()
        return False

    # Seed Default Users
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0] if is_sqlite else cur.fetchone()
    if not is_sqlite and count:
        if isinstance(count, dict):
            count = list(count.values())[0]
        else:
            count = count[0]
    else:
        count = count[0] if isinstance(count, tuple) else count
        
    if count == 0:
        users_to_seed = [
            ('admin', hash_password('admin123'), 'Admin', 'admin@store.com', 'Admin User'),
            ('employee', hash_password('emp123'), 'Employee', 'employee@store.com', 'Store Employee'),
            ('cashier', hash_password('cash123'), 'Cashier', 'cashier@store.com', 'Billing Cashier')
        ]
        insert_query = "INSERT INTO users (username, password_hash, role, email, full_name) VALUES (%s, %s, %s, %s, %s)"
        insert_query = translate_query(insert_query, is_sqlite)
        for u in users_to_seed:
            cur.execute(insert_query, u)
        conn.commit()
        print("Default users seeded.")

    # Seed Default Settings
    cur.execute("SELECT COUNT(*) FROM settings")
    set_count = cur.fetchone()
    if not is_sqlite and set_count:
        if isinstance(set_count, dict):
            set_count = list(set_count.values())[0]
        else:
            set_count = set_count[0]
    else:
        set_count = set_count[0] if isinstance(set_count, tuple) else set_count
        
    if set_count == 0:
        default_settings = [
            ('store_name', 'SKML Mobiles'),
            ('store_logo', ''),
            ('store_gst', '27AAPCS1234F1Z5'),
            ('store_address', '101, Business Hub, Sector 5, Tech City'),
            ('store_phone', '+91 9876543210'),
            ('store_email', 'billing@techmart.com'),
            ('invoice_footer', 'Thank you for shopping with us! Please visit again.'),
            ('currency', 'INR'),
            ('tax_enabled', '1'),
            ('tax_rate_default', '18.0'),
            ('auto_backup_enabled', '1')
        ]
        insert_setting = "INSERT INTO settings (key, value) VALUES (%s, %s)"
        insert_setting = translate_query(insert_setting, is_sqlite)
        for s in default_settings:
            cur.execute(insert_setting, s)
        conn.commit()
        print("Default settings seeded.")

    cur.close()
    conn.close()
    return True

def get_report_data(report_type, start_dt=None, end_dt=None):
    """Compiles list of records for audits report downloads."""
    if report_type == 'sales':
        rows = query_db(
            """SELECT s.invoice_number, s.date, COALESCE(c.name, 'Walk-in') AS customer_name,
                      u.username AS cashier_name, s.subtotal, s.discount, s.gst, s.grand_total,
                      s.payment_mode, s.status
               FROM sales s
               LEFT JOIN customers c ON s.customer_id = c.id
               JOIN users u ON s.cashier_id = u.id
               WHERE s.date >= %s AND s.date <= %s
               ORDER BY s.date DESC""",
            (start_dt, end_dt)
        )
        res = []
        for r in rows:
            res.append({
                'Invoice Number': r['invoice_number'],
                'Date': str(r['date']),
                'Customer': r['customer_name'],
                'Cashier': r['cashier_name'],
                'Subtotal': r['subtotal'],
                'Discount': r['discount'],
                'GST': r['gst'],
                'Grand Total': r['grand_total'],
                'Payment Mode': r['payment_mode'],
                'Status': r['status']
            })
        return res

    elif report_type == 'gst':
        rows = query_db(
            """SELECT s.invoice_number, s.date, p.name AS product_name, p.category,
                      p.gst AS gst_rate, si.quantity, si.gst AS tax_amount, si.subtotal AS taxable_value
               FROM sales_items si
               JOIN sales s ON si.sale_id = s.id
               JOIN products p ON si.product_id = p.id
               WHERE s.date >= %s AND s.date <= %s AND s.status != 'Cancelled'
               ORDER BY s.date DESC""",
            (start_dt, end_dt)
        )
        res = []
        for r in rows:
            res.append({
                'Invoice Number': r['invoice_number'],
                'Date': str(r['date']),
                'Product Name': r['product_name'],
                'Category': r['category'],
                'GST Rate (%)': r['gst_rate'],
                'Quantity': r['quantity'],
                'Tax Amount': r['tax_amount'],
                'Net Taxable Value': r['taxable_value']
            })
        return res

    elif report_type == 'discounts':
        rows = query_db(
            """SELECT s.invoice_number, s.date, s.subtotal, s.discount, s.grand_total, s.payment_mode
               FROM sales s
               WHERE s.date >= %s AND s.date <= %s AND s.discount > 0 AND s.status != 'Cancelled'
               ORDER BY s.date DESC""",
            (start_dt, end_dt)
        )
        res = []
        for r in rows:
            res.append({
                'Invoice Number': r['invoice_number'],
                'Date': str(r['date']),
                'Subtotal': r['subtotal'],
                'Discount Applied': r['discount'],
                'Final Total': r['grand_total'],
                'Payment Mode': r['payment_mode']
            })
        return res

    elif report_type == 'inventory':
        rows = query_db(
            """SELECT p.product_id, p.name, p.brand, p.category, p.purchase_price, p.selling_price, p.quantity, p.stock_status
               FROM products p
               ORDER BY p.name ASC"""
        )
        res = []
        for r in rows:
            qty = float(r['quantity'] or 0.0)
            cost = float(r['purchase_price'] or 0.0)
            res.append({
                'Product ID': r['product_id'],
                'Name': r['name'],
                'Brand': r['brand'],
                'Category': r['category'],
                'Purchase Price': r['purchase_price'],
                'Selling Price': r['selling_price'],
                'Quantity': qty,
                'Stock Value': qty * cost,
                'Stock Status': r['stock_status']
            })
        return res

    return []

def get_inventory_history_logs(limit=100):
    """Retrieves list of recent inventory adjustments."""
    return query_db(
        """SELECT ih.*, p.name AS product_name, p.product_id AS custom_product_id
           FROM inventory_history ih
           JOIN products p ON ih.product_id = p.id
           ORDER BY ih.timestamp DESC
           LIMIT %s""",
        (limit,)
    )
