from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import database.db as db_module
from database.db import query_db, execute_db, get_db_status, translate_query

billing_bp = Blueprint('billing', __name__)

def _get_db_type():
    """Safely returns the current chosen DB type at runtime."""
    return db_module._CHOSEN_DB_TYPE

@billing_bp.route('/')
@billing_bp.route('/bills')
def index():
    """Renders the main unified billing UI with recent billing transactions."""
    try:
        bills = query_db("SELECT * FROM billing ORDER BY bill_date DESC")
        if bills is None:
            bills = []
    except Exception as e:
        print(f"Notice fetching bills: {e}")
        bills = []

    # Compute sales statistics
    total_revenue = 0.0
    total_cash = 0.0
    total_online = 0.0
    for b in bills:
        try:
            price = float(b.get('item_price') or 0.0)
            total_revenue += price
            pay_type = str(b.get('payment_type', '')).lower()
            if 'cash' in pay_type:
                total_cash += price
            else:
                total_online += price
        except Exception:
            pass

    stats = {
        "total_revenue": round(total_revenue, 2),
        "total_bills": len(bills),
        "total_cash": round(total_cash, 2),
        "total_online": round(total_online, 2)
    }
    return render_template('billing.html', bills=bills, stats=stats)

@billing_bp.route('/api/bill', methods=['POST'])
def add_bill():
    """API endpoint to record a new billing transaction."""
    try:
        data = request.get_json() if request.is_json else request.form

        customer_name = (data.get('customer_name') or '').strip()
        phone_no = (data.get('phone_no') or '').strip()
        item_name = (data.get('item_name') or '').strip()

        try:
            cost_of_the_item = float(data.get('cost_of_the_item', 0))
        except (TypeError, ValueError):
            cost_of_the_item = 0.0

        try:
            item_qty = float(data.get('item_qty', 1))
        except (TypeError, ValueError):
            item_qty = 1.0

        item_price = round(cost_of_the_item * item_qty, 2)
        payment_type = (data.get('payment_type') or 'cash').lower().strip()

        if payment_type not in ('cash', 'online'):
            payment_type = 'cash'

        if not customer_name or not phone_no or not item_name:
            err_msg = "Customer Name, Phone No, and Item Name are required!"
            if request.is_json:
                return jsonify({"status": "error", "message": err_msg}), 400
            flash(err_msg, "danger")
            return redirect(url_for('billing.index'))

        is_sqlite = (_get_db_type() == 'SQLite')
        query = translate_query(
            "INSERT INTO billing (customer_name, phone_no, item_name, cost_of_the_item, item_qty, item_price, payment_type) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            is_sqlite
        )
        bill_id = execute_db(query, (customer_name, phone_no, item_name, cost_of_the_item, item_qty, item_price, payment_type), commit=True)

        if request.is_json:
            return jsonify({
                "status": "success",
                "message": "Bill saved successfully!",
                "bill_id": bill_id,
                "bill": {
                    "id": bill_id,
                    "customer_name": customer_name,
                    "phone_no": phone_no,
                    "item_name": item_name,
                    "cost_of_the_item": cost_of_the_item,
                    "item_qty": item_qty,
                    "item_price": item_price,
                    "payment_type": payment_type
                }
            }), 201
        flash("Bill saved successfully!", "success")
        return redirect(url_for('billing.index'))

    except Exception as e:
        print(f"Error saving bill: {e}")
        if request.is_json:
            return jsonify({"status": "error", "message": str(e)}), 500
        flash(f"Error saving bill: {e}", "danger")
        return redirect(url_for('billing.index'))

@billing_bp.route('/api/bill/<int:bill_id>', methods=['DELETE'])
def delete_bill(bill_id):
    """Deletes a billing record by ID."""
    try:
        is_sqlite = (_get_db_type() == 'SQLite')
        query = translate_query("DELETE FROM billing WHERE id = %s", is_sqlite)
        execute_db(query, (bill_id,), commit=True)
        return jsonify({"status": "success", "message": f"Bill #{bill_id} deleted."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@billing_bp.route('/api/status')
def status():
    """Returns current cloud DB connection status."""
    return jsonify(get_db_status())
