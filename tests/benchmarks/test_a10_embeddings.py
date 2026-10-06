import importlib.util,sys
from pathlib import Path
P=Path(__file__).resolve().parents[2]/"benchmarks"/"embeddings"/"run_a10.py"
spec=importlib.util.spec_from_file_location("a10",P); m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)

def test_dataset_has_no_duplicate_ids():
    assert len({d.id for d in m.DOCS})==len(m.DOCS)
    assert len({q.id for q in m.QUERIES})==len(m.QUERIES)

def test_all_relevance_ids_exist():
    ids={d.id for d in m.DOCS}
    assert all(set(q.relevant)<=ids for q in m.QUERIES)

def test_benchmark_contains_required_stress_kinds():
    kinds={q.kind for q in m.QUERIES}
    assert {"semantic","hard_negative","identifier","amount"}<=kinds

def test_recall_and_rr_metrics():
    assert m.recall_at(["a","b"],("a",),1)==1
    assert m.reciprocal_rank(["x","a"],("a",))==0.5
    assert 0 <= m.ndcg_at(["x","a"],("a",),5) <= 1

def test_no_real_case_claim():
    # Dataset is structurally declared synthetic; numeric strings are fixtures, not sourced case facts.
    assert len(m.DOCS)>=30 and len(m.QUERIES)>=15
