from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, session, current_app
import os
from routes.auth import login_required, role_required
from models.sale import Sale
from models.customer import Customer
from models.offer import Offer
from models.product import Product
from models.settings import Settings
from utils.pdf_generator import generate_invoice_pdf

pos_bp = Blueprint('pos', __name__)

@pos_bp.route('/pos')
@login_required
@role_required('Cashier')  # Cashier role or higher is required
def index():
    """Renders cashier POS billing window."""
    customers = Customer.get_all()
    # Fetch active coupons to display on search side panel
    active_coupons = [o for o in Offer.get_active_offers() if o.code]
    return render_template(
        'pos.html',
        customers=customers,
        active_coupons=active_coupons
    )

@pos_bp.route('/pos/checkout', methods=['POST'])
@login_required
@role_required('Cashier')
def checkout():
    """Processes checkouts from POSTed cart JSON."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid request payload."}), 400

    customer_id = int(data.get('customer_id')) if data.get('customer_id') else None
    customer_name = (data.get('customer_name') or '').strip()
    customer_phone = (data.get('customer_phone') or '').strip()
    customer_email = (data.get('customer_email') or '').strip() or None
    customer_address = (data.get('customer_address') or '').strip() or None

    # If customer is not in registry but phone number is provided, search or create customer profile
    if not customer_id and customer_phone:
        existing_customer = Customer.get_by_phone(customer_phone)
        if existing_customer:
            customer_id = existing_customer.id
        else:
            if not customer_name:
                customer_name = f"Walk-in ({customer_phone})"
            try:
                new_cust = Customer.create(
                    name=customer_name,
                    phone=customer_phone,
                    email=customer_email,
                    address=customer_address
                )
                customer_id = new_cust.id
            except Exception as creation_err:
                print(f"Bypassed auto customer registration: {creation_err}")

    cart_items = data.get('cart')
    payment_mode = data.get('payment_mode')
    cash_received = float(data.get('cash_received') or 0.0)
    coupon_code = (data.get('coupon_code') or '').strip() or None
    is_student = bool(data.get('is_student', False))

    if not cart_items:
        return jsonify({"success": False, "message": "Cart is empty."}), 400

    try:
        cashier_id = session['user_id']
        # Execute POS transaction
        invoice_number = Sale.create_transaction(
            customer_id=customer_id,
            cashier_id=cashier_id,
            cart_items=cart_items,
            payment_mode=payment_mode,
            cash_received=cash_received,
            coupon_code=coupon_code,
            is_student=is_student
        )
        return jsonify({"success": True, "invoice_number": invoice_number})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@pos_bp.route('/pos/invoice/<invoice_number>')
@login_required
def invoice_view(invoice_number):
    """HTML detailed receipt view of an completed invoice."""
    details = Sale.get_invoice_details(invoice_number)
    if not details:
        flash("Invoice not found.", "danger")
        return redirect(url_for('dashboard.index'))
    
    # Store settings for header/footer invoice rendering
    store_meta = {
        'name': Settings.get('store_name', 'SKML Mobiles'),
        'address': Settings.get('store_address', '101, Business Hub, Sector 5, Tech City'),
        'phone': Settings.get('store_phone', '+91 9876543210'),
        'email': Settings.get('store_email', 'billing@techmart.com'),
        'gst': Settings.get('store_gst', '27AAPCS1234F1Z5'),
        'footer': Settings.get('invoice_footer', 'Thank you for shopping!')
    }
    
    return render_template(
        'invoice.html',
        details=details,
        store=store_meta
    )

@pos_bp.route('/pos/invoice/<invoice_number>/download')
@login_required
def invoice_download(invoice_number):
    """Builds and serves PDF receipt for download."""
    details = Sale.get_invoice_details(invoice_number)
    if not details:
        flash("Invoice not found.", "danger")
        return redirect(url_for('dashboard.index'))

    # Inject store settings
    details['store'] = {
        'name': Settings.get('store_name', 'SKML Mobiles'),
        'address': Settings.get('store_address', '101, Business Hub, Sector 5, Tech City'),
        'phone': Settings.get('store_phone', '+91 9876543210'),
        'email': Settings.get('store_email', 'billing@techmart.com'),
        'gst': Settings.get('store_gst', '27AAPCS1234F1Z5'),
        'footer': Settings.get('invoice_footer', 'Thank you for shopping!')
    }

    # Destination PDF Path
    pdf_dir = os.path.join(current_app.root_path, 'static', 'invoice')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_filename = f"{invoice_number}.pdf"
    dest_path = os.path.join(pdf_dir, pdf_filename)

    try:
        generate_invoice_pdf(details, dest_path)
        return send_file(dest_path, as_attachment=True, download_name=pdf_filename)
    except Exception as e:
        flash(f"Error compiling PDF: {str(e)}", "danger")
        return redirect(url_for('pos.invoice_view', invoice_number=invoice_number))

@pos_bp.route('/api/pos/check_coupon')
@login_required
def check_coupon():
    """Ajax endpoint verifying coupon validation details."""
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({"valid": False, "message": "Coupon code is empty."})
        
    coupon = Offer.get_by_code(code)
    if coupon:
        return jsonify({
            "valid": True,
            "name": coupon.name,
            "type": coupon.type,
            "value": coupon.value,
            "min_purchase": coupon.min_purchase
        })
    return jsonify({"valid": False, "message": "Coupon code is invalid or expired."})

@pos_bp.route('/pos/history')
@login_required
@role_required('Employee')
def history():
    """Renders billing/invoice logs and search panel."""
    sales = Sale.get_all()
    query = request.args.get('search', '').strip()
    if query:
        filtered = []
        for s in sales:
            if (query.lower() in s.get('invoice_number', '').lower() or
                query.lower() in s.get('customer_name', '').lower() or
                query.lower() in s.get('cashier_username', '').lower() or
                query.lower() in s.get('payment_mode', '').lower()):
                filtered.append(s)
        sales = filtered
    return render_template('pos_history.html', sales=sales, search_query=query)

@pos_bp.route('/pos/invoice/<invoice_number>/cancel', methods=['POST'])
@login_required
@role_required('Admin')
def cancel_invoice(invoice_number):
    """Cancels a sale transaction, restores stock levels, and records a Customer Return."""
    try:
        Sale.cancel_transaction(invoice_number)
        flash(f"Invoice {invoice_number} has been cancelled successfully, and stock has been restored.", "success")
    except Exception as e:
        flash(f"Error cancelling invoice: {str(e)}", "danger")
    return redirect(url_for('pos.history'))


