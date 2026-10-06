# A14–A17 — Runtime and Production Governance v1

This bundle moves MIZAN from individually validated layers toward an auditable integrated runtime without pretending the current external providers are production-ready.

## A14 Intelligence Runtime
CONNECTS canonical document flow, citations, retrieval, knowledge and legal reasoning. It preserves case boundaries and cannot create Accepted Facts.

## A15 Golden Dataset Contract
Production evaluation requires traceable gold labels. Synthetic datasets remain valid for development but can never unlock production. Non-synthetic labels must be independently reviewed and bind expected citation IDs and Stable Locators.

## A16 Production Readiness Gate
Fail-closed gate. Current blockers include the documented Docling/PaddleOCR runtime risks plus the absence of a real/anonymized independently-reviewed Saudi legal Golden Dataset and local-runtime integration evidence. Reverse traceability and citation accuracy are hard 100% gates for production admission.

## A17 Capability Registry
Central MIZAN-owned decision memory for external providers. Discovery/benchmark results are recorded without turning a provider into system authority.

Current provider posture:
- Docling: EXTEND, sandbox candidate, NOT production.
- PaddleOCR: CONNECT, Arabic OCR specialist, NOT production.
- pgvector: EXTEND baseline candidate, NOT production.
- BGE-M3: EXTEND synthetic-baseline candidate, NOT production.

PR #2 and PR #5 remain unmerged provider sandboxes. Their evidence is consumed as registry decisions; their engine code is not pulled into MIZAN core.
