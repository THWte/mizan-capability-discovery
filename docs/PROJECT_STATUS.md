# MIZAN Capability Discovery — Project Status

This file describes the **merged public baseline**. It is intentionally conservative: experimental pull requests are not listed as complete until they are merged.

## Repository role

`mizan-capability-discovery` is the public capability-discovery, architecture, contract, benchmark, and governance repository for MIZAN.

It is **not** the private case store and is **not** the complete local production runtime.

## Merged baseline

| Area | State |
|---|---|
| Architectural invariants | MERGED |
| Canonical / Provenance / Identity / Stable Locator contracts | MERGED |
| Agent Society governance | MERGED |
| Document capability routing | MERGED |
| Evidence-resolution foundation | MERGED |
| Canonical document flow | MERGED |
| Citation engine architecture | MERGED |
| Retrieval benchmarks | MERGED |
| Arabic legal embedding benchmark | MERGED |
| Hybrid retrieval fabric | MERGED |
| Knowledge / legal reasoning foundations | MERGED |
| Intelligence runtime / production-readiness gates | MERGED |
| Capability registry | MERGED |
| Local runtime evidence contracts | MERGED |
| Long-document streaming / checkpointing | MERGED |
| Selective OCR routing | MERGED |
| Hierarchical Arabic legal segmentation | MERGED |
| Million-word synthetic stress gate | MERGED |
| Real 100-page PDF Windows gate | MERGED |

## Intentionally unresolved / not production-approved

The following must not be overclaimed:

- OCR-provider production approval remains provider-specific and evidence-driven.
- A passing PDF orchestration benchmark does not prove OCR accuracy.
- Public CI does not prove performance on the owner's local Windows hardware.
- A retrieval result is not evidence authority.
- Model-generated reasoning, simulation, or extraction is not an Accepted Fact.
- The private MIZAN runtime and real case data are outside this public repository.

## Current development rule

New capabilities should preserve:

1. cumulative construction rather than destructive replacement;
2. explicit provenance and epistemic state;
3. architecture regression tests;
4. synthetic/public test data only;
5. a clear separation between current reality, target capability, and unresolved gap.

## Status vocabulary

- **MERGED** — present on `main`.
- **CANDIDATE** — implemented or benchmarked on a branch/PR, not yet part of the merged baseline.
- **CONDITIONAL PASS** — useful capability with explicit blockers or restrictions.
- **PRODUCTION APPROVED** — requires stronger runtime and operational evidence; do not infer this from a sandbox or CI benchmark.
- **UNRESOLVED** — insufficient evidence; must not be silently upgraded.
