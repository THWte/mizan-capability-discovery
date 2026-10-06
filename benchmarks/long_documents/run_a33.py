#!/usr/bin/env python3
from pathlib import Path
import json,tempfile,time
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from mizan_agents.intelligent_document_ingestion import ingest_pdf

PAGES=24

def build(path):
    fontfile=Path("C:/Windows/Fonts/arial.ttf")
    pdfmetrics.registerFont(TTFont("MIZAN_AR",str(fontfile)))
    c=canvas.Canvas(str(path))
    for i in range(1,PAGES+1):
        if i==1:
            lines=["المحكمة الجزائية بمكة المكرمة","الدائرة السادسة","رقم القضية 4870236421","رقم الحكم 123456789","التاريخ 18-04-1448"]
        elif i==2:
            lines=["الطلبات","يطلب المدعي الحكم بالتعويض بمبلغ 12500 ريال"]
        elif i==20:
            lines=["الأسباب","ثبت للمحكمة من المستندات محل النظر"]
        elif i==24:
            lines=["المنطوق","حكمت الدائرة بما هو مبين في هذا المثال الاصطناعي"]
        else:
            lines=["الوقائع"]+["هذه صفحة اصطناعية لاختبار الاستخراج المباشر من الصك الطويل."]*18
        y=790
        c.setFont("MIZAN_AR",11)
        for line in lines:
            c.drawString(50,y,line)
            y-=28
        c.showPage()
    c.save()

def main():
    outp=Path("benchmarks/long_documents/results/a33-results.json")
    with tempfile.TemporaryDirectory() as td:
        pdf=Path(td)/"judgment_24p.pdf"; build(pdf)
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
