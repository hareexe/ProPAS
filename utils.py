import os, io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER

def add_signature_page(upload_folder, file_path, role_key, officer_name):
    """
    Handles the coordinate-heavy logic of drawing the NWU signature page.
    """
    try:
        full_path = os.path.join(upload_folder, file_path)
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=LETTER)
   
        roles_config = {
            "CAS": {"x": 70, "y": 680, "label": "Dean of Students Affairs"},
            "OSA": {"x": 350, "y": 750, "label": "RECOMMENDING APPROVAL:", "is_header": True},
            "VPAA": {"x": 350, "y": 600, "label": "Vice President For Academic Affairs"},
            "FINANCE": {"x": 70, "y": 500, "label": "Vice President for Finance", "extra": "Itemized Budget Reviewed by:"},
            "VICEPRESIDENT": {"x": 350, "y": 450, "label": "Executive Vice President", "header": "APPROVED:"},
            "PRESIDENT": {"x": 350, "y": 300, "label": "President"}
        }

        for key, cfg in roles_config.items():
            x, y = cfg["x"], cfg["y"]
            
            if "header" in cfg:
                can.setFont("Helvetica-Bold", 11)
                can.drawString(x, y + 60, cfg["header"])
            elif cfg.get("is_header"):
                can.setFont("Helvetica-Bold", 11)
                can.drawString(x, y + 30, cfg["label"])
                continue 

            if "extra" in cfg:
                can.setFont("Helvetica-Bold", 10)
                can.drawString(x, y + 60, cfg["extra"])

            can.setLineWidth(1)
            can.line(x, y + 15, x + 220, y + 15)

            if key == role_key:
                can.setFont("Helvetica-Bold", 12)
                can.drawCentredString(x + 110, y + 20, officer_name.upper())

            can.setFont("Helvetica-BoldOblique", 10)
            can.drawCentredString(x + 110, y + 2, cfg["label"])

        can.save()
        packet.seek(0)

        new_pdf = PdfReader(packet)
        existing_pdf = PdfReader(open(full_path, "rb"))
        output = PdfWriter()

        for page in existing_pdf.pages:
            output.add_page(page)
        output.add_page(new_pdf.pages[0])

        with open(full_path, "wb") as f:
            output.write(f)
        return True
    except Exception as e:
        print(f"PDF Error: {e}")
        return False