import os, io
import calendar
import json
from datetime import datetime
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

SIGNATURE_PAGE_MARKERS = (
    "noted:",
    "recommending approval:",
    "itemized budget reviewed by:",
    "approved:",
)

ORG_SIGNATURES = (
    {"key": "signatory_ProjPresident", "name_y": 258, "label_y": 252, "label": "President/Project Coordinator"},
    {"key": "signatory_adviser", "name_y": 233, "label_y": 227, "label": "Person In-Charge/Adviser"},
    {"key": "signatory_dept_head", "name_y": 208, "label_y": 202, "label": "Department / Program Head"},
    {"role": "CAS", "name_y": 183, "label_y": 177, "label": "Dean, College of Arts and Sciences", "draw_blank_line": True},
)

OFFICE_SIGNATURES = (
    {"role": "OSA", "x": 18, "line_y": 150, "label": "Dean, Office of Student Affairs", "header": "Noted:"},
    {"role": "VPAA", "x": 122, "line_y": 150, "label": "Vice President, Academic Affairs", "header": "RECOMMENDING APPROVAL:"},
    {"role": "FINANCE", "x": 18, "line_y": 100, "label": "Vice President for Finance", "header": "Itemized Budget Reviewed by:"},
    {"role": "VICEPRESIDENT", "x": 122, "line_y": 100, "label": "Executive Vice-President", "header": "APPROVED:"},
    {"role": "PRESIDENT", "x": 122, "line_y": 52, "label": "President"},
)

SIGNATURE_LINE_WIDTH_MM = 70
SIGNATURE_PAGE_FOOTER = (
    "Issue Status: 4",
    "Revision: 2",
    "Date: 15 April 2025",
    "Approved by: President",
)


def _clean_signature_text(value):
    return " ".join(str(value or "").split()).strip()


def _draw_org_signature(can, x_center_mm, name_y_mm, label_y_mm, name, label, draw_blank_line=False):
    safe_name = _clean_signature_text(name)
    if safe_name:
        can.setFont("Helvetica-Bold", 10)
        can.drawCentredString(x_center_mm * mm, name_y_mm * mm, safe_name.upper())

    if safe_name or draw_blank_line:
        line_half_width = 28 * mm
        line_y = (name_y_mm - 2) * mm
        can.line((x_center_mm * mm) - line_half_width, line_y, (x_center_mm * mm) + line_half_width, line_y)

    can.setFont("Helvetica", 8)
    can.drawCentredString(x_center_mm * mm, label_y_mm * mm, label)


def _draw_office_signature(can, slot, signed_roles):
    x = slot["x"] * mm
    line_y = slot["line_y"] * mm
    line_width = SIGNATURE_LINE_WIDTH_MM * mm
    header = slot.get("header")
    signed_name = _clean_signature_text(signed_roles.get(slot["role"]))

    if header:
        can.setFont("Helvetica-Bold", 10)
        can.drawString(x, line_y + (14 * mm), header)

    if signed_name:
        can.setFont("Helvetica-Bold", 10)
        can.drawCentredString(x + (line_width / 2), line_y + (2.5 * mm), signed_name.upper())

    can.setLineWidth(1)
    can.line(x, line_y, x + line_width, line_y)

    can.setFont("Helvetica", 8)
    can.drawCentredString(x + (line_width / 2), line_y - (5 * mm), slot["label"])


def _draw_signature_footer(can, page_width, footer_items):
    footer_x = 18 * mm
    footer_y = 15 * mm
    footer_height = 8.5 * mm
    footer_width = page_width - (36 * mm)
    cell_width = footer_width / max(len(footer_items), 1)

    can.rect(footer_x, footer_y, footer_width, footer_height)

    for index in range(1, len(footer_items)):
        x = footer_x + (cell_width * index)
        can.line(x, footer_y, x, footer_y + footer_height)

    can.setFont("Helvetica", 6.8)
    text_y = footer_y + (footer_height / 2) - 2
    for index, item in enumerate(footer_items):
        text_x = footer_x + (cell_width * index) + (cell_width / 2)
        can.drawCentredString(text_x, text_y, item)


def _build_signature_page(proposal_data, signed_roles):
    packet = io.BytesIO()
    page_width, _ = A4
    can = canvas.Canvas(packet, pagesize=A4)

    proposal_data = normalize_proposal_data(proposal_data)

    for org_signature in ORG_SIGNATURES:
        if "key" in org_signature:
            signature_name = proposal_data.get(org_signature["key"], "")
        else:
            signature_name = signed_roles.get(org_signature["role"], "")

        _draw_org_signature(
            can,
            x_center_mm=157,
            name_y_mm=org_signature["name_y"],
            label_y_mm=org_signature["label_y"],
            name=signature_name,
            label=org_signature["label"],
            draw_blank_line=org_signature.get("draw_blank_line", False),
        )

    for office_signature in OFFICE_SIGNATURES:
        _draw_office_signature(can, office_signature, signed_roles)

    _draw_signature_footer(can, page_width, SIGNATURE_PAGE_FOOTER)

    can.save()
    packet.seek(0)
    return PdfReader(packet)


def _is_signature_page(page):
    page_text = " ".join((page.extract_text() or "").lower().split())
    if not page_text:
        return False
    return all(marker in page_text for marker in SIGNATURE_PAGE_MARKERS)


def add_signature_page_bytes(pdf_bytes, signed_roles, proposal_data=None):
    try:
        if not pdf_bytes:
            print("PDF Error: missing PDF bytes")
            return None

        signature_page_pdf = _build_signature_page(proposal_data or {}, signed_roles)
        output = PdfWriter()
        existing_pdf = PdfReader(io.BytesIO(pdf_bytes))
        existing_pages = list(existing_pdf.pages)

        if existing_pages and _is_signature_page(existing_pages[-1]):
            existing_pages = existing_pages[:-1]

        for page in existing_pages:
            output.add_page(page)

        output.add_page(signature_page_pdf.pages[0])

        merged = io.BytesIO()
        output.write(merged)
        return merged.getvalue()
    except Exception as e:
        print(f"PDF Error: {e}")
        return None


def add_signature_page(upload_folder, file_path, signed_roles, proposal_data=None):
    """
    Backward-compatible local-disk wrapper around add_signature_page_bytes().
    """
    try:
        if not file_path:
            print("PDF Error: missing proposal file path")
            return False

        full_path = file_path if os.path.isabs(file_path) else os.path.join(upload_folder, file_path)
        if not os.path.exists(full_path):
            print(f"PDF Error: file not found at {full_path}")
            return False

        with open(full_path, "rb") as existing_file:
            merged_bytes = add_signature_page_bytes(existing_file.read(), signed_roles, proposal_data=proposal_data)

        if not merged_bytes:
            return False

        with open(full_path, "wb") as target_file:
            target_file.write(merged_bytes)
        return True
    except Exception as e:
        print(f"PDF Error: {e}")
        return False


def _paragraph_text(value, fallback='N/A'):
    text = str(value or '').strip()
    return text or fallback


def _bullet_lines(value):
    lines = [line.strip() for line in str(value or '').splitlines() if line.strip()]
    return lines or ['N/A']


def _proposal_logo_path():
    return os.path.join(os.path.dirname(__file__), 'static', 'images', 'NWUlogo.jpg')


def _draw_generated_pdf_chrome(can, doc):
    page_width, page_height = A4
    can.saveState()

    logo_path = _proposal_logo_path()
    if os.path.exists(logo_path):
        logo_width = 18 * mm
        logo_height = 18 * mm
        logo_x = (page_width - logo_width) / 2
        logo_y = page_height - (21 * mm)
        can.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    can.setLineWidth(1.2)
    can.line(18 * mm, page_height - (24 * mm), page_width - (18 * mm), page_height - (24 * mm))

    _draw_signature_footer(can, page_width, SIGNATURE_PAGE_FOOTER)
    can.restoreState()


def build_proposal_pdf_bytes(proposal_data, signed_roles=None, title=None):
    proposal_data = normalize_proposal_data(proposal_data)
    signed_roles = signed_roles or {}
    needs_budget = proposal_needs_budget(proposal_data)

    packet = io.BytesIO()
    doc = SimpleDocTemplate(
        packet,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=30 * mm,
        bottomMargin=28 * mm,
    )

    styles = getSampleStyleSheet()
    body = styles['BodyText']
    body.fontName = 'Helvetica'
    body.fontSize = 10
    body.leading = 13
    body.spaceAfter = 6

    label = ParagraphStyle(
        'ProposalLabel',
        parent=body,
        fontName='Helvetica-Bold',
        spaceAfter=3,
    )

    section_title = ParagraphStyle(
        'ProposalSectionTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        spaceAfter=6,
        textColor=colors.black,
    )

    centered = ParagraphStyle(
        'CenteredTitle',
        parent=styles['Title'],
        alignment=1,
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=17,
        textColor=colors.black,
        spaceAfter=4,
    )

    small_center = ParagraphStyle(
        'SmallCenter',
        parent=body,
        alignment=1,
        fontSize=9,
        leading=11,
        spaceAfter=2,
    )

    story = [
        Spacer(1, 10),
        Paragraph('NORTHWESTERN UNIVERSITY', centered),
        Paragraph('Don Mariano Marcos Avenue, Laoag City, 2900, Ilocos Norte, Philippines', small_center),
        Spacer(1, 6),
        Table(
            [['PROJECT PROPOSAL', 'OSA-F05A']],
            colWidths=[145 * mm, 25 * mm],
            style=TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]),
        ),
        Spacer(1, 12),
    ]

    proposal_title = title or proposal_data.get('title')
    sections = [
        ('I. Project Proposal Title', _paragraph_text(proposal_title)),
        ('II. Sponsor / Organization', _paragraph_text(proposal_data.get('sponsor'))),
        ('III. Date & Venue', f"Date: {_paragraph_text(proposal_data.get('event_date'))}<br/>Venue: {_paragraph_text(get_proposal_venue(proposal_data))}"),
        ('IV. Target Participants', _paragraph_text(proposal_data.get('participation'))),
        ('V. Background / Rationale', _paragraph_text(proposal_data.get('rationale'))),
    ]

    for heading, content in sections:
        story.append(Paragraph(heading, section_title))
        story.append(Paragraph(content.replace('\n', '<br/>'), body))
        story.append(Spacer(1, 4))

    story.append(Paragraph('VI. Objectives', section_title))
    for idx, line in enumerate(_bullet_lines(proposal_data.get('objectives_list')), start=1):
        story.append(Paragraph(f'{idx}. {line}', body))
    story.append(Spacer(1, 4))

    unsdgs = proposal_data.get('unsdg_goals') or []
    if isinstance(unsdgs, str):
        unsdgs = [item.strip() for item in unsdgs.split(',') if item.strip()]
    story.append(Paragraph('VII. UNSDGs', section_title))
    story.append(Paragraph(_paragraph_text(', '.join(unsdgs)), body))
    story.append(Spacer(1, 4))

    story.append(Paragraph('VIII. Approach / Process', section_title))
    approach_items = proposal_data.get('approach_items') or []
    if approach_items:
        approach_rows = [['Time', 'Activity', 'Description / Remarks']]
        for item in approach_items:
            approach_rows.append([
                _paragraph_text(item.get('time') or ''),
                _paragraph_text(item.get('activity')),
                _paragraph_text(item.get('remarks')),
            ])
        story.append(Table(
            approach_rows,
            colWidths=[35 * mm, 55 * mm, 80 * mm],
            style=TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.8, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('LEADING', (0, 0), (-1, -1), 11),
            ]),
        ))
    else:
        story.append(Paragraph('N/A', body))
    story.append(Spacer(1, 8))

    story.append(Paragraph('IX. Expected Outcomes', section_title))
    story.append(Paragraph(_paragraph_text(proposal_data.get('expected_outcome')).replace('\n', '<br/>'), body))
    story.append(Spacer(1, 4))

    if needs_budget:
        story.append(Paragraph('X. Budget', section_title))
        budget_items = proposal_data.get('budget_items') or []
        story.append(Paragraph(f"Proposed Budget: PHP {float(proposal_data.get('budget') or 0):,.2f}", body))
        if budget_items:
            budget_rows = [['#', 'Item', 'Qty', 'Unit Price', 'Amount']]
            grand_total = 0.0
            for idx, item in enumerate(budget_items, start=1):
                qty = float(item.get('quantity') or 0)
                unit = float(item.get('unit_cost') or 0)
                amount = float(item.get('amount') or (qty * unit))
                grand_total += amount
                budget_rows.append([str(idx), _paragraph_text(item.get('description')), f'{qty:g}', f'PHP {unit:,.2f}', f'PHP {amount:,.2f}'])
            budget_rows.append(['', '', '', 'TOTAL', f'PHP {grand_total:,.2f}'])
            story.append(Table(
                budget_rows,
                colWidths=[12 * mm, 82 * mm, 18 * mm, 28 * mm, 30 * mm],
                style=TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.8, colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                    ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('LEADING', (0, 0), (-1, -1), 11),
                ]),
            ))
        else:
            story.append(Paragraph('No budget breakdown provided.', body))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"Source of Funding: {_paragraph_text(proposal_data.get('funding_source'))}", body))

    doc.build(story, onFirstPage=_draw_generated_pdf_chrome, onLaterPages=_draw_generated_pdf_chrome)
    body_bytes = packet.getvalue()
    return add_signature_page_bytes(body_bytes, signed_roles, proposal_data=proposal_data) or body_bytes


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


def proposal_needs_budget(proposal_data):
    proposal_data = normalize_proposal_data(proposal_data)
    raw_value = proposal_data.get('needs_budget', 'yes')
    if isinstance(raw_value, bool):
        return raw_value
    return str(raw_value or 'yes').strip().lower() not in {'no', 'false', '0'}


def get_proposal_venue(proposal_data):
    proposal_data = normalize_proposal_data(proposal_data)
    venue = (proposal_data.get('venue') or '').strip()
    venue_other = (proposal_data.get('venue_other') or '').strip()
    if venue == 'Others':
        return venue_other or 'Other venue'
    return venue or venue_other or 'Venue not specified'


def build_month_matrix(year, month):
    return calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
