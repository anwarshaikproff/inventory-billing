from flask import Blueprint, render_template, jsonify, session, redirect, url_for
from routes.auth import login_required
from models.sale import Sale

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def home():
    """Redirect root access to appropriate view."""
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))

@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Renders main dashboard with analytical KPI counts."""
    stats = Sale.get_dashboard_stats()
    top_selling = Sale.get_top_selling_products(limit=5)
    least_selling = Sale.get_least_selling_products(limit=5)
    
    return render_template(
        'dashboard.html',
        stats=stats,
        top_selling=top_selling,
        least_selling=least_selling
    )

@dashboard_bp.route('/api/dashboard/charts')
@login_required
def chart_data():
    """API endpoint providing sales and profit trends for Chart.js."""
    data = Sale.get_sales_charts_data()
    return jsonify(data)
