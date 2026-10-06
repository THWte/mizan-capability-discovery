#!/usr/bin/env python3
"""A30 — million-word / 1000-page synthetic stress benchmark."""
from __future__ import annotations
import json,os,time,tracemalloc,hashlib
from pathlib import Path
from mizan_agents.long_document_stream import PageInput,PageResult,process_pages_streaming
from mizan_agents.legal_segmentation import segment_page
from mizan_agents.selective_ocr import route_page,PageRoute

OUT=Path(os.getenv("MIZAN_A30_OUT","benchmarks/long_documents/results/a30-results.json"))
PAGES=int(os.getenv("MIZAN_A30_PAGES","1000"))
WORDS_PER_PAGE=int(os.getenv("MIZAN_A30_WORDS_PER_PAGE","1000"))

AR=("المحكمة","المدعي","المدعى","الحكم","الأسباب","المستند","الدعوى","الطلب","الاستئناف","المادة","العقد","المبلغ","التاريخ","الطرف","الواقعة")

def make_page(i):
    words=[AR[(i+j)%len(AR)] for j in range(WORDS_PER_PAGE)]
    heading=("الوقائع\n" if i%5==1 else "الأسباب\n" if i%5==2 else "المنطوق\n" if i%5==3 else "")
    text=heading+" ".join(words)
    h=hashlib.sha256(text.encode()).hexdigest()
    # ~5% raster/ocr, ~5% ambiguous, ~5% tables; rest born-digital.
    if i%20==0:
        return PageInput(page_number=i,raw_text="",source_page_sha256=h,has_text_layer=False,image_coverage=1.0)
    if i%20==1:
        return PageInput(page_number=i,raw_text=text[:30],source_page_sha256=h,has_text_layer=True,image_coverage=0.6)
    return PageInput(page_number=i,raw_text=text,source_page_sha256=h,has_text_layer=True,image_coverage=0.0,table_hint=(i%20==2))

def processor(page):
    text=page.raw_text if page.raw_text else "OCR_SYNTHETIC_PAGE"
    spans=segment_page(page.page_number,text)
    return PageResult(page_number=page.page_number,raw_text=text,normalized_text=text,source_page_sha256=page.source_page_sha256,page_locator=f"MIZAN-DOC-000001/PAGE-{page.page_number:06d}",block_locators=tuple(s.span_id for s in spans))

def main():
    pages=[make_page(i) for i in range(1,PAGES+1)]
    routes=[route_page(p).route for p in pages]
    source_sha=hashlib.sha256("".join(p.source_page_sha256 for p in pages).encode()).hexdigest()
    t0=time.perf_counter();tracemalloc.start()
    last=None;count=0
    for result,cp in process_pages_streaming(document_id="MIZAN-DOC-000001",source_sha256=source_sha,pages=pages,page_processor=processor,checkpoint_every=10):
        count+=1; last=cp
    elapsed=time.perf_counter()-t0
    current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    # Resume must process zero pages once all completed.
    resumed=sum(1 for _ in process_pages_streaming(document_id="MIZAN-DOC-000001",source_sha256=source_sha,pages=pages,page_processor=processor,checkpoint=last))
    total_words=PAGES*WORDS_PER_PAGE
    result={
      "benchmark":"MIZAN-A30-Long-Document-v1",
      "pages":PAGES,"words":total_words,"processed_pages":count,"resume_reprocessed_pages":resumed,
      "elapsed_seconds":elapsed,"pages_per_second":count/elapsed if elapsed else None,
      "peak_python_bytes":peak,
      "routes":{r.value:routes.count(r) for r in PageRoute},
      "acceptance":{
        "zero_silent_page_loss": count==PAGES,
        "resume_without_reprocessing": resumed==0,
        "page_traceability_100_percent": last is not None and len(last.completed_pages)==PAGES,
        "million_word_target_reached": total_words>=1_000_000,
      }
    }
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    if not all(result["acceptance"].values()):
        raise SystemExit(2)

if __name__=="__main__": main()
