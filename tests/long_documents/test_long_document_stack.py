from __future__ import annotations
import hashlib,dataclasses,pytest
from mizan_agents.long_document_stream import PageInput,PageResult,make_checkpoint,pages_to_process,process_pages_streaming,LongDocumentError
from mizan_agents.selective_ocr import route_page,PageRoute
from mizan_agents.legal_segmentation import segment_page,build_hierarchy

H=lambda s: hashlib.sha256(s.encode()).hexdigest()

def page(n,text="نص عربي قانوني "*20,**kw):
    return PageInput(page_number=n,raw_text=text,source_page_sha256=H(f"{n}:{text}"),**kw)

def proc(p):
    spans=segment_page(p.page_number,p.raw_text)
    return PageResult(page_number=p.page_number,raw_text=p.raw_text,normalized_text=p.raw_text,source_page_sha256=p.source_page_sha256,page_locator=f"D/P/{p.page_number}",block_locators=tuple(s.span_id for s in spans))

def test_a27_resume_does_not_reprocess_completed_pages():
    pages=[page(i) for i in range(1,101)]
    source=H("source")
    first=[]
    cp=None
    for r,c in process_pages_streaming(document_id="D",source_sha256=source,pages=pages[:60],page_processor=proc):
        first.append(r.page_number);cp=c
    second=[r.page_number for r,c in process_pages_streaming(document_id="D",source_sha256=source,pages=pages,page_processor=proc,checkpoint=cp)]
    assert first==list(range(1,61))
    assert second==list(range(61,101))

def test_a27_rejects_tampered_checkpoint_and_cross_document_resume():
    cp=make_checkpoint("D",H("s"),[1,2,3])
    bad=dataclasses.replace(cp,completed_pages=(1,2,3,999))
    with pytest.raises(LongDocumentError,match="integrity"):
        list(pages_to_process([page(1)],bad))
    with pytest.raises(LongDocumentError,match="another document"):
        list(process_pages_streaming(document_id="OTHER",source_sha256=H("s"),pages=[page(1)],page_processor=proc,checkpoint=cp))

def test_a28_selective_ocr_routes_per_page_not_whole_document():
    assert route_page(page(1,has_text_layer=True,image_coverage=0)).route is PageRoute.TEXT_ONLY
    assert route_page(page(2,text="",has_text_layer=False,image_coverage=1)).route is PageRoute.OCR_ONLY
    assert route_page(page(3,text="قصير",has_text_layer=True,image_coverage=.5)).route is PageRoute.TEXT_PLUS_OCR_COMPARE
    assert route_page(page(4,text="",has_text_layer=False,image_coverage=1,table_hint=True)).route is PageRoute.TABLE_SPECIALIST
    assert route_page(page(5,low_quality_hint=True)).route is PageRoute.HUMAN_REVIEW

def test_a29_segmentation_is_deterministic_traceable_and_bounded():
    text="الوقائع\n"+"كلمة "*2000
    a=segment_page(7,text,max_chars=500,overlap=50)
    b=segment_page(7,text,max_chars=500,overlap=50)
    assert a==b and len(a)>1
    assert all(s.page_number==7 and s.end_offset>s.start_offset and len(s.text)<=500 for s in a)
    assert [s.span_id for s in a]==[s.span_id for s in b]
    hierarchy=build_hierarchy(a)
    assert hierarchy[0].first_page==7 and hierarchy[0].last_page==7

def test_no_fact_or_evidence_authority_fields_are_introduced():
    for obj in [page(1),route_page(page(1)),*segment_page(1,"المنطوق\nرفض الدعوى")]:
        names={f.name for f in dataclasses.fields(obj)}
        assert "fact_status" not in names
        assert "evidentiary_authority" not in names
        assert "accepted_fact" not in names
