from pathlib import Path
import importlib.util

P=Path("benchmarks/ocr_a32/run_a32.py")
spec=importlib.util.spec_from_file_location("a32",P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_metric_identity():
    s="رقم الصك ٣٥١٩٩٢٨٤٧ التاريخ ١٤٤٨-٠٤-١٨"
    assert m.cer(s,s)==0
    assert m.wer(s,s)==0
    assert m.critical_recall(s,s)==1

def test_arabic_indic_digits_compare_equal_to_latin():
    a="رقم القضية ٤٨٧٠٢٣٦٤٢١"
    b="رقم القضية 4870236421"
    assert m.cer(a,b)==0
    assert m.critical_recall(a,b)==1

def test_quality_classification_can_fail_without_harness_failure():
    rows=[
      {"name":"clear","expected_failure":False,"cer":0.01,"wer":0.05,"critical_recall":1.0},
      {"name":"numeric","expected_failure":False,"cer":0.50,"wer":0.80,"critical_recall":0.2},
      {"name":"arabic_indic","expected_failure":False,"cer":0.50,"wer":0.80,"critical_recall":0.2},
      {"name":"rotated","expected_failure":False,"cer":0.10,"wer":0.20,"critical_recall":1.0},
      {"name":"low_quality","expected_failure":False,"cer":0.80,"wer":0.95,"critical_recall":0.0},
    ]
    assert m.classify(rows)=="FAIL"
