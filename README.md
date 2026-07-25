# TechMart POS & Inventory System

TechMart is a professional, modular, and responsive **Inventory Management and POS Billing System** built in Python using Flask and SQLite, styled with a glassmorphic dashboard layout.

---

## Technical Stack

*   **Backend**: Flask (Python OOP models)
*   **Database**: SQLite (Normalized DB schemas, foreign keys)
*   **Frontend**: HTML5, Vanilla CSS (dynamic dark/light themes), JavaScript (AJAX autocompletes, video frames scanner)
*   **UI Components**: Bootstrap 5, FontAwesome 6 icons, Google Fonts (Outfit)
*   **Barcode Decoders**: OpenCV, Pyzbar (gracefully isolated fallbacks)
*   **Invoicing & Label Printers**: ReportLab (thermal slip PDFs & A4 barcode grids)
*   **Data Imports**: Pandas, Openpyxl (Excel templates)

---

## Directory Structure

```text
inventory_system/
│
├── app.py                   # Main Flask factory and app runner
├── requirements.txt         # Project dependencies
├── README.md                # System documentation
├── verify_system.py         # Automated components verification script
│
├── database/
│   ├── db.py                # Database connection context manager & seeding
│   └── schema.sql           # Database table structures
│
├── models/
│   ├── user.py              # Auth & RBAC logic
│   ├── product.py           # Product CRUD & spreadsheet imports
│   ├── customer.py          # Customer registry & reward ledger
│   ├── supplier.py          # Supplier logs & outstanding statements
│   ├── offer.py             # Promotion coupons & discount calculations
│   ├── sale.py              # POS transactions & metrics aggregator
│   └── settings.py          # Config registry & database backup/restore
│
├── routes/
│   ├── auth.py              # Login and session validation blueprints
│   ├── dashboard.py         # Visual KPI trackers & Chart.js data endpoints
│   ├── products.py          # Product inventory views & bulk operations
│   ├── pos.py               # Billing interface & invoice templates
│   ├── scanner.py           # Webcam processing endpoints
│   ├── offers.py            # Coupon setups CRUD
│   ├── reports.py           # PDF/Excel/CSV exports blueprints
│   ├── settings.py          # Configuration forms & backup managers
│   ├── customers.py         # Customer lists blueprints
│   └── suppliers.py         # Supplier list blueprints
│
├── utils/
│   ├── barcode_gen.py       # Code128, EAN13, and QR Code sticker builders
│   └── pdf_generator.py     # Retail sales thermal invoices generator
│
└── static/
    ├── css/
    │   └── styles.css       # Custom glassmorphic stylesheet variables
    ├── js/
    │   └── main.js          # Cart managers, webcam frames capture, voice recognitions
    └── uploads/             # Product pictures and exports directory
```

---

## Standard Installation & Setup

### 1. Requirements Installation
Ensure Python 3.10+ is installed. Execute pip installation:
```bash
python -m pip install -r requirements.txt
```

### 2. Launch the Application
Run the Flask server:
```bash
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) on your web browser.

### 3. Run Automated Validation Suite
Execute the testing scripts:
```bash
python verify_system.py
```

---

## Role-Based Access Control & Default Credentials

| Username | Password | Role | Permissions |
| :--- | :--- | :--- | :--- |
| `admin` | `admin123` | **Admin** | Full system rights, restore operations, delete operations, store configurations |
| `employee` | `emp123` | **Employee** | Product listings, reports exports, discount structures setups, supplier registries |
| `cashier` | `cash123` | **Cashier** | Billing terminal POS checkouts, customer loyalty registrations, invoice logs |

---

## POS Billing Keyboard Hotkeys Cheat Sheet

Cashiers can speed up transactions on the POS counter utilizing browser hotkeys:

*   **F2**: Focus input cursor on the **Product Search** bar.
*   **F4**: Focus input cursor on the **Cash Received** input field.
*   **F7**: Toggle **Webcam Barcode Scanner** overlay on/off.
*   **F8**: Change Payment mode select to **Cash**.
*   **F9**: Change Payment mode select to **UPI**.
*   **F10**: Submit billing cart and perform transaction **Checkout & Print**.

---

## Voice Recognition Search Commands

If Speech Recognition is active on your browser (e.g. Chrome/Edge), clicking the **Microphone** button allows the cashier to speak the name of a product (e.g., *"Wireless Mouse"* or *"Keyboard"*). The autocomplete search is triggered automatically matching vocal inputs.
