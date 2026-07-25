from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from routes.auth import login_required, role_required
from models.supplier import Supplier

suppliers_bp = Blueprint('suppliers', __name__)

@suppliers_bp.route('/suppliers', methods=['GET', 'POST'])
@login_required
@role_required('Employee')
def index():
    """Lists suppliers or registers a new supplier."""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip() or None
            gst_number = request.form.get('gst_number', '').strip() or None
            balance = float(request.form.get('balance', 0.0))
            
            Supplier.create(name=name, phone=phone, email=email, gst_number=gst_number, balance=balance)
            flash("Supplier added successfully!", "success")
        except Exception as e:
            flash(f"Error adding supplier: {str(e)}", "danger")
        return redirect(url_for('suppliers.index'))

    suppliers = Supplier.get_all()
    return render_template('suppliers.html', suppliers=suppliers)

@suppliers_bp.route('/suppliers/edit/<int:supplier_id>', methods=['POST'])
@login_required
@role_required('Employee')
def edit(supplier_id):
    """Updates supplier information properties."""
    supplier = Supplier.get_by_id(supplier_id)
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers.index'))

    try:
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip() or None
        gst_number = request.form.get('gst_number', '').strip() or None
        balance = float(request.form.get('balance', 0.0))
        
        supplier.update(name=name, phone=phone, email=email, gst_number=gst_number, balance=balance)
        flash("Supplier details updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating supplier: {str(e)}", "danger")

    return redirect(url_for('suppliers.index'))

@suppliers_bp.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
@login_required
@role_required('Admin')
def delete(supplier_id):
    """Deletes supplier profile completely."""
    supplier = Supplier.get_by_id(supplier_id)
    if supplier:
        supplier.delete()
        flash("Supplier profile deleted successfully.", "success")
    else:
        flash("Supplier not found.", "danger")
    return redirect(url_for('suppliers.index'))

@suppliers_bp.route('/api/suppliers/<int:supplier_id>/products')
@login_required
def products_api(supplier_id):
    """API endpoint providing list of products supplied by the supplier."""
    supplier = Supplier.get_by_id(supplier_id)
    if not supplier:
        return jsonify({"success": False, "message": "Supplier not found."}), 404
        
    products = supplier.get_supplied_products()
    return jsonify({"success": True, "products": products})
