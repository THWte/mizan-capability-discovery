from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from mizan_agents.intelligent_document_ingestion import *

def _font():
    path=Path("C:/Windows/Fonts/arial.ttf")
    pdfmetrics.registerFont(TTFont("MIZAN_AR",str(path)))
    return "MIZAN_AR"

def make_pdf(path:Path):
    font=_font()
    c=canvas.Canvas(str(path))
    pages=[
        ["المحكمة الجزائية","رقم القضية 4870236421","رقم الحكم 123456","التاريخ 18-04-1448","المبلغ 12500 ريال"],
        ["الطلبات","طلب المدعي الحكم له بالتعويض"],
        ["الأسباب","ثبت للمحكمة من المستندات"],
    ]
    for lines in pages:
        y=780
        c.setFont(font,14)
        for line in lines:
            c.drawString(70,y,line)
            y-=28
        c.showPage()
    c.save()

def test_a33_direct_text_pdf_skips_ocr_and_extracts_structured_candidates(tmp_path):
    p=tmp_path/"x.pdf"; make_pdf(p)
    out=ingest_pdf(pdf_path=p,document_id="MIZAN-DOC-TEST")
    assert out.page_count==3
    assert out.ocr_pages==()
    kinds={c.kind for pg in out.pages for c in pg.extraction_candidates}
    assert ExtractionKind.CASE_NUMBER in kinds
    assert ExtractionKind.JUDGMENT_NUMBER in kinds
    assert ExtractionKind.DATE in kinds
    assert ExtractionKind.AMOUNT in kinds
    assert out.accepted_fact_count==0

def test_a33_candidates_preserve_page_and_span_traceability(tmp_path):
    p=tmp_path/"x.pdf"; make_pdf(p)
    out=ingest_pdf(pdf_path=p,document_id="MIZAN-DOC-TEST")
    allc=[c for pg in out.pages for c in pg.extraction_candidates]
    assert all(c.page_number>=1 and c.span_id for c in allc)
    assert all(c.verified is False for c in allc)
