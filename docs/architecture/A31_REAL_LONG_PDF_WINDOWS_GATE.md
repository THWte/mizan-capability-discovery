# A31 — Real Long-PDF Windows Gate v1

A31 closes the gap between A30's synthetic million-word orchestration test and real PDF decoding.

## CI environment
GitHub Actions `windows-latest`.

## Real generated fixtures
No case data is used.
1. 100-page Arabic born-digital PDF.
2. 100-page mixed PDF in which every tenth page is rasterized into an image-only PDF page.

The fixtures are actual PDF files generated during CI, not strings pretending to be PDFs.

## Gate
For each fixture A31 verifies:
- exact page count;
- no silent page loss;
- streaming completion order;
- integrity-bound checkpoint/resume with zero completed-page reprocessing;
- born-digital text-layer detection;
- image-only page detection as OCR candidates;
- peak RSS below a configurable ceiling;
- file SHA-256 recorded in the benchmark result.

## Explicit non-claims
A31 does NOT certify:
- PaddleOCR or Docling for production;
- OCR character accuracy;
- performance on the owner's laptop;
- legal-semantic correctness of extracted text.

Those require provider-specific and local-runtime evidence.

## Acceptance
Digital PDF: 100 pages, zero OCR candidates.
Mixed PDF: 100 pages, exactly 10 OCR candidates.
Both: zero silent loss, zero resume reprocessing, RSS within gate.
Architecture/contracts regression must remain green.
