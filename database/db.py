import os
import sqlite3
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
    """Translates SQL parameter placeholders between SQLite (?) and PostgreSQL/MySQL (%s)."""
    if is_sqlite:
        return query.replace('%s', '?')
    return query

_CHOSEN_DB_TYPE = None

def get_connection():
    """Creates a connection to PostgreSQL (primary) or falls back to SQLite."""
    global DB_STATUS, _CHOSEN_DB_TYPE

    database_url = os.environ.get('DATABASE_URL')

    # 1. Try PostgreSQL connection (Neon / Supabase / Render)
    if database_url and (database_url.startswith("postgresql://") or database_url.startswith("postgres://")):
        try:
            import psycopg2
            conn = psycopg2.connect(database_url, connect_timeout=15)
            _CHOSEN_DB_TYPE = 'PostgreSQL'
            DB_STATUS['status'] = 'Connected'
            DB_STATUS['db_type'] = 'PostgreSQL (Neon Cloud)'
            DB_STATUS['last_sync_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return conn
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}. Falling back to SQLite.")

    # 2. Fall back to local SQLite for offline/dev usage
    try:
        _CHOSEN_DB_TYPE = 'SQLite'
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        DB_STATUS['status'] = 'Connected'
        DB_STATUS['db_type'] = 'SQLite (Local Fallback)'
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
        cur = conn.cursor()

    try:
        cur.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        conn.close()
        res = [dict(row) for row in rv]
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
        if _CHOSEN_DB_TYPE == 'PostgreSQL' and query.strip().upper().startswith('INSERT INTO') and 'RETURNING' not in query.strip().upper():
            query = query.rstrip(';') + ' RETURNING id'
            cur.execute(query, args)
            try:
                last_id = cur.fetchone()[0]
            except Exception:
                pass
        else:
            cur.execute(query, args)
            if is_sqlite:
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
    """Drops obsolete legacy tables and initializes the unified billing table."""
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
    else:
        # SQLite schema (local fallback)
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

    try:
        cur.execute(billing_schema)
        conn.commit()
        print(f"Unified 'billing' table ready on {_CHOSEN_DB_TYPE}.")
    except Exception as e:
        print(f"Error creating billing schema: {e}")
        cur.close()
        conn.close()
        return False

    cur.close()
    conn.close()
    return True

def get_report_data(start_dt=None, end_dt=None):
    """Compiles list of billing records for report downloads."""
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
