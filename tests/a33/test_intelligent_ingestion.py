from pathlib import Path
import fitz
from mizan_agents.intelligent_document_ingestion import *
from mizan_agents.intelligent_document_ingestion import _label_present

def make_pdf(path:Path):
    # Create a PDF from HTML through Chromium in the workflow before this test
    # when available; for unit behavior use a PDF with ASCII machine labels plus
    # Arabic content, while Arabic fidelity is verified by the 24-page E2E gate.
    doc=fitz.open()
    p=doc.new_page()
    p.insert_text((72,72),"CASE_NUMBER 4870236421\nJUDGMENT_NUMBER 123456\nDATE 18-04-1448\nAMOUNT 12500 SAR")
    p=doc.new_page(); p.insert_text((72,72),"REQUEST section")
    p=doc.new_page(); p.insert_text((72,72),"REASONING section")
    doc.save(path);doc.close()

def test_a33_candidates_never_self_verify():
    c=ExtractedCandidate(kind=ExtractionKind.CASE_NUMBER,value="4870236421",page_number=1,span_id="s",confidence=.9)
    assert c.verified is False
    import pytest
    with pytest.raises(IngestionError):
        ExtractedCandidate(kind=ExtractionKind.CASE_NUMBER,value="x",page_number=1,span_id="s",confidence=.9,verified=True)

def test_a33_label_helpers_do_not_invent_from_bare_number():
    assert not _label_present("4870236421",ExtractionKind.CASE_NUMBER)
