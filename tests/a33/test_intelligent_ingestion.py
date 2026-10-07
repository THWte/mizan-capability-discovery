from pathlib import Path
import fitz
from mizan_agents.intelligent_document_ingestion import *
from mizan_agents.intelligent_document_ingestion import _label_present, _resolve_page_amounts

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


def test_amount_resolver_requires_currency_and_handles_arabic_digits_across_lines():
    from mizan_agents.legal_segmentation import segment_page
    spans=segment_page(1,"المبلغ ١٢٬٥٠٠٫٧٥\nريال")
    got=_resolve_page_amounts(1,spans)
    assert len(got)==1
    assert got[0].value=="١٢٬٥٠٠٫٧٥"
    assert got[0].verified is False
    bare=segment_page(1,"رقم القضية 4870236421")
    assert _resolve_page_amounts(1,bare)==()


def test_amount_resolver_accepts_rtl_currency_before_number_and_spaced_currency():
    from mizan_agents.legal_segmentation import segment_page
    rtl=segment_page(1,"ريال\n12500")
    got=_resolve_page_amounts(1,rtl)
    assert len(got)==1 and got[0].value=="12500"
    spaced=segment_page(1,"12500 ر ي ا ل")
    got2=_resolve_page_amounts(1,spaced)
    assert len(got2)==1 and got2[0].value=="12500"
