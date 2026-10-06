#!/usr/bin/env python3
from pathlib import Path
import json, tempfile, time
import fitz
from mizan_agents.intelligent_document_ingestion import ingest_pdf,ExtractionKind

PAGES=24

def build(path):
    fontfile=Path("C:/Windows/Fonts/arial.ttf")
    doc=fitz.open()
    for i in range(1,PAGES+1):
        p=doc.new_page(); p.insert_font(fontname="AR",fontfile=str(fontfile))
        if i==1:
            text="المحكمة الجزائية بمكة المكرمة\nالدائرة السادسة\nرقم القضية 4870236421\nرقم الحكم 123456789\nالتاريخ 18-04-1448"
        elif i==2:
            text="الطلبات\nيطلب المدعي الحكم بالتعويض بمبلغ 12500 ريال"
        elif i==20:
            text="الاسباب\nثبت للمحكمة من المستندات محل النظر"
        elif i==24:
            text="المنطوق\nحكمت الدائرة بما هو مبين في هذا المثال الاصطناعي"
        else:
            text=("الوقائع\n"+"هذه صفحة اصطناعية لاختبار الاستخراج المباشر من الصك الطويل. "*30)
        p.insert_textbox(fitz.Rect(50,50,545,790),text,fontsize=11,fontname="AR")
    doc.save(path);doc.close()

def main():
    outp=Path("benchmarks/long_documents/results/a33-results.json")
    with tempfile.TemporaryDirectory() as td:
        pdf=Path(td)/"judgment_24p.pdf";build(pdf)
        t=time.perf_counter()
        out=ingest_pdf(pdf_path=pdf,document_id="MIZAN-DOC-A33")
        elapsed=time.perf_counter()-t
        candidates=[c for pg in out.pages for c in pg.extraction_candidates]
        kinds={c.kind.value for c in candidates}
        result={
          "benchmark":"MIZAN-A33-Intelligent-Ingestion-v1",
          "pages":out.page_count,
          "ocr_pages":list(out.ocr_pages),
          "human_review_pages":list(out.human_review_pages),
          "candidate_count":len(candidates),
          "candidate_kinds":sorted(kinds),
          "elapsed_seconds":elapsed,
          "pages_per_second":out.page_count/elapsed if elapsed else None,
          "acceptance":{
            "all_24_pages_processed":out.page_count==24,
            "direct_text_skips_ocr":len(out.ocr_pages)==0,
            "case_number_extracted":"CASE_NUMBER" in kinds,
            "judgment_number_extracted":"JUDGMENT_NUMBER" in kinds,
            "date_extracted":"DATE" in kinds,
            "amount_extracted":"AMOUNT" in kinds,
            "no_accepted_fact_created":out.accepted_fact_count==0,
            "page_traceability":all(c.page_number>=1 and c.span_id for c in candidates),
          }
        }
        result["acceptance_all"]=all(result["acceptance"].values())
        outp.parent.mkdir(parents=True,exist_ok=True)
        outp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if not result["acceptance_all"]: raise SystemExit(2)

if __name__=="__main__": main()
