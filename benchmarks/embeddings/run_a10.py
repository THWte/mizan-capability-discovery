#!/usr/bin/env python3
"""A10 MIZAN Arabic/Legal Embedding Benchmark v1.

Synthetic Arabic legal-style retrieval benchmark. It measures embedding retrieval
behavior only. It does not establish legal correctness, evidence authority, or
fitness on real case files.
"""
from __future__ import annotations

import json
import math
import os
import platform
import statistics
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import torch
from huggingface_hub import model_info
from sentence_transformers import SentenceTransformer

OUT=Path(os.getenv("MIZAN_A10_OUT","benchmarks/embeddings/results/a10-results.json"))

MODELS=[
    {"name":"multilingual-e5-base","repo":"intfloat/multilingual-e5-base","mode":"e5"},
    {"name":"bge-m3","repo":"BAAI/bge-m3","mode":"plain"},
    {"name":"multilingual-mpnet","repo":"sentence-transformers/paraphrase-multilingual-mpnet-base-v2","mode":"plain"},
]

@dataclass(frozen=True)
class Doc:
    id:str
    text:str
    domain:str

@dataclass(frozen=True)
class Query:
    id:str
    text:str
    relevant:tuple[str,...]
    kind:str

DOCS=[
Doc("D01","عامل يطلب تعويضاً عن إنهاء عقد العمل دون سبب مشروع بعد خدمة استمرت خمس سنوات.","labor"),
Doc("D02","نزاع عمالي بشأن فصل موظف من عمله ومطالبته بالتعويض عن الإنهاء غير المشروع.","labor"),
Doc("D03","عامل يطالب بأجر شهر متأخر وبدل ساعات عمل إضافية.","labor"),
Doc("D04","شركة أنهت عقد مقاول بسبب التأخر في تنفيذ مشروع إنشائي.","construction"),
Doc("D05","شركاء يعترضون على قرار تعيين مدير جديد للشركة ويطلبون إبطال قرار الشركاء.","companies"),
Doc("D06","نزاع بين شركاء حول صلاحيات المدير في توقيع العقود والتصرف في أصول الشركة.","companies"),
Doc("D07","مطالبة شريك بتوزيع أرباح سنوية لم تصرف له.","companies"),
Doc("D08","مدير سابق يطالب بمكافأة نهاية الخدمة بصفته موظفاً لدى الشركة.","labor"),
Doc("D09","طعن على حكم ابتدائي أمام محكمة الاستئناف وطلب نقض النتيجة وإعادة نظر النزاع.","appeal"),
Doc("D10","صدر حكم استئنافي أيد الحكم الابتدائي ورفض اعتراض المستأنف.","appeal"),
Doc("D11","طلب تنفيذ حكم مالي نهائي ضد مدين امتنع عن السداد.","enforcement"),
Doc("D12","نزاع حول اختصاص المحكمة التي نظرت الدعوى ابتداءً.","procedure"),
Doc("D13","ورثة يطلبون حصر موجودات التركة وقسمة العقارات والأموال بينهم.","inheritance"),
Doc("D14","خلاف بين الورثة بشأن بيع عقار موروث وتوزيع حصيلة البيع.","inheritance"),
Doc("D15","نزاع حول ملكية عقار اشتراه أحد الشركاء من ماله الخاص.","property"),
Doc("D16","طلب إثبات وصية صادرة من المورث قبل وفاته.","inheritance"),
Doc("D17","استند أحد الأطراف إلى رسائل واتساب لإثبات الاتفاق والمراسلات بين الطرفين.","evidence"),
Doc("D18","دليل إلكتروني عبارة عن محادثات ورسائل رقمية مطلوب التحقق من نسبتها إلى مرسلها.","evidence"),
Doc("D19","شاهد حضر توقيع العقد وقرر أمام المحكمة أنه رأى الطرفين يوقعان المستند.","evidence"),
Doc("D20","مستند ورقي مطعون في صحة التوقيع المنسوب إلى صاحبه.","evidence"),
Doc("D21","شخص استخدم وصف محام في خطاب رغم عدم ثبوت ترخيص مهني له.","legal_profession"),
Doc("D22","اتهام بممارسة أعمال المحاماة أو تقديم النفس بصفة مهنية دون ترخيص.","legal_profession"),
Doc("D23","محام مرخص يطالب موكله بسداد أتعاب متفق عليها في عقد مكتوب.","legal_profession"),
Doc("D24","موظف شركة قدم مشورة داخلية للإدارة دون تمثيل قضائي للغير.","legal_profession"),
Doc("D25","مالك مبنى يطالب المقاول بتعويض عن عيوب إنشائية ظهرت بعد التسليم.","construction"),
Doc("D26","نزاع عن تشققات وتسربات وعيوب في تنفيذ أعمال المقاولة.","construction"),
Doc("D27","مقاول يطالب بقيمة مستخلصات أعمال أنجزها ولم تسدد.","construction"),
Doc("D28","مورد يطالب شركة مقاولات بثمن مواد بناء تم توريدها.","commercial"),
Doc("D29","مؤجر يطلب إخلاء المستأجر لعدم سداد الأجرة المستحقة.","lease"),
Doc("D30","مستأجر يطلب تخفيض الأجرة بسبب عيب يمنع الانتفاع الكامل بالعين.","lease"),
Doc("D31","دعوى مطالبة بأجرة متأخرة عن عقد إيجار تجاري.","lease"),
Doc("D32","طلب إفراغ عقار مبيع للمشتري بعد سداد كامل الثمن.","property"),
Doc("D33","القضية رقم 4870236421 تتعلق بمخالفة مهنية مزعومة محل نظر قضائي.","identifier"),
Doc("D34","الصك رقم 351992847 مؤرخ في 18/04/1448هـ ويتضمن حكماً مالياً.","identifier"),
Doc("D35","مبلغ المطالبة 125000 ريال بينما يقر الخصم بمبلغ 120000 ريال فقط.","amount"),
Doc("D36","المطالبة بمبلغ 120000 ريال كاملة وفق كشف الحساب المرفق.","amount"),
Doc("D37","العقد ما زال نافذاً ولم يثبت فسخه أو إنهاؤه بين الطرفين.","contract_state"),
Doc("D38","ثبت فسخ العقد وانتهاء العلاقة التعاقدية بين الطرفين.","contract_state"),
Doc("D39","قضت المحكمة بقبول الدعوى شكلاً ورفضها موضوعاً.","procedure"),
Doc("D40","قضت المحكمة برفض الدعوى شكلاً دون بحث موضوعها.","procedure"),
Doc("D41","ألغت محكمة الاستئناف الحكم الابتدائي وقضت مجدداً برفض الطلب.","appeal"),
Doc("D42","أيدت محكمة الاستئناف الحكم الابتدائي وأبقت النتيجة كما هي.","appeal"),
Doc("D43","لم يثبت سداد المدين للمبلغ محل المطالبة.","payment_state"),
Doc("D44","ثبت سداد المدين كامل المبلغ محل المطالبة بموجب حوالة بنكية.","payment_state"),
Doc("D45","المدعي يطلب مبلغ 500000 ريال تعويضاً عن الضرر.","amount"),
Doc("D46","المدعي يطلب مبلغ 50000 ريال تعويضاً عن الضرر.","amount"),
Doc("D47","موعد الجلسة في 18/04/1448هـ.","date"),
Doc("D48","موعد الجلسة في 18/04/1447هـ.","date"),
Doc("D49","الحكم غير نهائي وما زال قابلاً للاعتراض.","judgment_state"),
Doc("D50","الحكم نهائي ومكتسب للقطعية وغير قابل للاعتراض بالطريق العادي.","judgment_state"),
]

QUERIES=[
Query("Q01","تعويض الموظف عن الفصل أو إنهاء العمل بلا سبب مشروع",("D01","D02"),"semantic"),
Query("Q02","الاعتراض على تعيين مدير الشركة وقرار الشركاء",("D05",),"semantic"),
Query("Q03","ما المستندات المتعلقة بصلاحيات مدير الشركة؟",("D06",),"semantic"),
Query("Q04","حكم الاستئناف الذي أيد حكم الدرجة الأولى",("D10",),"semantic"),
Query("Q05","تنفيذ حكم نهائي لتحصيل مبلغ من المدين",("D11",),"semantic"),
Query("Q06","قسمة التركة بين الورثة والعقارات الموروثة",("D13","D14"),"semantic"),
Query("Q07","إثبات الاتفاق عن طريق محادثات واتساب والرسائل الإلكترونية",("D17","D18"),"semantic"),
Query("Q08","الادعاء بصفة محام أو ممارسة المحاماة دون ترخيص",("D21","D22"),"semantic"),
Query("Q09","هل المشورة القانونية الداخلية لموظف الشركة تعد تمثيلاً قضائياً؟",("D24",),"hard_negative"),
Query("Q10","تعويض المالك عن عيوب المقاولة والتشققات والتسربات",("D25","D26"),"semantic"),
Query("Q11","إخلاء المستأجر بسبب عدم دفع الإيجار",("D29","D31"),"semantic"),
Query("Q12","القضية 4870236421",("D33",),"identifier"),
Query("Q13","الصك 351992847",("D34",),"identifier"),
Query("Q14","مطالبة بمبلغ 125 ألف ريال مع إقرار الخصم بمئة وعشرين ألفاً",("D35",),"amount"),
Query("Q15","المطالبة بمبلغ 120000 ريال",("D36","D35"),"amount"),
Query("Q16","مكافأة نهاية الخدمة لمدير كان موظفاً",("D08",),"hard_negative"),
Query("Q17","مطالبة المقاول بقيمة الأعمال المنفذة غير المسددة",("D27",),"semantic"),
Query("Q18","الطعن في صحة التوقيع على مستند ورقي",("D20",),"semantic"),
Query("Q19","المستند الذي يؤكد أن العقد لم يفسخ ولا يزال سارياً",("D37",),"negation"),
Query("Q20","المستند الذي يثبت انتهاء العقد بالفسخ",("D38",),"negation"),
Query("Q21","قبول الدعوى من ناحية الشكل مع خسارتها في الموضوع",("D39",),"procedural_contrast"),
Query("Q22","رفض القضية شكلياً من غير الدخول في أصل الحق",("D40",),"procedural_contrast"),
Query("Q23","الاستئناف نقض نتيجة الحكم الأول ولم يؤيده",("D41",),"outcome_contrast"),
Query("Q24","الاستئناف أبقى الحكم الابتدائي وأيده",("D42",),"outcome_contrast"),
Query("Q25","عدم ثبوت دفع الدين",("D43",),"negation"),
Query("Q26","إثبات أن الدين سدد بالكامل",("D44",),"negation"),
Query("Q27","تعويض نصف مليون ريال",("D45",),"numeric_precision"),
Query("Q28","تعويض خمسين ألف ريال",("D46",),"numeric_precision"),
Query("Q29","جلسة بتاريخ 18 ربيع الآخر 1448",("D47",),"date_precision"),
Query("Q30","جلسة بتاريخ 18 ربيع الآخر 1447",("D48",),"date_precision"),
Query("Q31","الحكم لا يزال قابلاً للاعتراض ولم يكتسب القطعية",("D49",),"status_contrast"),
Query("Q32","الحكم أصبح نهائياً مكتسباً للقطعية",("D50",),"status_contrast"),
]

def reciprocal_rank(ranked,relevant):
    rel=set(relevant)
    return next((1.0/i for i,x in enumerate(ranked,1) if x in rel),0.0)

def recall_at(ranked,relevant,k):
    rel=set(relevant)
    return len(set(ranked[:k]) & rel)/len(rel)

def ndcg_at(ranked,relevant,k):
    rel=set(relevant)
    dcg=sum((1/math.log2(i+1)) for i,x in enumerate(ranked[:k],1) if x in rel)
    ideal=sum((1/math.log2(i+1)) for i in range(1,min(len(rel),k)+1))
    return dcg/ideal if ideal else 0.0

def encode(model, texts, mode, is_query):
    if mode=="e5":
        prefix="query: " if is_query else "passage: "
        texts=[prefix+t for t in texts]
    return model.encode(texts,batch_size=16,normalize_embeddings=True,show_progress_bar=False,convert_to_numpy=True)

def evaluate(spec):
    t0=time.perf_counter()
    model=SentenceTransformer(spec["repo"],device="cpu")
    load_s=time.perf_counter()-t0
    docs=[d.text for d in DOCS]
    qs=[q.text for q in QUERIES]
    t1=time.perf_counter(); de=encode(model,docs,spec["mode"],False); doc_s=time.perf_counter()-t1
    t2=time.perf_counter(); qe=encode(model,qs,spec["mode"],True); query_s=time.perf_counter()-t2
    sims=qe @ de.T
    r1=[];r3=[];r5=[];mrr=[];ndcg=[];top1=[]
    by_kind={}
    failures=[]
    for i,q in enumerate(QUERIES):
        order=sims[i].argsort()[::-1]
        ranked=[DOCS[j].id for j in order]
        metrics={
            "recall1":recall_at(ranked,q.relevant,1),
            "recall3":recall_at(ranked,q.relevant,3),
            "recall5":recall_at(ranked,q.relevant,5),
            "mrr":reciprocal_rank(ranked,q.relevant),
            "ndcg5":ndcg_at(ranked,q.relevant,5),
            "top1":1.0 if ranked[0] in set(q.relevant) else 0.0,
        }
        r1.append(metrics["recall1"]);r3.append(metrics["recall3"]);r5.append(metrics["recall5"])
        mrr.append(metrics["mrr"]);ndcg.append(metrics["ndcg5"]);top1.append(metrics["top1"])
        by_kind.setdefault(q.kind,[]).append(metrics["top1"])
        if not metrics["top1"]:
            failures.append({"query_id":q.id,"query":q.text,"expected":q.relevant,"top5":ranked[:5]})
    info=model_info(spec["repo"])
    dim=int(de.shape[1])
    return {
        "name":spec["name"],"repo":spec["repo"],"revision":info.sha,"dimension":dim,
        "model_load_seconds":load_s,
        "documents_per_second":len(DOCS)/doc_s if doc_s else None,
        "queries_per_second":len(QUERIES)/query_s if query_s else None,
        "recall_at_1":statistics.mean(r1),
        "recall_at_3":statistics.mean(r3),
        "recall_at_5":statistics.mean(r5),
        "mrr":statistics.mean(mrr),
        "ndcg_at_5":statistics.mean(ndcg),
        "top1_accuracy":statistics.mean(top1),
        "top1_by_kind":{k:statistics.mean(v) for k,v in by_kind.items()},
        "failures":failures,
    }

def main():
    results=[]
    for spec in MODELS:
        print(f"=== {spec['name']} ===",flush=True)
        results.append(evaluate(spec))
    ranked=sorted(results,key=lambda x:(x["top1_accuracy"],x["mrr"],x["recall_at_5"]),reverse=True)
    out={
        "benchmark":"MIZAN-A10-Arabic-Legal-Embeddings-v1",
        "dataset_type":"synthetic_arabic_legal_style",
        "documents":len(DOCS),"queries":len(QUERIES),
        "limitations":[
            "Synthetic corpus is not a real Saudi legal Golden Dataset.",
            "Scores measure retrieval relevance labels defined in this benchmark, not legal correctness.",
            "No evidence/fact authority is created by embeddings or retrieval rank."
        ],
        "environment":{"python":platform.python_version(),"torch":torch.__version__,"device":"cpu"},
        "results":results,
        "ranking":[x["name"] for x in ranked],
        "candidate_decision":"Highest scoring model becomes A10 synthetic-baseline candidate only; real/anonymized Golden Dataset validation remains required."
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
