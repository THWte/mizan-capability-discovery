#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, time, unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parent
GT=ROOT/"fixtures"/"ground_truth.json"
OUT=Path(os.getenv("MIZAN_A32_OUT","benchmarks/ocr_a32/results/a32-results.json"))
DIGIT_TRANS=str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹","01234567890123456789")

def norm(s:str)->str:
    s=unicodedata.normalize("NFKC",s).translate(DIGIT_TRANS)
    s=re.sub(r"[\u064b-\u065f\u0670\u0640]","",s)
    s=s.replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ى","ي")
    s=re.sub(r"[^0-9A-Za-z\u0600-\u06FF.\-\s]"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def lev(a,b):
    if len(a)<len(b): a,b=b,a
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1):
            cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]

def cer(ref,hyp):
    r=norm(ref); h=norm(hyp)
    return lev(r,h)/max(len(r),1)

def wer(ref,hyp):
    r=norm(ref).split(); h=norm(hyp).split()
    return lev(r,h)/max(len(r),1)

def critical_tokens(s):
    s=norm(s)
    return set(re.findall(r"(?<!\\d)\\d[\\d.\\-]{2,}(?!\\d)",s))

def critical_recall(ref,hyp):
    r=critical_tokens(ref); h=critical_tokens(hyp)
    return 1.0 if not r else len(r & h)/len(r)

def ocr_one(path:str):
    import paddleocr, paddle
    if getattr(paddleocr,"__version__","")!="3.3.3":
        raise RuntimeError("paddleocr version mismatch")
    if getattr(paddle,"__version__","")!="3.2.2":
        raise RuntimeError("paddlepaddle version mismatch")
    engine=paddleocr.PaddleOCR(
        lang="ar",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    pages=list(engine.predict(path))
    lines=[]
    for page in pages:
        for t in (page.get("rec_texts") or []):
            if t: lines.append(str(t))
    return "\n".join(lines)

def child_main(path,out):
    payload={"path":path,"success":False,"text":"","error":None}
    try:
        payload["text"]=ocr_one(path)
        payload["success"]=True
    except BaseException as e:
        payload["error"]=f"{type(e).__name__}: {e}"
    Path(out).write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")

def classify(rows):
    valid=[r for r in rows if not r.get("expected_failure")]
    mean_cer=sum(r["cer"] for r in valid)/len(valid)
    mean_wer=sum(r["wer"] for r in valid)/len(valid)
    mean_critical=sum(r["critical_recall"] for r in valid)/len(valid)
    clear=next(r for r in valid if r["name"]=="clear")
    numeric=next(r for r in valid if r["name"]=="numeric")
    if clear["cer"]<=0.05 and clear["wer"]<=0.15 and mean_cer<=0.15 and mean_wer<=0.30 and mean_critical==1.0:
        return "PASS"
    if clear["cer"]<=0.12 and clear["wer"]<=0.30 and mean_cer<=0.40 and mean_wer<=0.65 and mean_critical>=0.60:
        return "CONDITIONAL_PASS"
    return "FAIL"

def parent_main():
    manifest=json.loads(GT.read_text(encoding="utf-8"))
    temp=ROOT/"results"/"child"; temp.mkdir(parents=True,exist_ok=True)
    rows=[]
    started=time.perf_counter()
    for name,item in manifest.items():
        result_file=temp/f"{name}.json"
        cmd=[sys.executable,__file__,"--child",item["path"],str(result_file)]
        p=subprocess.run(cmd,timeout=180,check=False)
        if result_file.exists():
            child=json.loads(result_file.read_text(encoding="utf-8"))
        else:
            child={"success":False,"text":"","error":f"subprocess_exit={p.returncode}"}
        expected_failure=bool(item.get("expected_failure"))
        row={"name":name,"expected_failure":expected_failure,"subprocess_exit":p.returncode,**child}
        if not expected_failure:
            if not child["success"]:
                row.update({"cer":1.0,"wer":1.0,"critical_recall":0.0})
            else:
                row.update({
                    "cer":cer(item["expected_text"],child["text"]),
                    "wer":wer(item["expected_text"],child["text"]),
                    "critical_recall":critical_recall(item["expected_text"],child["text"]),
                })
        rows.append(row)
    recovery_ok=(
        any(r["name"]=="corrupt" and not r["success"] for r in rows)
        and any(r["name"]=="low_quality" for r in rows)
        and rows[-1]["name"]=="corrupt"
    )
    engine_execution_ok=all(r["success"] for r in rows if not r["expected_failure"])
    decision=classify(rows) if engine_execution_ok else "FAIL"
    out={
      "benchmark":"MIZAN-A32-Arabic-OCR-Accuracy-Recovery-v1",
      "engine":{"paddleocr":"3.3.3","paddlepaddle":"3.2.2","mode":"isolated_subprocess_per_fixture"},
      "fixtures":rows,
      "engine_execution_ok":engine_execution_ok,
      "recovery_isolation_ok":recovery_ok,
      "quality_decision":decision,
      "production_approved":False,
      "elapsed_seconds":time.perf_counter()-started,
      "acceptance":{
        "measurement_completed":len(rows)==len(manifest),
        "all_valid_fixtures_executed":engine_execution_ok,
        "corrupt_fixture_isolated":recovery_ok,
        "quality_is_separate_from_harness_success":True
      }
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))
    # CI fails only if harness/engine execution/recovery failed, not for honest poor quality.
    if not all(out["acceptance"].values()):
        raise SystemExit(2)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--child",nargs=2,metavar=("IMAGE","OUT"))
    args=ap.parse_args()
    if args.child: child_main(*args.child)
    else: parent_main()
