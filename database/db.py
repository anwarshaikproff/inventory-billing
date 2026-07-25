import os
import json
import sqlite3
import pymysql
import pymysql.cursors
from datetime import datetime
from flask import g

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
    """Registers standard SQL table structures and drops obsolete tables as instructed."""
    conn = get_connection()
    is_sqlite = (_CHOSEN_DB_TYPE == 'SQLite')
    cur = conn.cursor()

    # Drop all remaining old tables from previous multi-table relational ERP design
    legacy_tables = [
        'sales_items', 'sales', 'offers', 'inventory_history', 'backups',
        'deletion_logs', 'customers', 'suppliers', 'products', 'settings',
        'login_history', 'users'
    ]
    for tbl in legacy_tables:
        try:
            if _CHOSEN_DB_TYPE == 'PostgreSQL':
                cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE;")
            else:
                cur.execute(f"DROP TABLE IF EXISTS {tbl};")
        except Exception as e:
            print(f"Notice during legacy table drop ({tbl}): {e}")

    try:
        conn.commit()
    except Exception:
        pass

    # Create the unified billing record table
    if _CHOSEN_DB_TYPE == 'PostgreSQL':
        billing_schema = """
        CREATE TABLE IF NOT EXISTS billing (
            id SERIAL PRIMARY KEY,
            customer_name VARCHAR(255) NOT NULL,
            phone_no VARCHAR(50) NOT NULL,
            item_name VARCHAR(255) NOT NULL,
            cost_of_the_item DOUBLE PRECISION NOT NULL,
            item_qty DOUBLE PRECISION NOT NULL,
            item_price DOUBLE PRECISION NOT NULL,
            payment_type VARCHAR(50) NOT NULL,
            bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT chk_payment_type CHECK (LOWER(payment_type) IN ('cash', 'online', 'upi', 'card', 'debit card', 'credit card'))
        );
        """
    elif is_sqlite:
        billing_schema = """
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone_no TEXT NOT NULL,
            item_name TEXT NOT NULL,
            cost_of_the_item REAL NOT NULL,
            item_qty REAL NOT NULL,
            item_price REAL NOT NULL,
            payment_type TEXT NOT NULL,
            bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    else:
        # MySQL schema
        billing_schema = """
        CREATE TABLE IF NOT EXISTS billing (
            id INT AUTO_INCREMENT PRIMARY KEY,
            customer_name VARCHAR(255) NOT NULL,
            phone_no VARCHAR(50) NOT NULL,
            item_name VARCHAR(255) NOT NULL,
            cost_of_the_item DOUBLE NOT NULL,
            item_qty DOUBLE NOT NULL,
            item_price DOUBLE NOT NULL,
            payment_type VARCHAR(50) NOT NULL,
            bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

    try:
        cur.execute(billing_schema)
        conn.commit()
        print("Unified 'billing' table created successfully and legacy tables removed.")
    except Exception as e:
        print(f"Error creating billing schema: {e}")
        cur.close()
        conn.close()
        return False

    cur.close()
    conn.close()
    return True

def get_report_data(report_type, start_dt=None, end_dt=None):
    """Compiles list of records from the unified billing table for report downloads."""
    if start_dt and end_dt:
        rows = query_db(
            "SELECT * FROM billing WHERE bill_date >= %s AND bill_date <= %s ORDER BY bill_date DESC",
            (start_dt, end_dt)
        )
    else:
        rows = query_db("SELECT * FROM billing ORDER BY bill_date DESC")
        
    res = []
    for r in rows:
        res.append({
            'Bill ID': r['id'],
            'Customer Name': r['customer_name'],
            'Phone No': r['phone_no'],
            'Item Name': r['item_name'],
            'Item Cost': r['cost_of_the_item'],
            'Quantity': r['item_qty'],
            'Total Price': r['item_price'],
            'Payment Type': r['payment_type'],
            'Date': str(r['bill_date'])
        })
    return res

def get_inventory_history_logs(limit=100):
    """Retrieves list of recent billing activity logs."""
    return query_db("SELECT * FROM billing ORDER BY bill_date DESC LIMIT %s", (limit,))
