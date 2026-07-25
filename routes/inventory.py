from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import login_required, role_required
from database.db import query_db, execute_db
from models.product import Product

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
@role_required('Employee')
def index():
    """
    Renders detailed inventory audit metrics, stock valuations, 
    low-stock lists, and logs stock adjustments (damaged/returned).
    """
    if request.method == 'POST':
        try:
            product_id = int(request.form.get('product_id'))
            action = request.form.get('action') # 'Damaged', 'Returned', 'Adjustment'
            quantity = float(request.form.get('quantity', 0.0))
            notes = request.form.get('notes', '').strip()
            source_dest = request.form.get('source_dest', 'Store').strip()

            product = Product.get_by_id(product_id)
            if not product:
                flash("Product not found.", "danger")
                return redirect(url_for('inventory.index'))

            # Adjust stock levels
            if action == 'Damaged':
                product.update(quantity=product.quantity - quantity)
            elif action == 'Returned':
                product.update(quantity=product.quantity + quantity)
            elif action == 'Adjustment':
                product.update(quantity=product.quantity + quantity)

            # Log to history in SQL
            execute_db(
                "INSERT INTO inventory_history (product_id, action, quantity, source_dest, notes, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
                (product_id, action, quantity, source_dest, notes, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )

            flash("Stock adjustment logged successfully!", "success")
        except Exception as e:
            flash(f"Error logging stock adjustment: {str(e)}", "danger")
        return redirect(url_for('inventory.index'))

    # Fetch stats
    products = Product.get_all()
    
    total_cost_val = sum(p.purchase_price * p.quantity for p in products)
    total_retail_val = sum(p.selling_price * p.quantity for p in products)
    
    low_stock_items = Product.get_low_stock(threshold=10)
    out_of_stock_items = Product.get_out_of_stock()

    return render_template(
        'inventory.html',
        products=products,
        total_cost_val=total_cost_val,
        total_retail_val=total_retail_val,
        low_stock_items=low_stock_items,
        out_of_stock_items=out_of_stock_items
    )
