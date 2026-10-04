# MIZAN Project Evaluation: Paperless-ngx

## Project
- Name: Paperless-ngx
- Repository: https://github.com/paperless-ngx/paperless-ngx
- License: GPL-3.0
- Primary domain: Document management (ingestion, archive, tagging, search)
- Decision: **INSPIRE / CONNECT (reference only, do not adopt as core)**

## 1. Capability fit
- A mature, full document management system: scanning ingestion, OCR, tagging,
  archiving, and search.
- Overlaps with MIZAN's document intake needs, but as a *complete end-user product*,
  not as an embeddable capability — adopting it wholesale would turn MIZAN into a
  "Paperless clone" rather than a legal-intelligence platform.
- The project itself documents caution around storing sensitive documents in
  untrusted environments, which is directly relevant to MIZAN's legal-document
  sensitivity.

## 2. Technical quality
- Large, active community-supported project; solid architecture for its stated
  purpose (Django + consumer pipeline).
- GPL-3.0 license has copyleft implications that must be reviewed before any code
  reuse (not just "inspiration").

## 3. Security and privacy
- Self-hostable, but its own documentation flags risks of storing sensitive documents
  on less-trusted infrastructure — a useful cautionary reference for MIZAN's own
  threat model.

## 4. Integration fit
- Not designed to be embedded as a library; it is a standalone application.
- Direct code reuse is legally constrained by GPL-3.0.

## 5. Operational fit
- Full application stack (web UI, consumer, database) — heavier than what MIZAN needs
  for a single ingestion layer.

## 6. Language / domain fit
- General-purpose; no legal-domain or Arabic-specific features.

## 7. What MIZAN should take
- Ingestion pipeline design (watch folder → OCR → classify → tag → index)
- Tagging/metadata taxonomy ideas
- Lessons from its documented security caveats around sensitive-document storage

## 8. What MIZAN should ignore
- The application/UI layer entirely
- Any direct code reuse without a GPL-3.0 compliance review
- Using it as the core system "as-is"

## 9. Strategic recommendation
### Decision: INSPIRE / CONNECT
### Why:
Valuable as an architectural and security reference for the ingestion/archival design
problem, but not suitable for direct adoption given its license and its identity as a
complete end-user product rather than an embeddable layer.

### Risks:
- Legal/compliance risk: medium (GPL-3.0 — any direct code use requires careful review)
- Integration risk: high if treated as embeddable (it isn't)

### Suggested next step:
Internal evaluation only: document the ingestion/tagging architecture ideas worth
borrowing; no code reuse without a licensing review.
