# A33 — Intelligent Document Ingestion & Extraction Experience

## User experience
The owner performs one action: provide a legal PDF. MIZAN hides engine complexity.

`PDF → understand pages → direct extraction first → OCR only when required → legal segmentation → structured extraction candidates → traceable document intelligence`

## Reuse
A33 extends rather than replaces:
- A27 streaming/checkpoint processing;
- A28 selective page OCR routing;
- A29 deterministic legal segmentation;
- A31 real-PDF Windows evidence.

A32 remains a provider-quality benchmark. Its current PaddleOCR quality result does not block born-digital PDFs with a usable text layer.

## Direct-text-first rule
A usable text layer must not be sent through OCR merely because the input is PDF. Image-only or ambiguous pages are the OCR candidates. If no OCR provider is available, the page is explicitly marked for human/provider review rather than silently treated as empty.

## Legal extraction
A33 emits extraction candidates for identifiers, judgment/deed numbers, dates, amounts, court/circuit cues and legal sections. Every candidate retains page number and deterministic span identity.

Extraction is not verification. A33 cannot create Accepted Fact.

## UX contract
Internal provider names and routing details are backend diagnostics. The primary experience should expose:
- document processing progress;
- pages requiring review;
- extracted structured fields;
- legal sections;
- source-page navigation.

## Gate
The Windows end-to-end gate generates an actual 24-page judgment-like Arabic PDF and requires:
- 24/24 pages processed;
- zero OCR for a fully born-digital document;
- extraction of case number, judgment number, date and amount;
- candidate-to-page/span traceability;
- zero Accepted Fact creation;
- architecture/contracts regression remains green.

No real case data is committed or uploaded.


## A33.1 — Authority Boundary & Mixed-Document Detection
A physical file is not assumed to have one authority. MIZAN classifies contiguous page ranges independently.

Initial authority classes:
- `OFFICIAL_COURT`
- `APPENDED_ANALYSIS`
- `LAWYER_MEMORANDUM`
- `ATTACHMENT`
- `USER_ADDED`
- `UNKNOWN`

A repeated court header is not sufficient to preserve court authority after an explicit official-end signal and a strong analysis-transition marker. Conversely, a quoted memorandum or the phrase “analysis of the judgment” inside the live official sequence does not demote a court page.

Authority classification is provenance metadata, not evidence resolution and not fact acceptance. Ambiguous material remains `UNKNOWN`; it is never silently promoted to official authority.

The regression fixture reproduces a 51-page mixed file synthetically: pages 1–31 are an official judgment sequence and pages 32–51 are an appended analysis that deliberately retains an official-looking header. No real case content is stored in the repository.
