import os
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect
from database.db import query_db, execute_db, get_report_data
from models.user import User
from models.product import Product
from models.customer import Customer
from models.sale import Sale
from models.offer import Offer
from models.supplier import Supplier

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.before_request
def enforce_https():
    """Enforces HTTPS for all API requests outside of local development environments."""
    if not request.is_secure and 'localhost' not in request.host and '127.0.0.1' not in request.host:
        secure_url = request.url.replace('http://', 'https://', 1)
        return redirect(secure_url, code=301)

def api_login_required(f):
    """API-friendly decorator to restrict access to authenticated sessions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Unauthorized. Please log in."}), 401
        user = User.get_by_id(session['user_id'])
        if not user:
            session.clear()
            return jsonify({"success": False, "message": "Session expired or invalid user."}), 401
        return f(*args, **kwargs)
    return decorated_function

def api_role_required(role_name):
    """API-friendly decorator to enforce role permissions hierarchy."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({"success": False, "message": "Unauthorized. Please log in."}), 401
            user = User.get_by_id(session['user_id'])
            if not user:
                session.clear()
                return jsonify({"success": False, "message": "Session expired."}), 401
            if not user.has_permission(role_name):
                return jsonify({"success": False, "message": "Access Denied: Insufficient privileges."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ----------------- ADMIN LOGIN & AUTH -----------------

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Authenticates admin/staff session via JSON POST request."""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required."}), 400

    user = User.authenticate(username, password)
    if user:
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        return jsonify({
            "success": True,
            "message": "Login successful.",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "email": user.email,
                "full_name": user.full_name
            }
        })
    return jsonify({"success": False, "message": "Invalid username, password, or inactive account."}), 401

@api_bp.route('/auth/logout', methods=['POST'])
def logout():
    """Logs out current user and clears session state."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})

@api_bp.route('/auth/me', methods=['GET'])
@api_login_required
def get_current_user():
    """Returns details of currently authenticated user session."""
    user = User.get_by_id(session['user_id'])
    if user:
        return jsonify({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "email": user.email,
                "full_name": user.full_name
            }
        })
    return jsonify({"success": False, "message": "User not found."}), 404

# ----------------- PRODUCT MANAGEMENT -----------------

@api_bp.route('/products', methods=['GET'])
@api_login_required
def get_products():
    """Fetches list of all product listings in database."""
    products = Product.get_all()
    products_list = []
    for p in products:
        products_list.append({
            "id": p.id,
            "name": p.name,
            "product_id": p.product_id,
            "barcode": p.barcode,
            "qrcode": p.qrcode,
            "category": p.category,
            "brand": p.brand,
            "supplier_id": p.supplier_id,
            "purchase_price": p.purchase_price,
            "mrp": p.mrp,
            "selling_price": p.selling_price,
            "gst": p.gst,
            "discount": p.discount,
            "quantity": p.quantity,
            "unit": p.unit,
            "weight": p.weight,
            "expiry_date": p.expiry_date,
            "mfg_date": p.mfg_date,
            "description": p.description,
            "image_path": p.image_path,
            "stock_status": p.stock_status
        })
    return jsonify({"success": True, "products": products_list})

@api_bp.route('/products/<int:prod_id>', methods=['GET'])
@api_login_required
def get_product(prod_id):
    """Fetches details of a single product SKU by ID."""
    p = Product.get_by_id(prod_id)
    if not p:
        return jsonify({"success": False, "message": "Product not found."}), 404
    return jsonify({
        "success": True,
        "product": {
            "id": p.id,
            "name": p.name,
            "product_id": p.product_id,
            "barcode": p.barcode,
            "qrcode": p.qrcode,
            "category": p.category,
            "brand": p.brand,
            "supplier_id": p.supplier_id,
            "purchase_price": p.purchase_price,
            "mrp": p.mrp,
            "selling_price": p.selling_price,
            "gst": p.gst,
            "discount": p.discount,
            "quantity": p.quantity,
            "unit": p.unit,
            "weight": p.weight,
            "expiry_date": p.expiry_date,
            "mfg_date": p.mfg_date,
            "description": p.description,
            "image_path": p.image_path,
            "stock_status": p.stock_status
        }
    })

@api_bp.route('/products', methods=['POST'])
@api_login_required
@api_role_required('Employee')
def add_product():
    """Adds a new product to the warehouse database catalog."""
    data = request.get_json() or {}
    try:
        p = Product.create(
            name=data.get('name', '').strip(),
            product_id=data.get('product_id', '').strip(),
            barcode=data.get('barcode', '').strip() or None,
            qrcode=data.get('qrcode', '').strip() or None,
            category=data.get('category', '').strip() or 'General',
            brand=data.get('brand', '').strip() or 'Generic',
            supplier_id=data.get('supplier_id') or None,
            purchase_price=float(data.get('purchase_price') or 0.0),
            mrp=float(data.get('mrp') or 0.0),
            selling_price=float(data.get('selling_price') or 0.0),
            gst=float(data.get('gst') or 0.0),
            discount=float(data.get('discount') or 0.0),
            quantity=float(data.get('quantity') or 0.0),
            unit=data.get('unit', 'pcs'),
            weight=float(data.get('weight')) if data.get('weight') else None,
            expiry_date=data.get('expiry_date') or None,
            mfg_date=data.get('mfg_date') or None,
            description=data.get('description', '').strip()
        )
        return jsonify({"success": True, "message": "Product added successfully.", "product_id": p.id}), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@api_bp.route('/products/<int:prod_id>', methods=['PUT', 'POST'])
@api_login_required
@api_role_required('Employee')
def edit_product(prod_id):
    """Updates product properties."""
    product = Product.get_by_id(prod_id)
    if not product:
        return jsonify({"success": False, "message": "Product not found."}), 404

    data = request.get_json() or {}
    try:
        product.update(
            name=data.get('name', product.name).strip(),
            category=data.get('category', product.category).strip(),
            brand=data.get('brand', product.brand).strip(),
            purchase_price=float(data.get('purchase_price') if 'purchase_price' in data else product.purchase_price),
            selling_price=float(data.get('selling_price') if 'selling_price' in data else product.selling_price),
            mrp=float(data.get('mrp') if 'mrp' in data else product.mrp),
            quantity=float(data.get('quantity') if 'quantity' in data else product.quantity),
            gst=float(data.get('gst') if 'gst' in data else product.gst),
            discount=float(data.get('discount') if 'discount' in data else product.discount),
            unit=data.get('unit', product.unit),
            weight=float(data.get('weight')) if data.get('weight') else product.weight,
            expiry_date=data.get('expiry_date') or product.expiry_date,
            mfg_date=data.get('mfg_date') or product.mfg_date,
            description=data.get('description', product.description).strip()
        )
        return jsonify({"success": True, "message": "Product updated successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@api_bp.route('/products/<int:prod_id>/delete', methods=['POST', 'DELETE'])
@api_login_required
@api_role_required('Admin')
def delete_product(prod_id):
    """Deletes product permanently."""
    product = Product.get_by_id(prod_id)
    if not product:
        return jsonify({"success": False, "message": "Product not found."}), 404

    try:
        p_name = product.name
        product.delete()
        return jsonify({"success": True, "message": f"Product '{p_name}' deleted successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Deletion failed: {str(e)}"}), 500

# ----------------- INVENTORY MANAGEMENT -----------------

@api_bp.route('/inventory', methods=['GET'])
@api_login_required
def get_inventory_stats():
    """Compiles detailed inventory statistics (valuations, low-stock metrics)."""
    products = Product.get_all()
    total_cost_val = sum(p.purchase_price * p.quantity for p in products)
    total_retail_val = sum(p.selling_price * p.quantity for p in products)
    
    # Filter low stock
    low_stock = []
    out_of_stock = []
    for p in products:
        if p.quantity <= 0:
            out_of_stock.append({"id": p.id, "name": p.name, "quantity": p.quantity, "sku": p.product_id})
        elif p.quantity <= 10.0:
            low_stock.append({"id": p.id, "name": p.name, "quantity": p.quantity, "sku": p.product_id})
            
    return jsonify({
        "success": True,
        "total_cost_value": total_cost_val,
        "total_retail_value": total_retail_val,
        "low_stock_items": low_stock,
        "out_of_stock_items": out_of_stock
    })

@api_bp.route('/inventory/adjust', methods=['POST'])
@api_login_required
@api_role_required('Employee')
def adjust_inventory():
    """Logs stock adjustment and updates catalog quantity levels."""
    data = request.get_json() or {}
    product_id = data.get('product_id')
    action = data.get('action') # 'Damaged', 'Returned', 'Adjustment'
    quantity = float(data.get('quantity', 0.0))
    notes = data.get('notes', '').strip()
    source_dest = data.get('source_dest', 'Store').strip()

    if not product_id or not action or quantity <= 0:
        return jsonify({"success": False, "message": "Invalid adjustment parameters."}), 400

    product = Product.get_by_id(product_id)
    if not product:
        return jsonify({"success": False, "message": "Product not found."}), 404

    try:
        # Calculate new quantity based on log type
        if action == 'Damaged':
            product.update(quantity=product.quantity - quantity)
        elif action in ('Returned', 'Adjustment'):
            product.update(quantity=product.quantity + quantity)
        else:
            return jsonify({"success": False, "message": "Invalid action value."}), 400

        # Log history
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execute_db(
            "INSERT INTO inventory_history (product_id, action, quantity, source_dest, notes, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
            (product_id, action, quantity, source_dest, notes, now_str)
        )
        return jsonify({"success": True, "message": "Stock adjustment recorded successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ----------------- BILLING & TRANSACTIONAL PROCESSING -----------------

@api_bp.route('/billing', methods=['GET'])
@api_login_required
def get_billing_invoices():
    """Lists recent billing invoices."""
    sales = Sale.get_all()
    invoices = []
    for s in sales:
        invoices.append({
            "id": s.get('id'),
            "invoice_number": s.get('invoice_number'),
            "customer_id": s.get('customer_id'),
            "customer_name": s.get('customer_name'),
            "date": str(s.get('date')),
            "subtotal": s.get('subtotal'),
            "discount": s.get('discount'),
            "gst": s.get('gst'),
            "grand_total": s.get('grand_total'),
            "payment_mode": s.get('payment_mode'),
            "status": s.get('status')
        })
    return jsonify({"success": True, "invoices": invoices})

@api_bp.route('/pos/checkout', methods=['POST'])
@api_login_required
def api_checkout():
    """Handles cart checkout transaction, computes totals, updates rewards and stock levels."""
    data = request.get_json() or {}
    customer_id = data.get('customer_id')
    cart_items = data.get('cart_items', [])
    payment_mode = data.get('payment_mode', 'Cash')
    cash_received = float(data.get('cash_received', 0.0))
    coupon_code = data.get('coupon_code')

    if not cart_items:
        return jsonify({"success": False, "message": "Cart is empty."}), 400

    try:
        invoice_number = Sale.create_transaction(
            customer_id=customer_id,
            cashier_id=session['user_id'],
            cart_items=cart_items,
            payment_mode=payment_mode,
            cash_received=cash_received,
            coupon_code=coupon_code
        )
        return jsonify({
            "success": True, 
            "message": "Checkout complete.", 
            "invoice_number": invoice_number
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@api_bp.route('/billing/cancel/<int:sale_id>', methods=['POST'])
@api_login_required
@api_role_required('Admin')
def cancel_invoice(sale_id):
    """Cancels a completed invoice and restores stock levels."""
    sale_data = query_db("SELECT * FROM sales WHERE id = %s", (sale_id,), one=True)
    if not sale_data:
        return jsonify({"success": False, "message": "Invoice record not found."}), 404

    try:
        Sale.cancel_transaction(sale_data['invoice_number'])
        return jsonify({"success": True, "message": "Invoice cancelled and inventory stock restored."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ----------------- CUSTOMER REGISTRY -----------------

@api_bp.route('/customers', methods=['GET'])
@api_login_required
def get_customers():
    """Lists registered customer accounts."""
    customers = Customer.get_all()
    cust_list = []
    for c in customers:
        cust_list.append({
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "email": c.email,
            "address": c.address,
            "reward_points": c.reward_points
        })
    return jsonify({"success": True, "customers": cust_list})

@api_bp.route('/customers', methods=['POST'])
@api_login_required
def add_customer():
    """Registers a new customer profile."""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip() or None
    address = data.get('address', '').strip() or None

    if not name or not phone:
        return jsonify({"success": False, "message": "Name and phone are required."}), 400

    try:
        cust = Customer.create(name=name, phone=phone, email=email, address=address)
        return jsonify({"success": True, "message": "Customer registered successfully.", "customer_id": cust.id}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@api_bp.route('/customers/<int:cust_id>', methods=['PUT', 'POST'])
@api_login_required
def edit_customer(cust_id):
    """Updates customer properties."""
    customer = Customer.get_by_id(cust_id)
    if not customer:
        return jsonify({"success": False, "message": "Customer not found."}), 404

    data = request.get_json() or {}
    name = data.get('name', customer.name).strip()
    phone = data.get('phone', customer.phone).strip()
    email = data.get('email', customer.email)
    address = data.get('address', customer.address)
    reward_points = data.get('reward_points', customer.reward_points)

    try:
        customer.update(name=name, phone=phone, email=email, address=address, reward_points=reward_points)
        return jsonify({"success": True, "message": "Customer profile updated successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@api_bp.route('/customers/<int:cust_id>/delete', methods=['POST', 'DELETE'])
@api_login_required
@api_role_required('Admin')
def delete_customer(cust_id):
    """Removes a customer profile completely."""
    customer = Customer.get_by_id(cust_id)
    if not customer:
        return jsonify({"success": False, "message": "Customer not found."}), 404

    try:
        customer.delete()
        return jsonify({"success": True, "message": "Customer profile deleted successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ----------------- ANALYTICS & REPORTS -----------------

@api_bp.route('/reports', methods=['GET'])
@api_login_required
@api_role_required('Employee')
def fetch_reports():
    """Generates detailed reports for sales, tax/gst, and discount distributions."""
    report_type = request.args.get('type', 'sales') # sales, gst, discounts, inventory
    start_date = request.args.get('start_date', datetime.now().strftime('%Y-%m-01') + " 00:00:00")
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d') + " 23:59:59")

    try:
        data = get_report_data(report_type, start_date, end_date)
        return jsonify({
            "success": True,
            "report_type": report_type,
            "start_date": start_date,
            "end_date": end_date,
            "data": data
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
