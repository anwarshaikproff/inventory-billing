# TechMart POS & Inventory System

This document provides a comprehensive overview of the TechMart Point of Sale (POS) & Inventory System project, including its application architecture, component breakdowns, file structure, and database configuration.

---

## 1. Connected Database Configuration

The application is connected to a primary PostgreSQL database hosted on **Supabase** with a local SQLite database acting as a high-availability fallback.

### Database Credentials
* **Database Engine**: PostgreSQL (Supabase)
* **Host**: `db.qujdweimasrbjwzejgaz.supabase.co`
* **Port**: `6543` (Connection Pooler / IPv4 Gateway)
* **Direct Port**: `5432` (Direct IPv6 Connection)
* **Database Name**: `postgres`
* **Username**: `postgres`
* **Connection String**: `postgresql://postgres:***@db.qujdweimasrbjwzejgaz.supabase.co:6543/postgres`

### SQLite Fallback Database
* **Fallback Type**: SQLite 3
* **Database Path**: `database/database.db`
* **Purpose**: If connection to the remote Supabase database times out or is offline, the system automatically falls back to the local SQLite database to prevent any service interruptions at the billing counter.

---

## 2. Technical Stack

* **Backend**: Python, Flask (with session and context management)
* **Database Client**: `psycopg2` (for PostgreSQL), `sqlite3` (for SQLite)
* **Frontend**: HTML5 (Semantic Structure), Bootstrap 5 (Responsive Layouts & Components), Vanilla CSS (Custom Styling)
* **Icons & Fonts**: FontAwesome 6, Google Fonts (Inter, Outfit)
* **Libraries**: `werkzeug` (for secure password hashing and verification)

---

## 3. Project Directory Structure

```text
inventory_system/
│
├── app.py                   # Main application factory, configures Flask, registers blueprint routes
├── requirements.txt         # Project dependencies (Flask, psycopg2, werkzeug, etc.)
├── verify_system.py         # Automated verification tests for authentication, checkout, discounts, etc.
│
├── database/                # Database management layer
│   ├── db.py                # Connection manager, query executor, schema builder, migration agent
│   ├── schema.sql           # Raw SQL script for SQLite table schemas
│   └── database.db          # SQLite fallback database file
│
├── models/                  # Domain business logic models
│   ├── user.py              # User authentication, profiles, role check (Admin, Employee, Cashier)
│   ├── product.py           # Product catalog, stock tracking, SKU barcode indexing
│   ├── customer.py          # Customer directory, contact tracking, reward points ledger
│   ├── supplier.py          # Suppliers details, contact tracking, outstanding balance
│   ├── offer.py             # Multi-tier discount calculations (Percentage, Flat, BOGO)
│   └── sale.py              # Transaction checkouts, billing calculation, stock deduction
│
├── routes/                  # Modular request controller blueprints
│   ├── auth.py              # Login sessions, registration, logout, and access decorators
│   ├── dashboard.py         # Home view with analytical charts and live sales summary metrics
│   ├── products.py          # Product catalog administration CRUD endpoints
│   ├── pos.py               # Live POS checkout cart, invoice receipt printing
│   ├── scanner.py           # QR/Barcode scan handler endpoints
│   ├── offers.py            # Offer coupon configurations
│   ├── customers.py         # Customer profile management
│   ├── suppliers.py         # Supplier profile management
│   ├── reports.py           # Sales audit summary compile, PDF receipt generator download
│   ├── settings.py          # Store information updates, database backups and restore triggers
│   └── db_management.py     # System administration panels (Admins/Users, Products, Sales Invoices)
│
├── static/                  # Static assets
│   ├── css/
│   │   └── styles.css       # Premium custom styling variables, fonts, glassmorphism, animations
│   └── uploads/             # User uploaded files (e.g., custom store receipt logos)
│
└── templates/               # Jinja2 HTML layout views
    ├── base.html            # Main template (navigation sidebar, header, flash alerts)
    ├── login.html           # Secure login page view
    ├── register.html        # Admin registration page
    ├── dashboard.html       # Metrics charts dashboard
    ├── pos.html             # Point of Sale interactive checkout board
    ├── invoice_pdf.html     # Raw HTML invoice receipt format
    ├── products.html        # Product inventory view
    ├── customers.html       # Customer list board
    ├── suppliers.html       # Supplier listings
    ├── offers.html          # Offer coupon view
    ├── reports.html         # Custom reporting panels
    ├── settings.html        # Store information settings page
    └── db_management.html   # User and catalog master database controls
```

---

## 4. Key Functional Features

1. **Role-Based Access Control (RBAC)**:
   * **Admin**: Access to all features, settings, databases, backups, and user management.
   * **Employee**: Access to product catalogs, customer files, reports, and inventory ledgers.
   * **Cashier**: Restrained to the Point of Sale interactive billing counter.

2. **Interactive Billing Interface (POS)**:
   * Real-time cart calculations including automatic tax calculations, discount computations, and customer loyalty rewards accumulation.
   * Invoice generator with printer-ready receipt download views.

3. **Multi-Tier Discount Engine**:
   * Support for BOGO (Buy One Get One), Flat Amount, and Percentage store-wide discount coupons.

4. **Inventory Management**:
   * Automatic stock deduction upon invoice checkout, adjustment log auditing, low-stock warnings, and barcode/QR scanning integration.

5. **Backup & Restore System**:
   * Supports manual database snapshots and restoring database state from uploaded database backup files (`.db`).
