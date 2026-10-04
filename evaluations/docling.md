# MIZAN Project Evaluation: Docling

## Project
- Name: Docling
- Repository: https://github.com/docling-project/docling
- License: MIT
- Primary domain: Document Intelligence (PDF/Office parsing, OCR, table extraction)
- Decision: **EXTEND / CONNECT**

## 1. Capability fit
- Solves document ingestion: converts PDF, Office, and scanned documents into
  structured, machine-readable data (text, layout, tables, OCR).
- Affects MIZAN's **evidence/document intake layer** — the first stage where case
  files, memos, and official documents enter the system.
- Fills a real gap: MIZAN currently has no mature, general-purpose document parser.
- Does not duplicate existing MIZAN functionality.
- Criticality: high — nearly every case file passes through this layer.

## 2. Technical quality
- Architecture: modular pipeline (`docling-core`, `docling-serve` as FastAPI service,
  `docling-mcp`, `docling-graph`).
- ~68k GitHub stars, very active, backed by the Docling org (IBM-originated).
- Documentation: strong, with examples and API references.
- Test coverage: present in CI; production-grade adoption by multiple downstream tools.
- Maintenance: very active, frequent releases.

## 3. Security and privacy
- Can run fully local/offline — no mandatory cloud dependency.
- OCR and parsing run in-process; no data leaves the environment unless configured to.
- Dependency surface is moderate (ML models for layout/OCR); needs a dependency and
  license audit before production use with sensitive legal documents.
- Compatible with a controlled, local-first deployment.

## 4. Integration fit
- Python-native; ships a FastAPI service (`docling-serve`) — directly compatible with
  MIZAN's stack.
- Clear API surface for document conversion.
- Data model (structured document + tables + layout) should map cleanly onto a MIZAN
  "parsed evidence" model with modest adaptation.

## 5. Operational fit
- Windows support: needs verification for OCR/model dependencies (some ML backends are
  Linux-first); should be validated in sandbox.
- Local/offline: yes.
- Resource usage: moderate-to-high for OCR/layout models; plan for GPU/CPU sizing.

## 6. Language / domain fit
- Arabic support: **unverified** — OCR quality on Arabic legal documents must be
  benchmarked specifically; this is the single biggest open question.
- No legal-domain-specific NER out of the box; that remains MIZAN's responsibility.

## 7. What MIZAN should take
- PDF/Office parsing pipeline
- Document structure extraction
- OCR capability (pending Arabic benchmark)
- Table extraction
- The `docling-serve` FastAPI service pattern as an ingestion microservice

## 8. What MIZAN should ignore
- Full document-management/archival features
- Any general file-management UI
- Non-essential format support not used by MIZAN's case files

## 9. Strategic recommendation
### Decision: EXTEND / CONNECT
### Why:
Docling is not a complete solution for MIZAN, but it is an excellent base for the
document-intake layer. Use it as an ingestion/parsing service and extend it with
MIZAN-specific legal/Arabic post-processing rather than replacing it.

### Risks:
- Integration risk: medium (Windows/OCR backend verification needed)
- Security risk: low (local-first capable)
- Legal/compliance risk: medium until Arabic OCR accuracy is benchmarked on real case
  documents
- Maintenance risk: low (very active project)

### Suggested next step:
Sandbox prototype — run `docling-serve` locally against a sample of real (anonymized)
Arabic case documents and benchmark OCR/table-extraction accuracy before deciding on
EXTEND vs. REUSE.
