# A32 — Arabic OCR Accuracy & Recovery Gate

A32 measures real Arabic OCR on Windows using the exact PaddleOCR candidate versions previously isolated by PR #5:
- paddleocr 3.3.3
- paddlepaddle 3.2.2

It does not merge PR #5 and does not production-approve PaddleOCR.

## Synthetic ground truth
Fixtures contain no case data. They cover:
- clear Arabic legal-style prose;
- critical identifiers, ISO dates and decimal amounts;
- Arabic-Indic digits;
- degraded/noisy text;
- rotated text.

## Metrics
- CER (character error rate)
- WER (word error rate)
- critical-token recall for identifiers/dates/amounts
- per-fixture elapsed time
- process RSS
- page success/failure accounting

## Decision policy
Quality is reported independently from runtime success:
- PASS: aggregate CER <= 0.10, WER <= 0.25, critical-token recall >= 0.95
- CONDITIONAL: CER <= 0.30 and WER <= 0.60 and critical-token recall >= 0.70
- FAIL: otherwise

A quality FAIL is evidence, not a reason to hide the benchmark. CI fails only if the benchmark cannot execute/measure, loses fixture accounting, or recovery invariants fail.

## Recovery invariant
A deliberately corrupted image is isolated as a failed page. Subsequent valid pages must still be processed. A single page failure cannot erase prior completed work or prevent later-page recovery.

## Non-claims
A32 does not establish:
- production approval;
- table-structure understanding;
- owner-laptop performance;
- accuracy on real Saudi court scans.
