from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from models.user import User

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """Decorator to restrict access to authenticated sessions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        user = User.get_by_id(session['user_id'])
        if not user:
            session.clear()
            flash("Session expired or user not found. Please log in again.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    """Decorator to enforce role permissions hierarchy."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            user = User.get_by_id(session['user_id'])
            if not user:
                session.clear()
                flash("Session expired. Please log in again.", "warning")
                return redirect(url_for('auth.login'))
            if not user.has_permission(role_name):
                flash("Access Denied: Insufficient privileges.", "danger")
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin/Employee/Cashier login handler."""
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.authenticate(username, password)
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f"Welcome back, {user.username}! Logged in as {user.role}.", "success")
            return redirect(url_for('dashboard.index'))
        else:
            flash("Invalid credentials or account is suspended.", "danger")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Clear session and log out."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Admin registration handler."""
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not (full_name and username and email and phone and password and confirm_password):
            flash("All fields are required.", "danger")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html')

        try:
            # Create the Admin user
            User.create(
                username=username,
                password=password,
                role='Admin',
                email=email,
                full_name=full_name,
                phone=phone
            )
            flash("Admin registered successfully! Please sign in.", "success")
            return redirect(url_for('auth.login'))
        except ValueError as e:
            flash(str(e), "danger")

    return render_template('register.html')

