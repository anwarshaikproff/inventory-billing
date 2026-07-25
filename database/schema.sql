-- SQLite Database Schema for Inventory and Billing System
-- Normalised database structure with appropriate foreign keys

-- 1. Users table (for authentication and role-based access control)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK(role IN ('Admin', 'Employee', 'Cashier')) NOT NULL,
    email TEXT,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Store Settings table (key-value configurations)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 3. Customers table
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    email TEXT,
    address TEXT,
    reward_points INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Suppliers table
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    gst_number TEXT,
    balance REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Products table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    product_id TEXT UNIQUE NOT NULL,
    barcode TEXT UNIQUE,
    qrcode TEXT UNIQUE,
    category TEXT,
    brand TEXT,
    supplier_id INTEGER,
    purchase_price REAL NOT NULL,
    mrp REAL NOT NULL,
    selling_price REAL NOT NULL,
    gst REAL DEFAULT 0.0,            -- in percentage, e.g., 18.0
    discount REAL DEFAULT 0.0,       -- product-specific percentage discount
    quantity REAL NOT NULL DEFAULT 0.0,
    unit TEXT DEFAULT 'pcs',         -- e.g., pcs, kg, ltr, box
    weight REAL,                     -- in grams/kg
    expiry_date TEXT,                -- YYYY-MM-DD
    mfg_date TEXT,                   -- YYYY-MM-DD
    description TEXT,
    image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
);

-- 6. Offers & Discounts Engine Table
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('Percentage', 'Flat', 'BOGO', 'Combo', 'Membership', 'Student', 'Senior Citizen')) NOT NULL,
    value REAL NOT NULL DEFAULT 0.0,            -- discount value (percent or flat amt)
    min_purchase REAL DEFAULT 0.0,
    code TEXT UNIQUE,                           -- coupon code if applicable
    start_date TEXT,                            -- YYYY-MM-DD
    end_date TEXT,                              -- YYYY-MM-DD
    active INTEGER DEFAULT 1 CHECK(active IN (0, 1))
);

-- 7. Sales (Invoices) Table
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    customer_id INTEGER,
    cashier_id INTEGER NOT NULL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    subtotal REAL NOT NULL,
    discount REAL DEFAULT 0.0,
    gst REAL DEFAULT 0.0,
    grand_total REAL NOT NULL,
    payment_mode TEXT CHECK(payment_mode IN ('Cash', 'UPI', 'Credit Card', 'Debit Card', 'Wallet')) NOT NULL,
    cash_received REAL DEFAULT 0.0,
    balance REAL DEFAULT 0.0,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (cashier_id) REFERENCES users(id)
);

-- 8. Sales Items Table (Detailing items in each invoice)
CREATE TABLE IF NOT EXISTS sales_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    mrp REAL NOT NULL,
    selling_price REAL NOT NULL,
    discount REAL DEFAULT 0.0,       -- final discount applied (absolute amount)
    gst REAL DEFAULT 0.0,            -- GST applied (absolute amount)
    subtotal REAL NOT NULL,          -- quantity * selling_price - discount
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 9. Inventory History Table (For auditing stock movement)
CREATE TABLE IF NOT EXISTS inventory_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    action TEXT CHECK(action IN ('Stock In', 'Sale', 'Damaged', 'Returned', 'Adjustment')) NOT NULL,
    quantity REAL NOT NULL,
    source_dest TEXT,                 -- e.g. Warehouse, Store, Customer Return
    notes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- 10. Database Backups Table
CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
