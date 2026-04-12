import os, io
import calendar
import json
from datetime import datetime
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER

SIGNATURE_PAGE_HEADERS = (
    "Received and Noted by:",
    "Recommending Approval:",
    "Itemized Budget Reviewed by:",
    "Approved:",
)

SIGNATURE_ROLES = {
    "CAS": {"x": 60, "y": 690, "label": "CAS Dean", "header": "Received and Noted by:"},
    "OSA": {"x": 360, "y": 690, "label": "Dean of OSA", "header": "Recommending Approval:"},
    "FINANCE": {"x": 60, "y": 445, "label": "Vice President of Finance", "header": "Itemized Budget Reviewed by:"},
    "VPAA": {"x": 360, "y": 445, "label": "Vice President for Academic Affairs"},
    "VICEPRESIDENT": {"x": 60, "y": 200, "label": "Executive Vice President", "header": "Approved:"},
    "PRESIDENT": {"x": 360, "y": 200, "label": "President"},
}


def _build_signature_overlay(signed_roles):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=LETTER)

    for key, cfg in SIGNATURE_ROLES.items():
        x, y = cfg["x"], cfg["y"]

        if "header" in cfg:
            can.setFont("Helvetica-Bold", 11)
            can.drawString(x, y + 60, cfg["header"])

        can.setLineWidth(1)
        can.line(x, y + 15, x + 220, y + 15)

        officer_name = (signed_roles.get(key) or "").strip()
        if officer_name:
            can.setFont("Helvetica-Bold", 12)
            can.drawCentredString(x + 110, y + 20, officer_name.upper())

        can.setFont("Helvetica-BoldOblique", 10)
        can.drawCentredString(x + 110, y + 2, cfg["label"])

    can.save()
    packet.seek(0)
    return PdfReader(packet)


def _is_signature_page(page):
    page_text = (page.extract_text() or "").strip()
    if not page_text:
        return False
    return all(header in page_text for header in SIGNATURE_PAGE_HEADERS)


def add_signature_page(upload_folder, file_path, signed_roles):
    """
    Rebuilds the shared signature page so approved signatories remain visible.
    """
    try:
        full_path = os.path.join(upload_folder, file_path)
        overlay_pdf = _build_signature_overlay(signed_roles)
        output = PdfWriter()

        with open(full_path, "rb") as existing_file:
            existing_pdf = PdfReader(existing_file)
            existing_pages = list(existing_pdf.pages)

            if existing_pages and _is_signature_page(existing_pages[-1]):
                existing_pages = existing_pages[:-1]

            for page in existing_pages:
                output.add_page(page)

            output.add_page(overlay_pdf.pages[0])

        with open(full_path, "wb") as target_file:
            output.write(target_file)
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


def normalize_proposal_data(proposal_data):
    if isinstance(proposal_data, dict):
        return proposal_data

    if isinstance(proposal_data, str):
        raw = proposal_data.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    return dict(proposal_data or {})


def get_proposal_venue(proposal_data):
    proposal_data = normalize_proposal_data(proposal_data)
    venue = (proposal_data.get('venue') or '').strip()
    venue_other = (proposal_data.get('venue_other') or '').strip()
    if venue == 'Others':
        return venue_other or 'Other venue'
    return venue or venue_other or 'Venue not specified'


def build_month_matrix(year, month):
    return calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
