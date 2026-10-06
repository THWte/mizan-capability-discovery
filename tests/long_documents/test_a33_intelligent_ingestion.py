from pathlib import Path
import fitz
from mizan_agents.intelligent_document_ingestion import *

def make_pdf(path:Path):
    fontfile=Path("C:/Windows/Fonts/arial.ttf")
    doc=fitz.open()
    p=doc.new_page(); p.insert_text((72,72),"المحكمة الجزائية\nرقم القضية 4870236421\nرقم الحكم 123456\nالتاريخ 18-04-1448\nالمبلغ 12500 ريال")
    p=doc.new_page(); p.insert_text((72,72),"الطلبات\nطلب المدعي الحكم له بالتعويض")
    p=doc.new_page(); p.insert_text((72,72),"الاسباب\nثبت للمحكمة من المستندات")
    doc.save(path);doc.close()

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
