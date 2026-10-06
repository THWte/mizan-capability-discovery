#!/usr/bin/env python3
from pathlib import Path
import json,tempfile,time,subprocess
from mizan_agents.intelligent_document_ingestion import ingest_pdf

PAGES=24
def html_document():
    parts=["<!doctype html><html lang='ar' dir='rtl'><meta charset='utf-8'><style>@page{size:A4;margin:18mm}body{font-family:Arial;font-size:16px}.page{page-break-after:always}</style><body>"]
    for i in range(1,PAGES+1):
        if i==1:
            body="<h1>المحكمة الجزائية بمكة المكرمة</h1><p>الدائرة السادسة</p><p>رقم القضية 4870236421</p><p>رقم الحكم 123456789</p><p>التاريخ 18-04-1448</p>"
        elif i==2: body="<h2>الطلبات</h2><p>يطلب المدعي الحكم بالتعويض بمبلغ 12500 ريال</p>"
        elif i==20: body="<h2>الأسباب</h2><p>ثبت للمحكمة من المستندات محل النظر</p>"
        elif i==24: body="<h2>المنطوق</h2><p>حكمت الدائرة بما هو مبين في هذا المثال الاصطناعي</p>"
        else: body="<h2>الوقائع</h2><p>"+("هذه صفحة اصطناعية لاختبار الاستخراج المباشر من الصك الطويل. "*35)+"</p>"
        parts.append(f"<section class='page'>{body}</section>")
    parts.append("</body></html>")
    return "".join(parts)

def build_with_chrome(html,pdf):
    html.write_text(html_document(),encoding="utf-8")
    chrome=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if not chrome.exists(): chrome=Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if not chrome.exists(): raise RuntimeError("Chromium browser not found on Windows runner")
    url=html.resolve().as_uri()
    subprocess.run([str(chrome),"--headless","--disable-gpu","--no-pdf-header-footer",f"--print-to-pdf={pdf.resolve()}",url],check=True,timeout=90)
    if not pdf.exists() or pdf.stat().st_size==0: raise RuntimeError("PDF generation failed")

def main():
    outp=Path("benchmarks/long_documents/results/a33-results.json")
    with tempfile.TemporaryDirectory() as td:
        html=Path(td)/"judgment.html"; pdf=Path(td)/"judgment_24p.pdf"; build_with_chrome(html,pdf)
        t=time.perf_counter(); out=ingest_pdf(pdf_path=pdf,document_id="MIZAN-DOC-A33"); elapsed=time.perf_counter()-t
        candidates=[c for pg in out.pages for c in pg.extraction_candidates]; kinds={c.kind.value for c in candidates}
        result={"benchmark":"MIZAN-A33-Intelligent-Ingestion-v1","fixture":"Chromium HTML-to-PDF Arabic Unicode","pages":out.page_count,"ocr_pages":list(out.ocr_pages),"human_review_pages":list(out.human_review_pages),"candidate_count":len(candidates),"candidate_kinds":sorted(kinds),"elapsed_seconds":elapsed,"pages_per_second":out.page_count/elapsed if elapsed else None,"acceptance":{"all_24_pages_processed":out.page_count==24,"direct_text_skips_ocr":len(out.ocr_pages)==0,"case_number_extracted":"CASE_NUMBER" in kinds,"judgment_number_extracted":"JUDGMENT_NUMBER" in kinds,"date_extracted":"DATE" in kinds,"amount_extracted":"AMOUNT" in kinds,"no_accepted_fact_created":out.accepted_fact_count==0,"page_traceability":all(c.page_number>=1 and c.span_id for c in candidates)}}
        result["acceptance_all"]=all(result["acceptance"].values()); outp.parent.mkdir(parents=True,exist_ok=True); outp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(result,ensure_ascii=False,indent=2))
        if not result["acceptance_all"]: raise SystemExit(2)
if __name__=="__main__": main()
