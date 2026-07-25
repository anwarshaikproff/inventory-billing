import os
import pandas as pd
from datetime import datetime
from database.db import query_db, execute_db

def get_stock_status(quantity):
    qty = float(quantity or 0.0)
    if qty <= 0:
        return 'Out of Stock'
    elif qty <= 10.0:
        return 'Low Stock'
    return 'In Stock'

class Product:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.product_id = kwargs.get('product_id')
        self.barcode = kwargs.get('barcode')
        self.qrcode = kwargs.get('qrcode')
        self.category = kwargs.get('category')
        self.brand = kwargs.get('brand')
        self.supplier_id = kwargs.get('supplier_id')
        self.purchase_price = float(kwargs.get('purchase_price', 0.0))
        self.mrp = float(kwargs.get('mrp', 0.0))
        self.selling_price = float(kwargs.get('selling_price', 0.0))
        self.gst = float(kwargs.get('gst', 0.0))
        self.discount = float(kwargs.get('discount', 0.0))
        self.quantity = float(kwargs.get('quantity', 0.0))
        self.unit = kwargs.get('unit', 'pcs')
        self.weight = float(kwargs.get('weight')) if kwargs.get('weight') is not None else None
        self.expiry_date = kwargs.get('expiry_date')
        self.mfg_date = kwargs.get('mfg_date')
        self.description = kwargs.get('description')
        self.image_path = kwargs.get('image_path')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.stock_status = kwargs.get('stock_status') or get_stock_status(self.quantity)

    @classmethod
    def get_by_id(cls, db_id):
        """Get product by internal primary key."""
        row = query_db("SELECT * FROM products WHERE id = %s", (db_id,), one=True)
        if row:
            return cls(**row)
        return None

    @classmethod
    def get_by_product_id(cls, product_id):
        """Get product by custom product string ID."""
        row = query_db("SELECT * FROM products WHERE product_id = %s", (product_id,), one=True)
        if row:
            return cls(**row)
        return None

    @classmethod
    def get_by_barcode(cls, barcode):
        """Get product by barcode or qrcode scanner value."""
        row = query_db("SELECT * FROM products WHERE barcode = %s OR qrcode = %s", (barcode, barcode), one=True)
        if row:
            return cls(**row)
        return None

    @classmethod
    def get_all(cls):
        """Get all products in the database."""
        rows = query_db("SELECT * FROM products ORDER BY id DESC")
        return [cls(**r) for r in rows]

    @classmethod
    def create(cls, **data):
        """
        Creates a new product with duplicate prevention checks.
        Validates product_id, barcode and qrcode uniqueness.
        """
        if cls.get_by_product_id(data.get('product_id')):
            raise ValueError(f"Product ID '{data.get('product_id')}' already exists.")
        
        bc = data.get('barcode')
        if bc and cls.get_by_barcode(bc):
            raise ValueError(f"Barcode or QR Code '{bc}' already exists.")
            
        qc = data.get('qrcode')
        if qc and cls.get_by_barcode(qc):
            raise ValueError(f"QR Code or Barcode '{qc}' already exists.")

        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        qty = float(data.get('quantity', 0.0))
        stock_status = get_stock_status(qty)

        p_id = execute_db(
            """INSERT INTO products (
                name, product_id, barcode, qrcode, category, brand, supplier_id,
                purchase_price, mrp, selling_price, gst, discount, quantity,
                unit, weight, expiry_date, mfg_date, description, image_path,
                created_at, updated_at, stock_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                data.get('name'), data.get('product_id'), data.get('barcode'), data.get('qrcode'),
                data.get('category'), data.get('brand'), data.get('supplier_id'),
                float(data.get('purchase_price', 0.0)), float(data.get('mrp', 0.0)), float(data.get('selling_price', 0.0)),
                float(data.get('gst', 0.0)), float(data.get('discount', 0.0)), qty,
                data.get('unit', 'pcs'), data.get('weight'), data.get('expiry_date'), data.get('mfg_date'),
                data.get('description'), data.get('image_path'), created_at, created_at, stock_status
            )
        )

        if not p_id:
            row = query_db("SELECT id FROM products WHERE product_id = %s", (data.get('product_id'),), one=True)
            if row:
                p_id = row['id']

        # Log to Inventory History
        execute_db(
            "INSERT INTO inventory_history (product_id, action, quantity, source_dest, notes, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
            (p_id, 'Stock In', qty, 'Store', 'Initial Stock Addition', created_at)
        )

        return cls.get_by_id(p_id)

    def update(self, **data):
        """Updates product information and logs inventory changes."""
        pid = data.get('product_id')
        if pid and pid != self.product_id:
            existing = self.get_by_product_id(pid)
            if existing and existing.id != self.id:
                raise ValueError(f"Product ID '{pid}' already exists on another product.")
        
        bc = data.get('barcode')
        if bc and bc != self.barcode:
            existing = self.get_by_barcode(bc)
            if existing and existing.id != self.id:
                raise ValueError(f"Barcode/QR Code '{bc}' already exists on another product.")
                
        qc = data.get('qrcode')
        if qc and qc != self.qrcode:
            existing = self.get_by_barcode(qc)
            if existing and existing.id != self.id:
                raise ValueError(f"QR Code/Barcode '{qc}' already exists on another product.")

        new_qty = float(data.get('quantity', self.quantity))
        old_qty = self.quantity
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if new_qty != old_qty:
            diff = new_qty - old_qty
            action = 'Stock In' if diff > 0 else 'Adjustment'
            execute_db(
                "INSERT INTO inventory_history (product_id, action, quantity, source_dest, notes, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
                (self.id, action, abs(diff), 'Store', f"Stock quantity manually updated from {old_qty} to {new_qty}", created_at)
            )

        stock_status = get_stock_status(new_qty)

        execute_db(
            """UPDATE products SET
                name = %s, product_id = %s, barcode = %s, qrcode = %s, category = %s, brand = %s, supplier_id = %s,
                purchase_price = %s, mrp = %s, selling_price = %s, gst = %s, discount = %s, quantity = %s,
                unit = %s, weight = %s, expiry_date = %s, mfg_date = %s, description = %s, image_path = %s,
                updated_at = %s, stock_status = %s WHERE id = %s""",
            (
                data.get('name', self.name), data.get('product_id', self.product_id), data.get('barcode', self.barcode), data.get('qrcode', self.qrcode),
                data.get('category', self.category), data.get('brand', self.brand), data.get('supplier_id', self.supplier_id),
                float(data.get('purchase_price', self.purchase_price)), float(data.get('mrp', self.mrp)), float(data.get('selling_price', self.selling_price)),
                float(data.get('gst', self.gst)), float(data.get('discount', self.discount)), new_qty,
                data.get('unit', self.unit), data.get('weight', self.weight), data.get('expiry_date', self.expiry_date), data.get('mfg_date', self.mfg_date),
                data.get('description', self.description), data.get('image_path', self.image_path), created_at, stock_status, self.id
            )
        )

        # Refresh self
        self.name = data.get('name', self.name)
        self.product_id = data.get('product_id', self.product_id)
        self.barcode = data.get('barcode', self.barcode)
        self.qrcode = data.get('qrcode', self.qrcode)
        self.category = data.get('category', self.category)
        self.brand = data.get('brand', self.brand)
        self.supplier_id = data.get('supplier_id', self.supplier_id)
        self.purchase_price = float(data.get('purchase_price', self.purchase_price))
        self.mrp = float(data.get('mrp', self.mrp))
        self.selling_price = float(data.get('selling_price', self.selling_price))
        self.gst = float(data.get('gst', self.gst))
        self.discount = float(data.get('discount', self.discount))
        self.quantity = new_qty
        self.unit = data.get('unit', self.unit)
        self.weight = data.get('weight', self.weight)
        self.expiry_date = data.get('expiry_date', self.expiry_date)
        self.mfg_date = data.get('mfg_date', self.mfg_date)
        self.description = data.get('description', self.description)
        self.image_path = data.get('image_path', self.image_path)
        self.updated_at = created_at
        self.stock_status = stock_status

    def delete(self):
        """Remove product and clean up its inventory logs."""
        execute_db("DELETE FROM inventory_history WHERE product_id = %s", (self.id,))
        execute_db("DELETE FROM products WHERE id = %s", (self.id,))

    @classmethod
    def search(cls, query_string):
        """Search products by name, product_id, category, barcode, or brand using SQL LIKE."""
        q = f"%{query_string.lower()}%"
        rows = query_db(
            """SELECT * FROM products WHERE
                LOWER(name) LIKE %s OR LOWER(product_id) LIKE %s OR barcode = %s OR qrcode = %s OR
                LOWER(category) LIKE %s OR LOWER(brand) LIKE %s ORDER BY name ASC""",
            (q, q, query_string, query_string, q, q)
        )
        return [cls(**row) for row in rows]

    @classmethod
    def get_low_stock(cls, threshold=10.0):
        """Fetch products where stock level is at or below threshold and above zero."""
        rows = query_db("SELECT * FROM products WHERE quantity <= %s AND quantity > 0 ORDER BY quantity ASC", (threshold,))
        return [cls(**row) for row in rows]

    @classmethod
    def get_out_of_stock(cls):
        """Fetch products with zero or negative stock levels."""
        rows = query_db("SELECT * FROM products WHERE quantity <= 0 ORDER BY id DESC")
        return [cls(**row) for row in rows]

    @classmethod
    def import_from_excel(cls, file_path):
        """Reads Excel file using pandas/openpyxl and inserts into database."""
        df = pd.read_excel(file_path)
        df.columns = [c.strip().lower().replace(" ", "_").replace("(%)", "").replace("_%", "") for c in df.columns]
        
        success_count = 0
        error_list = []
        
        for idx, row in df.iterrows():
            try:
                name = str(row.get('name', ''))
                product_id = str(row.get('product_id', ''))
                if not name or name == 'nan' or not product_id or product_id == 'nan':
                    raise ValueError("Product Name and Product ID are required fields.")
                
                purchase_price = float(row.get('purchase_price', 0.0))
                mrp = float(row.get('mrp', 0.0))
                selling_price = float(row.get('selling_price', 0.0))
                gst = float(row.get('gst', 0.0))
                discount = float(row.get('discount', 0.0))
                quantity = float(row.get('quantity', 0.0))
                
                barcode = str(row.get('barcode', '')) if pd.notna(row.get('barcode')) and str(row.get('barcode')) != 'nan' else None
                qrcode = str(row.get('qrcode', '')) if pd.notna(row.get('qrcode')) and str(row.get('qrcode')) != 'nan' else None
                category = str(row.get('category', '')) if pd.notna(row.get('category')) and str(row.get('category')) != 'nan' else None
                brand = str(row.get('brand', '')) if pd.notna(row.get('brand')) and str(row.get('brand')) != 'nan' else None
                unit = str(row.get('unit', 'pcs')) if pd.notna(row.get('unit')) and str(row.get('unit')) != 'nan' else 'pcs'
                weight = float(row.get('weight')) if pd.notna(row.get('weight')) else None
                
                expiry_date = str(row.get('expiry_date'))[:10] if pd.notna(row.get('expiry_date')) else None
                mfg_date = str(row.get('mfg_date'))[:10] if pd.notna(row.get('mfg_date')) else None
                description = str(row.get('description', '')) if pd.notna(row.get('description')) else ''
                
                supplier_id = int(row.get('supplier_id')) if pd.notna(row.get('supplier_id')) else None
                
                payload = {
                    'name': name,
                    'product_id': product_id,
                    'barcode': barcode,
                    'qrcode': qrcode,
                    'category': category,
                    'brand': brand,
                    'supplier_id': supplier_id,
                    'purchase_price': purchase_price,
                    'mrp': mrp,
                    'selling_price': selling_price,
                    'gst': gst,
                    'discount': discount,
                    'quantity': quantity,
                    'unit': unit,
                    'weight': weight,
                    'expiry_date': expiry_date,
                    'mfg_date': mfg_date,
                    'description': description,
                    'image_path': None
                }
                
                cls.create(**payload)
                success_count += 1
            except Exception as e:
                error_list.append(f"Row {idx + 2}: {str(e)}")
                
        if error_list:
            raise ValueError("Import errors encountered: " + "; ".join(error_list))
            
        return success_count

    @classmethod
    def export_to_excel(cls, dest_file_path):
        """Export all products in database to Excel sheet."""
        rows = query_db("SELECT * FROM products")
        df = pd.DataFrame(rows)
        
        if not df.empty:
            df.rename(columns={
                'name': 'Name',
                'product_id': 'Product ID',
                'barcode': 'Barcode',
                'qrcode': 'QR Code',
                'category': 'Category',
                'brand': 'Brand',
                'supplier_id': 'Supplier ID',
                'purchase_price': 'Purchase Price',
                'mrp': 'MRP',
                'selling_price': 'Selling Price',
                'gst': 'GST (%)',
                'discount': 'Discount (%)',
                'quantity': 'Quantity',
                'unit': 'Unit',
                'weight': 'Weight',
                'expiry_date': 'Expiry Date',
                'mfg_date': 'Mfg Date',
                'description': 'Description',
                'image_path': 'Image Path',
                'created_at': 'Created At',
                'updated_at': 'Updated At',
                'stock_status': 'Stock Status'
            }, inplace=True)
        
        os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
        df.to_excel(dest_file_path, index=False)
        return dest_file_path
