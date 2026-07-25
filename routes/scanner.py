import base64
import numpy as np
from flask import Blueprint, request, jsonify
from routes.auth import login_required
from models.product import Product

# Graceful import of OpenCV and Pyzbar
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

try:
    from pyzbar.pyzbar import decode
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

scanner_bp = Blueprint('scanner', __name__)

@scanner_bp.route('/api/scanner/scan', methods=['POST'])
@login_required
def scan_webcam_frame():
    """
    Decodes frame images received from POS webcam and extracts barcode.
    Returns product info or failure triggers.
    """
    if not OPENCV_AVAILABLE or not PYZBAR_AVAILABLE:
        return jsonify({
            "success": False, 
            "message": "Server-side scanning is disabled (OpenCV/Pyzbar native dependencies are not installed on this OS)."
        }), 501

    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"success": False, "message": "No image data received."}), 400

    try:
        # Base64 image decode: data:image/png;base64,...
        header, encoded = data['image'].split(',', 1)
        image_data = base64.b64decode(encoded)
        
        # Convert binary string to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"success": False, "message": "Could not decode frame image."}), 400

        # Run pyzbar scanning
        barcodes = decode(img)
        if not barcodes:
            return jsonify({"success": False, "message": "No barcode or QR code detected in frame."})

        # Process first scanned barcode
        scanned_obj = barcodes[0]
        barcode_str = scanned_obj.data.decode('utf-8').strip()
        
        # Query product by barcode
        product = Product.get_by_barcode(barcode_str)
        if product:
            return jsonify({
                "success": True,
                "found": True,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "product_id": product.product_id,
                    "barcode": product.barcode,
                    "selling_price": product.selling_price,
                    "mrp": product.mrp,
                    "quantity": product.quantity,
                    "unit": product.unit,
                    "gst": product.gst,
                    "discount": product.discount
                }
            })
        else:
            return jsonify({
                "success": True,
                "found": False,
                "barcode": barcode_str,
                "message": "Product Not Found"
            })
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Scanner error: {str(e)}"}), 500
