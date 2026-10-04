# Provenance Contract v1

**Status:** Reference implementation exists at
[`contracts/mizan_contracts/provenance_v1.py`](../mizan_contracts/provenance_v1.py),
exercised by [`tests/contracts/`](../../tests/contracts/) (AC-04, AC-11,
AC-12, AC-13, AC-14, AC-15, AC-16). This document remains the
human-readable specification; the Python module is the normative,
versioned, importable contract. Structural reverse traceability
(Observation → Span → Block → Page → Source Artifact → SHA-256) is
implemented and tested; the full Accepted-Fact trace is explicitly NOT
implemented (no interpretation/verification layer exists yet) — see
`tests/architecture/test_provenance_traceability.py` for the honest SKIP.

## Purpose

This directory will hold the versioned specification of how provenance is
recorded and carried through MIZAN's pipeline, implementing:

- [Invariant 6: Evidence Resolution Does Not Create Truth](../../docs/architecture/ARCHITECTURAL_INVARIANTS.md#6-evidence-resolution-does-not-create-truth)
- [Invariant 7: Complete Reverse Traceability](../../docs/architecture/ARCHITECTURAL_INVARIANTS.md#7-complete-reverse-traceability)

## Scope (to be specified in a future change)

- The required fields for a provenance record at each pipeline stage (which
  engine, which engine version/configuration, which adapter, timestamp,
  source locator).
- The minimum information needed to walk backward from an Accepted Fact to
  its original Source Artifact without gaps, terminating at a SHA-256 content
  hash of that artifact, per
  [Invariant 7: Complete Reverse Traceability](../../docs/architecture/ARCHITECTURAL_INVARIANTS.md#7-complete-reverse-traceability).
- How provenance records for raw vs. normalized extraction (see the Docling
  sandbox's `raw_text` / `normalized_text` precedent in
  `sandboxes/docling/adapter.py`) are to be generalized across engines.

## Status of this document

`contracts/mizan_contracts/provenance_v1.py` now implements
`ProvenanceRecord` (engine, engine_version, settings, extraction_timestamp,
extraction_method, source_sha256, stable_locator, and optional
model/confidence/page/bbox fields), `SourceArtifactRecord`, and
`trace_to_source_sha256()` as real, importable, versioned
(`CONTRACT_VERSION = "v1"`) code with enforced validation — not a JSON
Schema/protobuf file. It accepts no retrieval_score/similarity/rank field
(Invariant 4, see `tests/contracts/test_ac13_*.py`). See
[`tests/contracts/`](../../tests/contracts/) for the acceptance-criteria
test suite that exercises every rule above, and
[`docs/architecture/adr/`](../../docs/architecture/adr/) for the
corresponding ADR once filed.
