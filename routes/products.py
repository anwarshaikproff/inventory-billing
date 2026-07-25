import os
import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, current_app
from werkzeug.utils import secure_filename
from routes.auth import login_required, role_required
from models.product import Product
from models.supplier import Supplier
from utils.barcode_gen import generate_barcode, generate_qrcode, build_barcode_pdf_sheet

products_bp = Blueprint('products', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@products_bp.route('/products')
@login_required
@role_required('Employee')
def index():
    """Renders product dashboard table with categories and suppliers."""
    products = Product.get_all()
    suppliers = Supplier.get_all()
    
    # Extract unique categories
    categories = sorted(list(set(p.category for p in products if p.category)))
    
    return render_template(
        'products.html',
        products=products,
        suppliers=suppliers,
        categories=categories
    )

@products_bp.route('/products/add', methods=['POST'])
@login_required
@role_required('Employee')
def add_product():
    """Handles product creation, barcode/QR rendering, and image upload."""
    try:
        # File Upload
        image_file = request.files.get('product_image')
        image_path = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            image_path = os.path.join(upload_dir, filename)
            image_file.save(image_path)
            # relative path to store in db
            image_path = f"static/uploads/{filename}"

        # Setup Auto Barcode if empty
        barcode_val = request.form.get('barcode', '').strip()
        if not barcode_val:
            barcode_val = "200" + "".join(random.choices("0123456789", k=9))
            
        qrcode_val = request.form.get('qrcode', '').strip()
        if not qrcode_val:
            qrcode_val = barcode_val

        # Call generators
        bc_img_rel = generate_barcode(barcode_val, 'Code128')
        qr_img_rel = generate_qrcode(qrcode_val)

        payload = {
            'name': request.form.get('name', '').strip(),
            'product_id': request.form.get('product_id', '').strip(),
            'barcode': barcode_val,
            'qrcode': qrcode_val,
            'category': request.form.get('category', '').strip() or 'General',
            'brand': request.form.get('brand', '').strip() or 'Generic',
            'supplier_id': request.form.get('supplier_id') or None,
            'purchase_price': float(request.form.get('purchase_price') or 0.0),
            'mrp': float(request.form.get('mrp') or 0.0),
            'selling_price': float(request.form.get('selling_price') or 0.0),
            'gst': float(request.form.get('gst') or 0.0),
            'discount': float(request.form.get('discount') or 0.0),
            'quantity': float(request.form.get('quantity') or 0.0),
            'unit': request.form.get('unit', 'pcs'),
            'weight': float(request.form.get('weight')) if request.form.get('weight') else None,
            'expiry_date': request.form.get('expiry_date') or None,
            'mfg_date': request.form.get('mfg_date') or None,
            'description': request.form.get('description', '').strip(),
            'image_path': image_path
        }

        Product.create(**payload)
        flash("Product added successfully!", "success")
    except Exception as e:
        flash(f"Error adding product: {str(e)}", "danger")

    return redirect(url_for('products.index'))

@products_bp.route('/products/edit/<int:product_id>', methods=['POST'])
@login_required
@role_required('Employee')
def edit_product(product_id):
    """Updates product records and processes secondary image uploads."""
    product = Product.get_by_id(product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('products.index'))

    try:
        # File Upload
        image_file = request.files.get('product_image')
        image_path = product.image_path
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            dest_image_path = os.path.join(upload_dir, filename)
            image_file.save(dest_image_path)
            image_path = f"static/uploads/{filename}"

        # Read Barcode
        barcode_val = request.form.get('barcode', '').strip() or product.barcode
        qrcode_val = request.form.get('qrcode', '').strip() or product.qrcode

        # Re-render barcodes if updated
        if barcode_val != product.barcode:
            generate_barcode(barcode_val, 'Code128')
        if qrcode_val != product.qrcode:
            generate_qrcode(qrcode_val)

        payload = {
            'name': request.form.get('name', '').strip(),
            'product_id': request.form.get('product_id', '').strip(),
            'barcode': barcode_val,
            'qrcode': qrcode_val,
            'category': request.form.get('category', '').strip() or 'General',
            'brand': request.form.get('brand', '').strip() or 'Generic',
            'supplier_id': request.form.get('supplier_id') or None,
            'purchase_price': float(request.form.get('purchase_price') or 0.0),
            'mrp': float(request.form.get('mrp') or 0.0),
            'selling_price': float(request.form.get('selling_price') or 0.0),
            'gst': float(request.form.get('gst') or 0.0),
            'discount': float(request.form.get('discount') or 0.0),
            'quantity': float(request.form.get('quantity') or 0.0),
            'unit': request.form.get('unit', 'pcs'),
            'weight': float(request.form.get('weight')) if request.form.get('weight') else None,
            'expiry_date': request.form.get('expiry_date') or None,
            'mfg_date': request.form.get('mfg_date') or None,
            'description': request.form.get('description', '').strip(),
            'image_path': image_path
        }

        product.update(**payload)
        flash("Product updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating product: {str(e)}", "danger")

    return redirect(url_for('products.index'))

@products_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
@role_required('Admin')  # Only admin can delete products
def delete_product(product_id):
    """Deletes a product completely from DB."""
    product = Product.get_by_id(product_id)
    if product:
        try:
            product.delete()
            flash("Product deleted successfully.", "success")
        except Exception as e:
            flash("This product cannot be deleted because it is referenced in past sales invoices. You can set its stock to 0 to disable it.", "warning")
    else:
        flash("Product not found.", "danger")
    return redirect(url_for('products.index'))

@products_bp.route('/products/import', methods=['POST'])
@login_required
@role_required('Employee')
def import_excel():
    """Import spreadsheet products list."""
    excel_file = request.files.get('excel_file')
    if excel_file and allowed_file(excel_file.filename):
        filename = secure_filename(excel_file.filename)
        temp_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, filename)
        excel_file.save(temp_path)

        try:
            count = Product.import_from_excel(temp_path)
            flash(f"Successfully imported {count} products!", "success")
        except Exception as e:
            flash(f"Import failed: {str(e)}", "danger")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    else:
        flash("Invalid file uploaded. Only Excel sheets (.xlsx / .xls) are permitted.", "danger")
        
    return redirect(url_for('products.index'))

@products_bp.route('/products/export', methods=['GET'])
@login_required
@role_required('Employee')
def export_excel():
    """Download database inventory as Excel format."""
    export_dir = os.path.join(current_app.root_path, 'static', 'uploads')
    os.makedirs(export_dir, exist_ok=True)
    dest_path = os.path.join(export_dir, 'products_export.xlsx')
    
    try:
        Product.export_to_excel(dest_path)
        return send_file(dest_path, as_attachment=True, download_name='products_export.xlsx')
    except Exception as e:
        flash(f"Export failed: {str(e)}", "danger")
        return redirect(url_for('products.index'))

@products_bp.route('/products/print_barcode/<int:product_id>')
@login_required
@role_required('Employee')
def print_barcode(product_id):
    """Generates and downloads a printable PDF of barcode sticker sheet."""
    product = Product.get_by_id(product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('products.index'))

    label_count = request.args.get('count', 24, type=int)
    pdf_dir = os.path.join(current_app.root_path, 'static', 'uploads')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"barcodes_{product.product_id}.pdf")

    try:
        build_barcode_pdf_sheet(product, label_count, pdf_path)
        return send_file(pdf_path, as_attachment=True, download_name=f"barcodes_{product.product_id}.pdf")
    except Exception as e:
        flash(f"Sticker PDF generation failed: {str(e)}", "danger")
        return redirect(url_for('products.index'))

@products_bp.route('/api/products/search')
@login_required
def search_ajax():
    """JSON auto-completion endpoint for cashier searches."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    products = Product.search(query)
    # Serialize for JSON consumption
    results = []
    for p in products:
        results.append({
            'id': p.id,
            'product_id': p.product_id,
            'name': p.name,
            'barcode': p.barcode,
            'selling_price': p.selling_price,
            'mrp': p.mrp,
            'quantity': p.quantity,
            'unit': p.unit,
            'gst': p.gst,
            'discount': p.discount
        })
    return jsonify(results)
