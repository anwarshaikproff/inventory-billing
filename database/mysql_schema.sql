-- MySQL Database Schema for POS & Inventory System

-- 1. Users Table
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Login History Table
CREATE TABLE IF NOT EXISTS login_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(255),
    status VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Store Config Settings Table
CREATE TABLE IF NOT EXISTS settings (
    `key` VARCHAR(255) PRIMARY KEY,
    `value` TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    address TEXT,
    reward_points INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Suppliers Table
CREATE TABLE IF NOT EXISTS suppliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    gst_number VARCHAR(255),
    balance DOUBLE DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Products Table
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Offers Table
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Sales (Invoices) Table
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Sales Items Table
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. Inventory History Table
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. Database Backups Table
CREATE TABLE IF NOT EXISTS backups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filepath VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 12. Deletion Logs Table
CREATE TABLE IF NOT EXISTS deletion_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(255) NOT NULL,
    record_id VARCHAR(255) NOT NULL,
    deleted_by VARCHAR(255) NOT NULL,
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_details TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
