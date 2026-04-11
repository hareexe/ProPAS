import os, io
import calendar
from datetime import datetime
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
            "CAS": {"x": 60, "y": 690, "label": "CAS Dean", "header": "Received and Noted by:"},
            "OSA": {"x": 360, "y": 690, "label": "Dean of OSA", "header": "Recommending Approval:"},
            "FINANCE": {"x": 60, "y": 445, "label": "Vice President of Finance", "header": "Itemized Budget Reviewed by:"},
            "VPAA": {"x": 360, "y": 445, "label": "Vice President for Academic Affairs"},
            "VICEPRESIDENT": {"x": 60, "y": 200, "label": "Executive Vice President", "header": "Approved:"},
            "PRESIDENT": {"x": 360, "y": 200, "label": "President"}
        }

        for key, cfg in roles_config.items():
            x, y = cfg["x"], cfg["y"]
            
            if "header" in cfg:
                can.setFont("Helvetica-Bold", 11)
                can.drawString(x, y + 60, cfg["header"])

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


def parse_event_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day'):
        return value

    raw = str(value).strip()
    if not raw:
        return None

    for fmt in ('%Y-%m-%d', '%B %d, %Y', '%b %d, %Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def get_proposal_venue(proposal_data):
    proposal_data = proposal_data or {}
    venue = (proposal_data.get('venue') or '').strip()
    venue_other = (proposal_data.get('venue_other') or '').strip()
    if venue == 'Others':
        return venue_other or 'Other venue'
    return venue or venue_other or 'Venue not specified'


def build_month_matrix(year, month):
    return calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
