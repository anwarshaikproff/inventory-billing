import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INVOICE_DIR = os.path.join(BASE_DIR, 'static', 'invoice')
os.makedirs(INVOICE_DIR, exist_ok=True)

def generate_invoice_pdf(invoice_details, dest_path=None):
    """
    Renders a professional PDF invoice using ReportLab.
    invoice_details should contain keys: 'sale', 'items', 'cashier', 'customer', 'store'
    """
    sale = invoice_details['sale']
    items = invoice_details['items']
    cashier = invoice_details.get('cashier', 'Unknown')
    customer = invoice_details.get('customer')
    store = invoice_details.get('store', {
        'name': 'SKML Mobiles',
        'address': '101, Business Hub, Sector 5, Tech City',
        'phone': '+91 9876543210',
        'email': 'billing@techmart.com',
        'gst': '27AAPCS1234F1Z5',
        'footer': 'Thank you for shopping with us!'
    })

    if not dest_path:
        dest_path = os.path.join(INVOICE_DIR, f"{sale['invoice_number']}.pdf")

    # Document Setup
    # A standard retail print layout
    doc = SimpleDocTemplate(
        dest_path,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'StoreTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#2C3E50"),
        alignment=0
    )
    store_meta_style = ParagraphStyle(
        'StoreMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#7F8C8D")
    )
    inv_title_style = ParagraphStyle(
        'InvTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        textColor=colors.HexColor("#2C3E50"),
        alignment=2 # Right
    )
    inv_meta_style = ParagraphStyle(
        'InvMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        alignment=2 # Right
    )
    section_title = ParagraphStyle(
        'SecTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#34495E")
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#2C3E50")
    )
    totals_label_style = ParagraphStyle(
        'TotalsLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        alignment=2 # Right
    )
    totals_val_style = ParagraphStyle(
        'TotalsValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=12,
        alignment=2 # Right
    )
    footer_style = ParagraphStyle(
        'InvFooter',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        alignment=1, # Center
        textColor=colors.HexColor("#95A5A6")
    )

    story = []

    # 1. Header (Store details on Left, Invoice details on Right)
    store_info = [
        Paragraph(store['name'], title_style),
        Paragraph(f"{store['address']}", store_meta_style),
        Paragraph(f"Phone: {store['phone']} | Email: {store['email']}", store_meta_style),
        Paragraph(f"GSTIN: {store['gst']}", store_meta_style),
    ]

    inv_info = [
        Paragraph("RETAIL INVOICE", inv_title_style),
        Spacer(1, 4),
        Paragraph(f"<b>Invoice No:</b> {sale['invoice_number']}", inv_meta_style),
        Paragraph(f"<b>Date:</b> {sale['date']}", inv_meta_style),
        Paragraph(f"<b>Cashier:</b> {cashier}", inv_meta_style),
        Paragraph(f"<b>Payment Mode:</b> {sale['payment_mode']}", inv_meta_style),
    ]

    header_table = Table([[store_info, inv_info]], colWidths=[4.0*inch, 3.5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # 2. Customer details section
    cust_details = []
    if customer:
        cust_details = [
            Paragraph("<b>Billed To (Customer):</b>", section_title),
            Paragraph(f"Name: {customer['name']}", store_meta_style),
            Paragraph(f"Phone: {customer['phone']}", store_meta_style),
            Paragraph(f"Email: {customer.get('email') or 'N/A'} | Address: {customer.get('address') or 'N/A'}", store_meta_style),
            Paragraph(f"Reward Points: {customer.get('reward_points', 0)}", store_meta_style),
        ]
    else:
        cust_details = [
            Paragraph("<b>Billed To (Customer):</b>", section_title),
            Paragraph("Walk-in Customer", store_meta_style)
        ]
        
    cust_table = Table([[cust_details]], colWidths=[7.5*inch])
    cust_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8F9F9")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#BDC3C7")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(cust_table)
    story.append(Spacer(1, 15))

    # 3. Billing Line Items Table
    # Headers
    table_data = [[
        Paragraph("S.No", table_header_style),
        Paragraph("Item Description", table_header_style),
        Paragraph("Qty", table_header_style),
        Paragraph("MRP", table_header_style),
        Paragraph("Selling Price", table_header_style),
        Paragraph("CGST %", table_header_style),
        Paragraph("CGST Amt", table_header_style),
        Paragraph("SGST %", table_header_style),
        Paragraph("SGST Amt", table_header_style),
        Paragraph("Disc Amt", table_header_style),
        Paragraph("Subtotal", table_header_style)
    ]]

    # Items rows
    for idx, item in enumerate(items, 1):
        cgst_rate = float(item.get('gst_rate', 0.0)) / 2.0
        cgst_amt = float(item.get('gst', 0.0)) / 2.0
        table_data.append([
            Paragraph(str(idx), table_cell_style),
            Paragraph(f"{item['product_name']}", table_cell_style),
            Paragraph(f"{item['quantity']} {item.get('unit', 'pcs')}", table_cell_style),
            Paragraph(f"{item['mrp']:.2f}", table_cell_style),
            Paragraph(f"{item['selling_price']:.2f}", table_cell_style),
            Paragraph(f"{cgst_rate:.1f}%", table_cell_style),
            Paragraph(f"{cgst_amt:.2f}", table_cell_style),
            Paragraph(f"{cgst_rate:.1f}%", table_cell_style),
            Paragraph(f"{cgst_amt:.2f}", table_cell_style),
            Paragraph(f"{item['discount']:.2f}", table_cell_style),
            Paragraph(f"{item['subtotal']:.2f}", table_cell_style),
        ])

    items_table = Table(table_data, colWidths=[0.4*inch, 1.8*inch, 0.5*inch, 0.6*inch, 0.6*inch, 0.5*inch, 0.6*inch, 0.5*inch, 0.6*inch, 0.6*inch, 0.8*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BDC3C7")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9EBEA")]), # Alternating white/very light red
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # 4. Totals Calculation Box (Subtotal, Discount, CGST, SGST, Grand Total, Cash Received, Balance)
    half_gst = float(sale.get('gst', 0.0)) / 2.0
    totals_data = [
        [Paragraph("Subtotal:", totals_label_style), Paragraph(f"INR {sale['subtotal']:.2f}", totals_val_style)],
        [Paragraph("Discounts:", totals_label_style), Paragraph(f"- INR {sale['discount']:.2f}", totals_val_style)],
        [Paragraph("CGST:", totals_label_style), Paragraph(f"+ INR {half_gst:.2f}", totals_val_style)],
        [Paragraph("SGST:", totals_label_style), Paragraph(f"+ INR {half_gst:.2f}", totals_val_style)],
        [Paragraph("Grand Total:", ParagraphStyle('GrandLabel', parent=totals_label_style, fontSize=11, textColor=colors.HexColor("#E74C3C"))), 
         Paragraph(f"<b>INR {sale['grand_total']:.2f}</b>", ParagraphStyle('GrandVal', parent=totals_val_style, fontSize=11, textColor=colors.HexColor("#E74C3C")))],
    ]

    if sale['payment_mode'] == 'Cash':
        totals_data.append([Paragraph("Cash Received:", totals_label_style), Paragraph(f"INR {sale['cash_received']:.2f}", totals_val_style)])
        totals_data.append([Paragraph("Balance Returned:", totals_label_style), Paragraph(f"INR {sale['balance']:.2f}", totals_val_style)])

    totals_table = Table(totals_data, colWidths=[5.5*inch, 2.0*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    
    # 5. Signatory and Stamp Block
    sig_data = [
        [
            Paragraph("<font color='#7F8C8D'>Store Seal / Stamp</font>", ParagraphStyle('SealText', fontName='Helvetica-Oblique', fontSize=8.5, alignment=1)),
            Paragraph("<font color='#2C3E50'>For <b>" + store['name'] + "</b><br/><br/><br/><br/>Authorized Signatory</font>", ParagraphStyle('SigText', fontName='Helvetica', fontSize=9, leading=12, alignment=2))
        ]
    ]
    sig_table = Table(sig_data, colWidths=[2.0*inch, 5.5*inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        # Create a dashed border for the stamp box
        ('BOX', (0,0), (0,0), 1, colors.HexColor("#BDC3C7")),
        ('TOPPADDING', (0,0), (0,0), 30), # space inside the stamp box
        ('BOTTOMPADDING', (0,0), (0,0), 30),
    ]))

    # Wrap in KeepTogether to ensure it doesn't break across pages awkwardly
    footer_elements = [
        totals_table,
        Spacer(1, 25),
        sig_table,
        Spacer(1, 20),
        Paragraph(store['footer'], footer_style)
    ]
    story.append(KeepTogether(footer_elements))

    doc.build(story)
    return dest_path
