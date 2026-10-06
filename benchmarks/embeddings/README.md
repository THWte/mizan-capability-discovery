# A10 — Arabic/Legal Embedding Benchmark v1

A synthetic, reproducible first gate for local/open multilingual embedding candidates.

Candidates:
- intfloat/multilingual-e5-base (MIT; 94 languages)
- BAAI/bge-m3 (MIT; multilingual, 1024 dimensions, long-context retrieval design)
- sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (Apache-2.0; 50 languages)

The corpus is intentionally synthetic. It tests Arabic legal-style paraphrase retrieval, close hard negatives, identifiers, and monetary-value distinctions without using any real case file.

Metrics: Recall@1/3/5, MRR, nDCG@5, Top-1 accuracy, per-stress-kind Top-1, model load time, and CPU encoding throughput.

A winner here is only a **synthetic baseline candidate**. It must later pass a real/anonymized MIZAN Golden Dataset before production adoption.

Embedding similarity and retrieval rank never create Evidence, Fact, Verified Fact, or Accepted Fact.
