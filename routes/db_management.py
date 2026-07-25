from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from routes.auth import login_required, role_required
from models.user import User
from models.product import Product
from models.sale import Sale
from models.offer import Offer
from models.customer import Customer
from database.db import query_db, execute_db, get_db_status
from datetime import datetime

db_management_bp = Blueprint('db_management', __name__)

def log_deletion(table_name, record_id, deleted_by, record_details=""):
    """Inserts a deletion audit log record."""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    execute_db(
        "INSERT INTO deletion_logs (table_name, record_id, deleted_by, deleted_at, record_details) VALUES (%s, %s, %s, %s, %s)",
        (table_name, str(record_id), deleted_by, now_str, record_details)
    )

@db_management_bp.route('/admin/db-management')
@login_required
@role_required('Admin')
def index():
    """Renders Admin Database Management Panel."""
    tab = request.args.get('tab', 'admins')
    search_q = request.args.get('q', '').strip()
    
    # 1. ADMINS TAB
    admins = User.get_all()
    if tab == 'admins' and search_q:
        admins = [a for a in admins if (
            search_q.lower() in a.username.lower() or 
            search_q.lower() in (a.full_name or '').lower() or 
            search_q.lower() in (a.email or '').lower() or 
            search_q.lower() in (a.phone or '').lower()
        )]

    # 2. PRODUCTS TAB
    products = Product.get_all()
    category_filter = request.args.get('category', '').strip()
    stock_filter = request.args.get('stock_status', '').strip()
    
    if tab == 'products':
        if search_q:
            products = [p for p in products if (
                search_q.lower() in p.name.lower() or 
                search_q.lower() in p.product_id.lower() or
                (p.barcode and search_q == p.barcode) or 
                (p.qrcode and search_q == p.qrcode)
            )]
        if category_filter:
            products = [p for p in products if p.category == category_filter]
        if stock_filter:
            products = [p for p in products if p.stock_status == stock_filter]

    # Categories list for dropdown
    categories = sorted(list(set(p.category for p in Product.get_all() if p.category)))

    # 3. OFFERS TAB
    offers = Offer.get_all()
    if tab == 'offers' and search_q:
        offers = [o for o in offers if (
            search_q.lower() in o.name.lower() or 
            (o.code and search_q.lower() in o.code.lower()) or 
            search_q.lower() in o.type.lower()
        )]

    # 4. CUSTOMERS TAB
    customers = Customer.get_all()
    if tab == 'customers' and search_q:
        customers = [c for c in customers if (
            search_q.lower() in c.name.lower() or 
            search_q.lower() in c.phone.lower() or 
            (c.email and search_q.lower() in c.email.lower()) or 
            (c.address and search_q.lower() in c.address.lower())
        )]

    # 5. BILLING TAB
    bills = Sale.get_all()
    payment_filter = request.args.get('payment_mode', '').strip()
    date_filter = request.args.get('date', '').strip() # Expect YYYY-MM-DD
    
    if tab == 'billing':
        if search_q:
            bills = [b for b in bills if (
                search_q.lower() in b.get('invoice_number', '').lower() or
                search_q.lower() in b.get('customer_name', '').lower()
            )]
        if payment_filter:
            bills = [b for b in bills if b.get('payment_mode') == payment_filter]
        if date_filter:
            bills = [b for b in bills if str(b.get('date'))[:10] == date_filter]

    # Database Status Details
    db_status = get_db_status()

    # Pagination Helper (Items per page = 10)
    limit = 10
    
    # Page numbers
    admins_page = int(request.args.get('admins_page', 1))
    products_page = int(request.args.get('products_page', 1))
    offers_page = int(request.args.get('offers_page', 1))
    customers_page = int(request.args.get('customers_page', 1))
    billing_page = int(request.args.get('billing_page', 1))
    
    # Slicing helper
    def paginate(items, page):
        offset = (page - 1) * limit
        total_pages = max(1, (len(items) + limit - 1) // limit)
        return items[offset:offset+limit], total_pages

    paginated_admins, admins_total_pages = paginate(admins, admins_page)
    paginated_products, products_total_pages = paginate(products, products_page)
    paginated_offers, offers_total_pages = paginate(offers, offers_page)
    paginated_customers, customers_total_pages = paginate(customers, customers_page)
    paginated_bills, billing_total_pages = paginate(bills, billing_page)

    return render_template(
        'db_management.html',
        tab=tab,
        q=search_q,
        db_status=db_status,
        
        # Admins
        admins=paginated_admins,
        admins_page=admins_page,
        admins_total_pages=admins_total_pages,
        total_admins_count=len(admins),
        
        # Products
        products=paginated_products,
        products_page=products_page,
        products_total_pages=products_total_pages,
        categories=categories,
        category_filter=category_filter,
        stock_filter=stock_filter,
        total_products_count=len(products),
        
        # Offers
        offers=paginated_offers,
        offers_page=offers_page,
        offers_total_pages=offers_total_pages,
        total_offers_count=len(offers),
        
        # Customers
        customers=paginated_customers,
        customers_page=customers_page,
        customers_total_pages=customers_total_pages,
        total_customers_count=len(customers),
        
        # Billing
        bills=paginated_bills,
        billing_page=billing_page,
        billing_total_pages=billing_total_pages,
        payment_filter=payment_filter,
        date_filter=date_filter,
        total_bills_count=len(bills)
    )

# ----------------- ADMIN/USER ACTIONS -----------------

@db_management_bp.route('/admin/db-management/users/add', methods=['POST'])
@login_required
@role_required('Admin')
def add_user():
    """Adds a new user profile via Database Management."""
    full_name = request.form.get('full_name', '').strip()
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    role = request.form.get('role', 'Cashier').strip()
    password = request.form.get('password', '').strip()

    if not username or not password or not role:
        flash("Username, password, and role are required.", "danger")
        return redirect(url_for('db_management.index', tab='admins'))

    try:
        User.create(
            username=username,
            password=password,
            role=role,
            email=email or None,
            full_name=full_name or None,
            phone=phone or None
        )
        flash(f"User '{username}' created successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for('db_management.index', tab='admins'))

@db_management_bp.route('/admin/db-management/users/<int:user_id>/edit', methods=['POST'])
@login_required
@role_required('Admin')
def edit_user(user_id):
    """Updates user information."""
    user = User.get_by_id(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('db_management.index', tab='admins'))

    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    role = request.form.get('role', user.role).strip()
    status = request.form.get('status', 'active').strip()

    # Self role/status block protection
    if user.id == session.get('user_id') and status == 'inactive':
        flash("You cannot deactivate your own logged-in admin account.", "danger")
        return redirect(url_for('db_management.index', tab='admins'))

    try:
        user.update_details(
            role=role,
            email=email or None,
            status=status,
            full_name=full_name or None,
            phone=phone or None
        )
        flash(f"User '{user.username}' details updated.", "success")
    except Exception as e:
        flash(f"Update failed: {str(e)}", "danger")
    return redirect(url_for('db_management.index', tab='admins'))

@db_management_bp.route('/admin/db-management/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@role_required('Admin')
def reset_user_password(user_id):
    """Resets user account password securely."""
    user = User.get_by_id(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('db_management.index', tab='admins'))

    password = request.form.get('password', '').strip()
    if not password:
        flash("Password cannot be empty.", "danger")
        return redirect(url_for('db_management.index', tab='admins'))

    try:
        user.update_password(password)
        flash(f"Password reset for '{user.username}' successfully.", "success")
    except Exception as e:
        flash(f"Password reset failed: {str(e)}", "danger")
    return redirect(url_for('db_management.index', tab='admins'))

@db_management_bp.route('/admin/db-management/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required('Admin')
def toggle_user(user_id):
    """Enables or disables user account."""
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    if user.id == session.get('user_id'):
        return jsonify({"success": False, "message": "You cannot disable your own active admin account."}), 400

    # Last super admin check
    if user.role == 'Admin' and user.status == 'active':
        admins = [u for u in User.get_all() if u.role == 'Admin' and u.status == 'active']
        if len(admins) <= 1:
            return jsonify({"success": False, "message": "You cannot disable the last active administrator."}), 400

    new_status = 'inactive' if user.status == 'active' else 'active'
    try:
        user.update_details(role=user.role, email=user.email, status=new_status, full_name=user.full_name, phone=user.phone)
        return jsonify({"success": True, "new_status": new_status})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@db_management_bp.route('/admin/db-management/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_user(user_id):
    """Deletes admin/user securely."""
    user = User.get_by_id(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('db_management.index', tab='admins'))

    if user.id == session.get('user_id'):
        flash("You cannot delete your own logged-in admin account.", "danger")
        return redirect(url_for('db_management.index', tab='admins'))

    if user.role == 'Admin':
        admins = [u for u in User.get_all() if u.role == 'Admin' and u.status == 'active']
        if len(admins) <= 1:
            flash("You cannot delete the last active administrator.", "danger")
            return redirect(url_for('db_management.index', tab='admins'))

    try:
        username = user.username
        user.delete()
        log_deletion('users', user_id, session.get('username', 'Admin'), f"Username: {username}")
        flash(f"User account '{username}' has been permanently deleted.", "success")
    except Exception as e:
        if "foreign key" in str(e).lower() or "integrityerror" in str(type(e)).lower() or "violation" in str(e).lower():
            flash("This user account cannot be deleted because they are referenced in past transactions. You can toggle their status to inactive to disable the account.", "warning")
        else:
            flash(f"Deletion failed: {str(e)}", "danger")
    return redirect(url_for('db_management.index', tab='admins'))

# ----------------- PRODUCT ACTIONS -----------------

@db_management_bp.route('/admin/db-management/products/<int:prod_id>/edit', methods=['POST'])
@login_required
@role_required('Admin')
def edit_product(prod_id):
    """Updates product records from DB Panel."""
    product = Product.get_by_id(prod_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('db_management.index', tab='products'))

    try:
        product.update(
            name=request.form.get('name', '').strip(),
            category=request.form.get('category', '').strip(),
            brand=request.form.get('brand', '').strip(),
            purchase_price=float(request.form.get('purchase_price') or 0.0),
            selling_price=float(request.form.get('selling_price') or 0.0),
            mrp=float(request.form.get('mrp') or 0.0),
            quantity=float(request.form.get('quantity') or 0.0)
        )
        flash(f"Product '{product.name}' details updated.", "success")
    except Exception as e:
        flash(f"Update failed: {str(e)}", "danger")
    return redirect(url_for('db_management.index', tab='products'))

@db_management_bp.route('/admin/db-management/products/<int:prod_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_product(prod_id):
    """Deletes product permanently and logs."""
    product = Product.get_by_id(prod_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('db_management.index', tab='products'))

    try:
        p_name = product.name
        product.delete()
        log_deletion('products', prod_id, session.get('username', 'Admin'), f"Name: {p_name}")
        flash(f"Product '{p_name}' has been permanently deleted.", "success")
    except Exception as e:
        if "foreign key" in str(e).lower() or "integrityerror" in str(type(e)).lower() or "violation" in str(e).lower():
            flash("This product cannot be deleted because it is referenced in past sales invoices. You can set its stock to 0 to disable it.", "warning")
        else:
            flash(f"Deletion failed: {str(e)}", "danger")
    return redirect(url_for('db_management.index', tab='products'))

# ----------------- BILLING ACTIONS -----------------

@db_management_bp.route('/admin/db-management/billing/<int:bill_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_bill(bill_id):
    """Deletes billing record invoice from DB Panel."""
    # Fetch sale details
    sale_data = query_db("SELECT * FROM sales WHERE id = %s", (bill_id,), one=True)
    if not sale_data:
        flash("Billing invoice not found.", "danger")
        return redirect(url_for('db_management.index', tab='billing'))

    try:
        inv = sale_data['invoice_number']
        
        # Restore stock if not already cancelled before deleting
        if sale_data.get('status') != 'Cancelled':
            try:
                Sale.cancel_transaction(inv)
            except Exception as restoration_err:
                print(f"Stock restoration bypassed during deletion: {restoration_err}")

        # Delete billing references
        execute_db("DELETE FROM sales_items WHERE sale_id = %s", (bill_id,))
        execute_db("DELETE FROM sales WHERE id = %s", (bill_id,))
        
        log_deletion('sales', bill_id, session.get('username', 'Admin'), f"Invoice: {inv}")
        flash(f"Billing record '{inv}' deleted successfully.", "success")
    except Exception as e:
        flash(f"Deletion failed: {str(e)}", "danger")
    return redirect(url_for('db_management.index', tab='billing'))

# ----------------- OFFER & CUSTOMER ACTIONS -----------------

@db_management_bp.route('/admin/db-management/offers/<int:offer_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_offer(offer_id):
    """Deletes offer rule permanently and logs."""
    offer = Offer.get_by_id(offer_id)
    if not offer:
        flash("Offer not found.", "danger")
        return redirect(url_for('db_management.index', tab='offers'))

    try:
        o_name = offer.name
        offer.delete()
        log_deletion('offers', offer_id, session.get('username', 'Admin'), f"Name: {o_name}")
        flash(f"Offer '{o_name}' has been permanently deleted.", "success")
    except Exception as e:
        flash(f"Deletion failed: {str(e)}", "danger")
    return redirect(url_for('db_management.index', tab='offers'))

@db_management_bp.route('/admin/db-management/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_customer(customer_id):
    """Deletes customer record permanently and logs."""
    customer = Customer.get_by_id(customer_id)
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for('db_management.index', tab='customers'))

    try:
        c_name = customer.name
        customer.delete()
        log_deletion('customers', customer_id, session.get('username', 'Admin'), f"Name: {c_name}")
        flash(f"Customer '{c_name}' has been permanently deleted.", "success")
    except Exception as e:
        flash(f"Deletion failed: {str(e)}", "danger")
    return redirect(url_for('db_management.index', tab='customers'))
