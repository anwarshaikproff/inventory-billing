from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from routes.auth import login_required, role_required
from models.customer import Customer

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/customers', methods=['GET', 'POST'])
@login_required
@role_required('Cashier')
def index():
    """List all customers or create a new customer."""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip() or None
            address = request.form.get('address', '').strip() or None
            
            Customer.create(name=name, phone=phone, email=email, address=address)
            flash("Customer registered successfully!", "success")
        except Exception as e:
            flash(f"Error registering customer: {str(e)}", "danger")
        return redirect(url_for('customers.index'))

    customers = Customer.get_all()
    return render_template('customers.html', customers=customers)

@customers_bp.route('/customers/edit/<int:customer_id>', methods=['POST'])
@login_required
@role_required('Cashier')
def edit(customer_id):
    """Updates customer properties."""
    customer = Customer.get_by_id(customer_id)
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for('customers.index'))

    try:
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip() or None
        address = request.form.get('address', '').strip() or None
        reward_points = request.form.get('reward_points', 0)
        
        customer.update(name=name, phone=phone, email=email, address=address, reward_points=reward_points)
        flash("Customer details updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating customer: {str(e)}", "danger")

    return redirect(url_for('customers.index'))

@customers_bp.route('/customers/delete/<int:customer_id>', methods=['POST'])
@login_required
@role_required('Admin')
def delete(customer_id):
    """Removes a customer profile completely."""
    customer = Customer.get_by_id(customer_id)
    if customer:
        customer.delete()
        flash("Customer record removed successfully.", "success")
    else:
        flash("Customer not found.", "danger")
    return redirect(url_for('customers.index'))

@customers_bp.route('/api/customers/<int:customer_id>/history')
@login_required
def history_api(customer_id):
    """API endpoint providing customer invoice sales history."""
    customer = Customer.get_by_id(customer_id)
    if not customer:
        return jsonify({"success": False, "message": "Customer not found."}), 404
    
    history = customer.get_purchase_history()
    return jsonify({"success": True, "history": history})
