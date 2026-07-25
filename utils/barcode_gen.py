import os
import barcode
from barcode.writer import ImageWriter
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Static paths for saving images
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BARCODE_DIR = os.path.join(BASE_DIR, 'static', 'barcode')
QRCODE_DIR = os.path.join(BASE_DIR, 'static', 'qrcode')

os.makedirs(BARCODE_DIR, exist_ok=True)
os.makedirs(QRCODE_DIR, exist_ok=True)

def generate_barcode(data, format_type='Code128'):
    """
    Generates a barcode image and returns the relative file path.
    Supported types: Code128, EAN13
    """
    try:
        if format_type == 'EAN13':
            # EAN13 requires exactly 12 digits. If not, fallback to Code128.
            clean_data = ''.join(c for c in data if c.isdigit())
            if len(clean_data) < 12:
                # Pad with leading zeros
                clean_data = clean_data.zfill(12)
            elif len(clean_data) > 12:
                clean_data = clean_data[:12]
            
            bar_class = barcode.get_barcode_class('ean13')
            bar = bar_class(clean_data, writer=ImageWriter())
        else:
            bar_class = barcode.get_barcode_class('code128')
            bar = bar_class(data, writer=ImageWriter())
            
        file_path = os.path.join(BARCODE_DIR, f"{data}")
        # write returns file_path + '.png'
        actual_path = bar.save(file_path)
        return f"static/barcode/{os.path.basename(actual_path)}"
    except Exception as e:
        print(f"Barcode Generation Error for {data}: {e}")
        # Try Code128 fallback
        if format_type == 'EAN13':
            return generate_barcode(data, 'Code128')
        return None

def generate_qrcode(data):
    """
    Generates a QR Code image and returns the relative file path.
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        file_path = os.path.join(QRCODE_DIR, f"{data}.png")
        img.save(file_path)
        return f"static/qrcode/{data}.png"
    except Exception as e:
        print(f"QR Code Generation Error for {data}: {e}")
        return None

def build_barcode_pdf_sheet(product, label_count=24, dest_filepath="barcode_sheet.pdf"):
    """
    Generates a printable A4 PDF sheet containing a grid of barcode stickers.
    Each sticker contains: Product Name, Weight, Category, Barcode image, MRP, Price.
    A4 page typically holds 24 stickers (3 columns x 8 rows).
    """
    doc = SimpleDocTemplate(
        dest_filepath, 
        pagesize=A4,
        rightMargin=0.25*inch, 
        leftMargin=0.25*inch,
        topMargin=0.4*inch, 
        bottomMargin=0.4*inch
    )
    
    # 1. Generate code barcode image
    bc_path_rel = generate_barcode(product.barcode or product.product_id, 'Code128')
    bc_full_path = os.path.join(BASE_DIR, bc_path_rel)
    
    # Setup styling
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle(
        'StickerName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=9,
        alignment=1 # Center
    )
    detail_style = ParagraphStyle(
        'StickerDetails',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.5,
        leading=8,
        alignment=1 # Center
    )
    price_style = ParagraphStyle(
        'StickerPrice',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        alignment=1 # Center
    )

    story = []
    
    # Generate single sticker cell content
    def create_sticker_cell():
        img = Image(bc_full_path, width=1.8*inch, height=0.6*inch)
        cell_elements = [
            Paragraph(f"<b>{product.name}</b>", name_style),
            Spacer(1, 2),
            Paragraph(f"Cat: {product.category or 'General'} | Wt: {product.weight or 0} {product.unit}", detail_style),
            Spacer(1, 2),
            img,
            Spacer(1, 2),
            Paragraph(f"MRP: INR {product.mrp:.2f} | <b>Price: INR {product.selling_price:.2f}</b>", price_style)
        ]
        
        # Wrap elements in a single table cell container
        cell_table = Table([[cell_elements]], colWidths=[2.2*inch], rowHeights=[1.15*inch])
        cell_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOX', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        return cell_table

    # Build Grid
    grid_data = []
    current_row = []
    cols = 3 # 3 stickers per row
    
    for i in range(label_count):
        current_row.append(create_sticker_cell())
        if len(current_row) == cols:
            grid_data.append(current_row)
            current_row = []
            
    if current_row:
        # Pad remaining columns
        while len(current_row) < cols:
            current_row.append("")
        grid_data.append(current_row)

    # Compile the final layout table
    outer_table = Table(grid_data, colWidths=[2.4*inch]*cols)
    outer_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    
    story.append(outer_table)
    doc.build(story)
    return dest_filepath
