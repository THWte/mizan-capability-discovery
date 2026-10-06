import math
import importlib.util
import sys
from pathlib import Path

P=Path(__file__).resolve().parents[2]/"benchmarks"/"retrieval"/"run_benchmark.py"
spec=importlib.util.spec_from_file_location("bench",P)
b=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=b
spec.loader.exec_module(b)

def test_generation_is_deterministic_and_has_1000_queries(monkeypatch):
    monkeypatch.setattr(b,"N_DOCS",500)
    monkeypatch.setattr(b,"N_QUERIES",100)
    a1,q1=b.generate(); a2,q2=b.generate()
    assert a1==a2 and q1==q2
    assert len(q1)==100

def test_unit_vectors_and_truth_sizes(monkeypatch):
    monkeypatch.setattr(b,"N_DOCS",500)
    monkeypatch.setattr(b,"N_QUERIES",20)
    items,queries=b.generate()
    assert all(abs(sum(x*x for x in i.vector)-1)<1e-6 for i in items)
    assert all(len(q.truth5)==5 and len(q.truth10)==10 for q in queries)

def test_dcg_perfect_is_maximal():
    rel=(1,2,3,4,5)
    perfect=b.dcg(rel,rel)
    reversed_score=b.dcg(tuple(reversed(rel)),rel)
    assert perfect==reversed_score  # binary relevance: order within relevant set is not distinguished

def test_citation_ids_are_unique(monkeypatch):
    monkeypatch.setattr(b,"N_DOCS",100)
    monkeypatch.setattr(b,"N_QUERIES",10)
    items,_=b.generate()
    assert len({x.citation_id for x in items})==len(items)
