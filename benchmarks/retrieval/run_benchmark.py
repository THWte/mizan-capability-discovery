#!/usr/bin/env python3
"""A9 MIZAN retrieval benchmark: Qdrant v1.19.1 vs pgvector v0.8.6.

The benchmark isolates retrieval-engine behavior by using the exact same
synthetic vectors, metadata, queries, ground truth, and citation IDs for
both engines. It does not benchmark embedding-model quality or legal truth.
"""
from __future__ import annotations

import json
import math
import os
import random
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import psycopg

SEED = 20261006
DIM = 32
N_DOCS = int(os.getenv("MIZAN_BENCH_DOCS", "5000"))
N_QUERIES = int(os.getenv("MIZAN_BENCH_QUERIES", "1000"))
TOPK = 10
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
PG_DSN = os.getenv("PG_DSN", "postgresql://postgres:postgres@127.0.0.1:5432/mizan")
OUT = Path(os.getenv("MIZAN_BENCH_OUT", "benchmark-results.json"))

COURTS = ("commercial", "labor", "criminal", "civil")
YEARS = (1445, 1446, 1447, 1448)


@dataclass(frozen=True)
class Item:
    id: int
    vector: tuple[float, ...]
    court: str
    year: int
    citation_id: str


@dataclass(frozen=True)
class Query:
    id: int
    vector: tuple[float, ...]
    court: str
    year: int
    truth5: tuple[int, ...]
    truth10: tuple[int, ...]


def unit(v):
    n = math.sqrt(sum(x*x for x in v))
    return tuple(x/n for x in v)


def cosine(a, b):
    return sum(x*y for x, y in zip(a, b))


def generate():
    rng = random.Random(SEED)
    items = []
    for i in range(1, N_DOCS + 1):
        court = COURTS[(i * 7) % len(COURTS)]
        year = YEARS[(i * 11) % len(YEARS)]
        base = [rng.gauss(0, 1) for _ in range(DIM)]
        # Metadata-specific signal keeps filtered neighborhoods nontrivial.
        base[(COURTS.index(court) * 3) % DIM] += 1.5
        base[(YEARS.index(year) * 5 + 1) % DIM] += 1.0
        items.append(Item(i, unit(base), court, year, f"CIT-SYN-{i:06d}"))

    queries = []
    eligible = [x for x in items if sum(1 for y in items if y.court == x.court and y.year == x.year) >= TOPK]
    for qid in range(1, N_QUERIES + 1):
        target = eligible[(qid * 37) % len(eligible)]
        noise = [rng.gauss(0, 0.03) for _ in range(DIM)]
        qv = unit([a+b for a,b in zip(target.vector, noise)])
        pool = [x for x in items if x.court == target.court and x.year == target.year]
        ranked = sorted(pool, key=lambda x: (-cosine(qv, x.vector), x.id))
        queries.append(Query(qid, qv, target.court, target.year,
                             tuple(x.id for x in ranked[:5]),
                             tuple(x.id for x in ranked[:10])))
    return items, queries


def vector_literal(v):
    return "[" + ",".join(f"{x:.9f}" for x in v) + "]"


def qrequest(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(QDRANT_URL + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def wait_qdrant():
    last = None
    for _ in range(60):
        try:
            with urllib.request.urlopen(QDRANT_URL + "/readyz", timeout=5) as resp:
                if 200 <= resp.status < 300:
                    return
        except Exception as e:
            last = e
            time.sleep(1)
    raise RuntimeError(f"Qdrant did not become ready: {last}")


def load_qdrant(items):
    wait_qdrant()
    try:
        qrequest("DELETE", "/collections/mizan_bench")
    except Exception:
        pass
    qrequest("PUT", "/collections/mizan_bench", {
        "vectors": {"size": DIM, "distance": "Cosine"},
        "hnsw_config": {"m": 16, "ef_construct": 100}
    })
    batch = []
    for x in items:
        batch.append({"id": x.id, "vector": x.vector,
                      "payload": {"court": x.court, "year": x.year,
                                  "citation_id": x.citation_id}})
        if len(batch) == 256:
            qrequest("PUT", "/collections/mizan_bench/points?wait=true", {"points": batch})
            batch = []
    if batch:
        qrequest("PUT", "/collections/mizan_bench/points?wait=true", {"points": batch})


def query_qdrant(q):
    body = {
        "query": q.vector,
        "filter": {"must": [
            {"key": "court", "match": {"value": q.court}},
            {"key": "year", "match": {"value": q.year}},
        ]},
        "limit": TOPK,
        "with_payload": True,
        "params": {"hnsw_ef": 128, "exact": False}
    }
    t0 = time.perf_counter()
    r = qrequest("POST", "/collections/mizan_bench/points/query", body)
    ms = (time.perf_counter() - t0) * 1000
    points = r["result"]["points"]
    return [(int(p["id"]), p.get("payload") or {}) for p in points], ms


def load_pgvector(items):
    with psycopg.connect(PG_DSN, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute("DROP TABLE IF EXISTS mizan_bench")
        conn.execute(f"""CREATE TABLE mizan_bench(
            id integer PRIMARY KEY,
            embedding vector({DIM}) NOT NULL,
            court text NOT NULL,
            year integer NOT NULL,
            citation_id text NOT NULL
        )""")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO mizan_bench(id, embedding, court, year, citation_id) VALUES (%s, %s::vector, %s, %s, %s)",
                [(x.id, vector_literal(x.vector), x.court, x.year, x.citation_id) for x in items]
            )
        conn.execute("CREATE INDEX mizan_bench_hnsw ON mizan_bench USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=100)")
        conn.execute("ANALYZE mizan_bench")


def query_pg(q):
    vec = vector_literal(q.vector)
    with psycopg.connect(PG_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL hnsw.ef_search = 128")
            cur.execute("SET LOCAL enable_seqscan = off")
            t0 = time.perf_counter()
            cur.execute(
                """SELECT id, citation_id, court, year
                   FROM mizan_bench
                   WHERE court=%s AND year=%s
                   ORDER BY embedding <=> %s::vector
                   LIMIT %s""",
                (q.court, q.year, vec, TOPK)
            )
            rows = cur.fetchall()
            ms = (time.perf_counter() - t0) * 1000
    return [(int(r[0]), {"citation_id": r[1], "court": r[2], "year": r[3]}) for r in rows], ms


def dcg(ids, relevant):
    total = 0.0
    rel = set(relevant)
    for i, doc_id in enumerate(ids, 1):
        if doc_id in rel:
            total += 1.0 / math.log2(i + 1)
    return total


def evaluate(engine_name, query_fn, queries, item_map):
    r5=[]; r10=[]; mrr=[]; ndcg=[]; cp1=[]; filter_ok=[]; cite_ok=[]; lat=[]
    for q in queries:
        result, ms = query_fn(q)
        ids = [x[0] for x in result]
        r5.append(len(set(ids[:5]) & set(q.truth5))/5)
        r10.append(len(set(ids[:10]) & set(q.truth10))/10)
        rel = set(q.truth10)
        rr = next((1/i for i,x in enumerate(ids,1) if x in rel), 0.0)
        mrr.append(rr)
        ideal = dcg(q.truth10, q.truth10)
        ndcg.append(dcg(ids[:10], q.truth10)/ideal if ideal else 0.0)
        cp1.append(1.0 if ids and ids[0] == q.truth10[0] else 0.0)
        filter_ok.append(1.0 if all(p.get("court")==q.court and int(p.get("year"))==q.year for _,p in result) else 0.0)
        cite_ok.append(1.0 if all(p.get("citation_id")==item_map[i].citation_id for i,p in result) else 0.0)
        lat.append(ms)
    lat_sorted=sorted(lat)
    def pct(p):
        if not lat_sorted: return None
        idx=min(len(lat_sorted)-1, max(0, math.ceil(p*len(lat_sorted))-1))
        return lat_sorted[idx]
    return {
        "engine": engine_name,
        "queries": len(queries),
        "recall_at_5": statistics.mean(r5),
        "recall_at_10": statistics.mean(r10),
        "mrr_at_10": statistics.mean(mrr),
        "ndcg_at_10": statistics.mean(ndcg),
        "citation_precision_at_1": statistics.mean(cp1),
        "metadata_filter_accuracy": statistics.mean(filter_ok),
        "citation_preservation_accuracy": statistics.mean(cite_ok),
        "latency_ms": {
            "mean": statistics.mean(lat),
            "p50": statistics.median(lat),
            "p95": pct(0.95),
            "max": max(lat),
        }
    }


def pg_size():
    with psycopg.connect(PG_DSN) as conn:
        return conn.execute("SELECT pg_total_relation_size('mizan_bench')").fetchone()[0]


def qdrant_info():
    r=qrequest("GET","/collections/mizan_bench")
    x=r.get("result",{})
    return {
        "points_count": x.get("points_count"),
        "indexed_vectors_count": x.get("indexed_vectors_count"),
        "status": x.get("status"),
        "optimizer_status": x.get("optimizer_status"),
        "storage_bytes": None,
        "storage_bytes_note": "Qdrant REST collection info does not expose directly comparable total storage bytes in this benchmark."
    }


def main():
    items,queries=generate()
    item_map={x.id:x for x in items}
    load_qdrant(items)
    load_pgvector(items)

    # Warm-up both engines outside measured query set.
    for q in queries[:20]:
        query_qdrant(q)
        query_pg(q)

    qres=evaluate("qdrant",query_qdrant,queries,item_map)
    pres=evaluate("pgvector",query_pg,queries,item_map)
    result={
        "benchmark": "MIZAN-A9-retrieval-v1",
        "seed": SEED,
        "dimension": DIM,
        "documents": N_DOCS,
        "queries": N_QUERIES,
        "topk": TOPK,
        "scope": "vector similarity + metadata filtering + citation payload preservation",
        "not_measured": ["Arabic embedding quality", "lexical/BM25 hybrid retrieval", "legal answer quality", "evidence authority"],
        "versions": {
            "qdrant_server_expected": "1.19.1",
            "pgvector_expected": "0.8.6",
            "postgres_expected": "18"
        },
        "qdrant": qres,
        "pgvector": pres,
        "storage": {"pgvector_relation_bytes": pg_size(), "qdrant": qdrant_info()},
        "decision_rule": {
            "minimum_metadata_filter_accuracy": 1.0,
            "minimum_citation_preservation_accuracy": 1.0,
            "winner": "No automatic architecture adoption. Metrics inform REUSE/EXTEND/CONNECT decision; Retrieval != Evidence Authority."
        }
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
