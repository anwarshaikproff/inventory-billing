from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import login_required, role_required
from models.offer import Offer

offers_bp = Blueprint('offers', __name__)

@offers_bp.route('/offers', methods=['GET', 'POST'])
@login_required
@role_required('Employee')
def index():
    """Renders discounts control board and creates new offers."""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            type_val = request.form.get('type', '').strip()
            value = float(request.form.get('value') or 0.0)
            min_purchase = float(request.form.get('min_purchase') or 0.0)
            code = request.form.get('code', '').strip() or None
            start_date = request.form.get('start_date') or None
            end_date = request.form.get('end_date') or None
            active = 1 if request.form.get('active') else 0

            Offer.create(
                name=name, type=type_val, value=value, min_purchase=min_purchase,
                code=code, start_date=start_date, end_date=end_date, active=active
            )
            flash("Offer created successfully!", "success")
        except Exception as e:
            flash(f"Error creating offer: {str(e)}", "danger")
        return redirect(url_for('offers.index'))

    offers = Offer.get_all()
    return render_template('offers.html', offers=offers)

@offers_bp.route('/offers/edit/<int:offer_id>', methods=['POST'])
@login_required
@role_required('Employee')
def edit(offer_id):
    """Updates selected offer rule attributes."""
    offer = Offer.get_by_id(offer_id)
    if not offer:
        flash("Offer rule not found.", "danger")
        return redirect(url_for('offers.index'))

    try:
        name = request.form.get('name', '').strip()
        type_val = request.form.get('type', '').strip()
        value = float(request.form.get('value') or 0.0)
        min_purchase = float(request.form.get('min_purchase') or 0.0)
        code = request.form.get('code', '').strip() or None
        start_date = request.form.get('start_date') or None
        end_date = request.form.get('end_date') or None
        active = 1 if request.form.get('active') else 0

        offer.update(
            name=name, type=type_val, value=value, min_purchase=min_purchase,
            code=code, start_date=start_date, end_date=end_date, active=active
        )
        flash("Offer updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating offer: {str(e)}", "danger")

    return redirect(url_for('offers.index'))

@offers_bp.route('/offers/delete/<int:offer_id>', methods=['POST'])
@login_required
@role_required('Admin')
def delete(offer_id):
    """Removes a discount offer rule permanently."""
    offer = Offer.get_by_id(offer_id)
    if offer:
        offer.delete()
        flash("Offer rule deleted successfully.", "success")
    else:
        flash("Offer rule not found.", "danger")
    return redirect(url_for('offers.index'))
