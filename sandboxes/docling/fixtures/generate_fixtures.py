"""
Generates synthetic, non-sensitive fixture files used to benchmark Docling.

No real case files, personal data, or legal documents are used anywhere in this
sandbox. Every fixture below is invented text for testing purposes only.
"""
from __future__ import annotations

import pathlib

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from docx import Document as DocxDocument
from openpyxl import Workbook
from pptx import Presentation
from pptx.util import Inches
import arabic_reshaper
from bidi.algorithm import get_display

FIXTURES_DIR = pathlib.Path(__file__).parent


def make_plain_text_pdf() -> None:
    path = FIXTURES_DIR / "sample_plain_text.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica", 12)
    lines = [
        "SYNTHETIC TEST DOCUMENT - NOT A REAL CASE FILE",
        "",
        "Title: Sample Agreement Memo (Fictional)",
        "",
        "Section 1: Purpose",
        "This is a synthetic memo created only to benchmark document parsing.",
        "It contains invented parties, invented dates, and invented clauses.",
        "",
        "Section 2: Fictional Parties",
        "Party A: Acme Testing Corp (fictional)",
        "Party B: Example Holdings Ltd (fictional)",
        "",
        "Section 3: Fictional Terms",
        "1. This fixture exists only to validate text extraction order.",
        "2. Numbers should remain in order: 1, 2, 3, 4, 5.",
        "3. End of fictional terms.",
    ]
    y = 800
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
    c.showPage()
    c.save()


def make_table_pdf() -> None:
    path = FIXTURES_DIR / "sample_with_tables.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("SYNTHETIC TEST DOCUMENT WITH TABLE - NOT A REAL CASE FILE", styles["Title"]),
        Paragraph("Fictional exhibit list for benchmarking table extraction.", styles["Normal"]),
    ]
    data = [
        ["Exhibit #", "Description (fictional)", "Date (fictional)", "Status"],
        ["EX-001", "Sample fictional contract", "2024-01-10", "Accepted"],
        ["EX-002", "Sample fictional invoice", "2024-02-15", "Pending"],
        ["EX-003", "Sample fictional letter", "2024-03-02", "Rejected"],
        ["EX-004", "Sample fictional report", "2024-04-21", "Accepted"],
    ]
    table = Table(data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)


def make_docx() -> None:
    path = FIXTURES_DIR / "sample.docx"
    d = DocxDocument()
    d.add_heading("SYNTHETIC TEST DOCUMENT - NOT A REAL CASE FILE", level=1)
    d.add_heading("Section 1: Fictional Background", level=2)
    d.add_paragraph(
        "This DOCX fixture is synthetic and created only to benchmark Docling's "
        "DOCX parsing. It has no relation to any real matter."
    )
    d.add_heading("Section 2: Fictional Findings", level=2)
    d.add_paragraph("Finding A (fictional): placeholder text one.")
    d.add_paragraph("Finding B (fictional): placeholder text two.")
    d.add_heading("Section 3: Fictional Table", level=2)
    table = d.add_table(rows=3, cols=3)
    table.style = "Table Grid"
    headers = ["Item", "Fictional Value", "Fictional Note"]
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    table.rows[1].cells[0].text = "Row 1"
    table.rows[1].cells[1].text = "100"
    table.rows[1].cells[2].text = "Sample note"
    table.rows[2].cells[0].text = "Row 2"
    table.rows[2].cells[1].text = "200"
    table.rows[2].cells[2].text = "Another note"
    d.save(str(path))


def make_xlsx() -> None:
    path = FIXTURES_DIR / "sample.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "FictionalSheet"
    ws.append(["Case Ref (fictional)", "Fictional Amount", "Fictional Status"])
    ws.append(["FX-0001", 1000, "Open"])
    ws.append(["FX-0002", 2500, "Closed"])
    ws.append(["FX-0003", 750, "Open"])
    wb.save(str(path))


def make_pptx() -> None:
    path = FIXTURES_DIR / "sample.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "SYNTHETIC TEST DECK - NOT REAL"
    slide.placeholders[1].text = "Fictional subtitle for Docling benchmarking"
    slide2 = prs.slides.add_slide(prs.slide_layouts[1])
    slide2.shapes.title.text = "Fictional Section"
    body = slide2.placeholders[1].text_frame
    body.text = "Fictional bullet one"
    body.add_paragraph().text = "Fictional bullet two"
    prs.save(str(path))


def shape_arabic(text: str) -> str:
    """Apply Arabic glyph joining + BIDI reordering so the PDF stores text in the
    correct visual order. Without this, naive drawString/drawRightString calls with
    raw logical-order Arabic produce visually-reversed, unjoined letters in the PDF,
    which would unfairly bias any OCR/text-extraction benchmark against Docling."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def make_arabic_pdf() -> bool:
    """Arabic-only synthetic PDF. Uses a bundled Unicode font if available,
    otherwise falls back to a note explaining the limitation."""
    path = FIXTURES_DIR / "sample_arabic.pdf"
    font_candidates = [
        pathlib.Path(r"C:\Windows\Fonts\arial.ttf"),
        pathlib.Path(r"C:\Windows\Fonts\tahoma.ttf"),
    ]
    font_path = next((f for f in font_candidates if f.exists()), None)
    c = canvas.Canvas(str(path), pagesize=A4)
    if font_path:
        pdfmetrics.registerFont(TTFont("ArabicFont", str(font_path)))
        c.setFont("ArabicFont", 14)
    else:
        c.setFont("Helvetica", 14)
    # Fictional Arabic legal-style text (synthetic, not a real document).
    lines = [
        "هذا مستند تجريبي اصطناعي وليس ملف قضية حقيقي",
        "العنوان: مذكرة تجريبية خيالية",
        "الطرف الأول: شركة الاختبار الوهمية",
        "الطرف الثاني: مؤسسة النموذج الوهمية",
        "البند الأول: هذا نص تجريبي فقط لاختبار استخراج النص العربي",
        "البند الثاني: يجب أن يحافظ الترتيب على اتجاه الكتابة من اليمين لليسار",
    ]
    y = 800
    for line in lines:
        c.drawRightString(540, y, shape_arabic(line) if font_path else line)
        y -= 24
    c.showPage()
    c.save()
    return font_path is not None


def make_mixed_language_pdf() -> bool:
    path = FIXTURES_DIR / "sample_mixed_ar_en.pdf"
    font_candidates = [
        pathlib.Path(r"C:\Windows\Fonts\arial.ttf"),
        pathlib.Path(r"C:\Windows\Fonts\tahoma.ttf"),
    ]
    font_path = next((f for f in font_candidates if f.exists()), None)
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(72, 800, "SYNTHETIC MIXED-LANGUAGE DOCUMENT - NOT REAL")
    c.drawString(72, 780, "Section 1: English fictional clause.")
    c.drawString(72, 760, "This is a fictional clause used only for benchmarking.")
    if font_path:
        pdfmetrics.registerFont(TTFont("ArabicFont2", str(font_path)))
        c.setFont("ArabicFont2", 12)
        c.drawRightString(540, 730, shape_arabic("القسم الثاني: بند تجريبي باللغة العربية"))
        c.drawRightString(540, 710, shape_arabic("هذا بند خيالي لأغراض الاختبار فقط"))
    c.setFont("Helvetica", 12)
    c.drawString(72, 680, "Section 3: Back to English fictional clause.")
    c.showPage()
    c.save()
    return font_path is not None


def make_corrupted_file() -> None:
    path = FIXTURES_DIR / "corrupted.pdf"
    path.write_bytes(b"%PDF-1.4\nTHIS IS NOT A VALID PDF BODY \x00\x01\x02 BROKEN")


def make_unsupported_file() -> None:
    path = FIXTURES_DIR / "unsupported.xyz"
    path.write_text("This is a made-up extension Docling is not expected to support.")


def main() -> None:
    make_plain_text_pdf()
    make_table_pdf()
    make_docx()
    make_xlsx()
    make_pptx()
    arabic_font_ok = make_arabic_pdf()
    mixed_font_ok = make_mixed_language_pdf()
    make_corrupted_file()
    make_unsupported_file()
    print("Fixtures generated in", FIXTURES_DIR)
    print("Arabic font embedded:", arabic_font_ok)
    print("Mixed-language font embedded:", mixed_font_ok)


if __name__ == "__main__":
    main()
