import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from routes.auth import login_required, role_required
from models.settings import Settings

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('Admin')  # Only Admin role can alter settings
def index():
    """Renders store setup properties form and logs backup lists."""
    if request.method == 'POST':
        # Collect store settings
        store_settings = {
            'store_name': request.form.get('store_name', '').strip(),
            'store_gst': request.form.get('store_gst', '').strip(),
            'store_address': request.form.get('store_address', '').strip(),
            'store_phone': request.form.get('store_phone', '').strip(),
            'store_email': request.form.get('store_email', '').strip(),
            'invoice_footer': request.form.get('invoice_footer', '').strip(),
            'currency': request.form.get('currency', 'INR').strip(),
            'tax_enabled': '1' if request.form.get('tax_enabled') else '0',
            'tax_rate_default': request.form.get('tax_rate_default', '18.0').strip(),
            'auto_backup_enabled': '1' if request.form.get('auto_backup_enabled') else '0'
        }

        # Handling Store Logo Upload
        logo_file = request.files.get('store_logo')
        if logo_file and logo_file.filename:
            filename = secure_filename(logo_file.filename)
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            logo_path = os.path.join(upload_dir, filename)
            logo_file.save(logo_path)
            store_settings['store_logo'] = f"static/uploads/{filename}"

        try:
            Settings.update_multiple(store_settings)
            flash("Store settings updated successfully!", "success")
        except Exception as e:
            flash(f"Error saving settings: {str(e)}", "danger")

        return redirect(url_for('settings.index'))

    configs = Settings.get_all()
    backups = Settings.get_backups()
    return render_template('settings.html', configs=configs, backups=backups)

@settings_bp.route('/settings/backup', methods=['POST'])
@login_required
@role_required('Admin')
def trigger_backup():
    """Manually creates a database backup file."""
    try:
        backup_path = Settings.backup_database()
        filename = os.path.basename(backup_path)
        flash(f"Database backup created successfully: {filename}", "success")
    except Exception as e:
        flash(f"Backup failed: {str(e)}", "danger")
        
    return redirect(url_for('settings.index'))

@settings_bp.route('/settings/restore/<int:backup_id>', methods=['POST'])
@login_required
@role_required('Admin')
def restore_backup(backup_id):
    """Restores database state to a previously archived backup file."""
    try:
        Settings.restore_database(backup_id)
        flash("Database restored successfully! Refreshing database snapshot.", "success")
    except Exception as e:
        flash(f"Database restore failed: {str(e)}", "danger")
        
    return redirect(url_for('settings.index'))

@settings_bp.route('/settings/restore_upload', methods=['POST'])
@login_required
@role_required('Admin')
def restore_upload():
    """Restores database from an uploaded sqlite .db backup file."""
    db_file = request.files.get('backup_file')
    if db_file and db_file.filename.endswith('.db'):
        filename = secure_filename(db_file.filename)
        temp_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, filename)
        db_file.save(temp_path)
        
        try:
            Settings.restore_from_file(temp_path)
            flash("Database state successfully restored from uploaded file!", "success")
        except Exception as e:
            flash(f"Restore failed: {str(e)}", "danger")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    else:
        flash("Invalid file format. Please upload a valid SQLite backup database (.db) file.", "danger")
        
    return redirect(url_for('settings.index'))
