#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, time
from pathlib import Path
import fitz, psutil

from mizan_agents.long_document_stream import PageInput, PageResult, process_pages_streaming
from mizan_agents.selective_ocr import route_page, PageRoute
from mizan_agents.legal_segmentation import segment_page

OUT=Path(os.getenv("MIZAN_A31_OUT","benchmarks/long_documents/results/a31-results.json"))
DIGITAL=Path("benchmarks/long_documents/fixtures/a31_arabic_100p_digital.pdf")
MIXED=Path("benchmarks/long_documents/fixtures/a31_arabic_100p_mixed.pdf")
RSS_LIMIT=int(os.getenv("MIZAN_A31_RSS_LIMIT_MB","700"))*1024*1024

def file_sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):
            h.update(c)
    return h.hexdigest()

def page_fingerprint(doc_sha:str,page_no:int,text:str,image_count:int)->str:
    return hashlib.sha256(f"{doc_sha}|{page_no}|{text}|{image_count}".encode("utf-8")).hexdigest()

def decode_pdf(path:Path):
    proc=psutil.Process()
    rss_peak=proc.memory_info().rss
    doc=fitz.open(path)
    doc_sha=file_sha(path)
    page_inputs=[]
    stats=[]
    for i in range(doc.page_count):
        page=doc.load_page(i)
        text=page.get_text("text") or ""
        images=page.get_images(full=True)
        rss_peak=max(rss_peak,proc.memory_info().rss)
        page_inputs.append(PageInput(
            page_number=i+1,
            raw_text=text,
            source_page_sha256=page_fingerprint(doc_sha,i+1,text,len(images)),
            has_text_layer=bool(text.strip()),
            image_coverage=1.0 if (not text.strip() and images) else (0.5 if images else 0.0),
            table_hint=False,
        ))
        stats.append({"page":i+1,"text_chars":len(text),"images":len(images)})
    doc.close()
    return doc_sha,page_inputs,stats,rss_peak

def processor(page:PageInput)->PageResult:
    spans=segment_page(page.page_number,page.raw_text or "OCR_REQUIRED_PLACEHOLDER")
    return PageResult(
        page_number=page.page_number,
        raw_text=page.raw_text,
        normalized_text=page.raw_text,
        source_page_sha256=page.source_page_sha256,
        page_locator=f"MIZAN-DOC-A31/PAGE-{page.page_number:06d}",
        block_locators=tuple(s.span_id for s in spans),
    )

def run_one(path:Path,expected_pages:int,expected_ocr_pages:int):
    t0=time.perf_counter()
    sha,pages,stats,rss_peak=decode_pdf(path)
    routes=[route_page(p).route for p in pages]
    completed=[]
    last=None
    for result,cp in process_pages_streaming(
        document_id="MIZAN-DOC-A31",
        source_sha256=sha,
        pages=pages,
        page_processor=processor,
    ):
        completed.append(result.page_number)
        last=cp
    resumed=sum(1 for _ in process_pages_streaming(
        document_id="MIZAN-DOC-A31",
        source_sha256=sha,
        pages=pages,
        page_processor=processor,
        checkpoint=last,
    ))
    elapsed=time.perf_counter()-t0
    ocr_pages=sum(1 for r in routes if r in (PageRoute.OCR_ONLY,PageRoute.TEXT_PLUS_OCR_COMPARE,PageRoute.TABLE_SPECIALIST))
    text_pages=sum(1 for p in pages if p.has_text_layer)
    return {
        "path":str(path),"sha256":sha,"page_count":len(pages),
        "text_pages":text_pages,"ocr_candidate_pages":ocr_pages,
        "completed_pages":len(completed),"resume_reprocessed_pages":resumed,
        "elapsed_seconds":elapsed,"pages_per_second":len(pages)/elapsed if elapsed else None,
        "rss_peak_bytes":rss_peak,
        "rss_limit_bytes":RSS_LIMIT,
        "acceptance":{
            "expected_page_count":len(pages)==expected_pages,
            "zero_silent_page_loss":len(completed)==expected_pages and completed==list(range(1,expected_pages+1)),
            "resume_without_reprocessing":resumed==0,
            "ocr_candidate_detection":ocr_pages==expected_ocr_pages,
            "rss_within_limit":rss_peak<=RSS_LIMIT,
        },
        "sample_page_stats":stats[:3]+stats[-3:],
    }

def main():
    results={
      "benchmark":"MIZAN-A31-Real-Long-PDF-Windows-v1",
      "platform":os.name,
      "digital":run_one(DIGITAL,100,0),
      "mixed":run_one(MIXED,100,10),
      "scope":[
        "real PDF open/decode on GitHub windows-latest",
        "Arabic Unicode fixture generation",
        "born-digital text extraction",
        "image-only page detection",
        "streaming/checkpoint/resume",
        "memory ceiling"
      ],
      "not_measured":[
        "PaddleOCR/Docling production stability",
        "OCR character accuracy on image-only Arabic pages",
        "owner laptop hardware performance"
      ]
    }
    results["acceptance_all"]=all(
        all(section["acceptance"].values())
        for section in (results["digital"],results["mixed"])
    )
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(results,ensure_ascii=False,indent=2))
    if not results["acceptance_all"]:
        raise SystemExit(2)

if __name__=="__main__":
    main()
