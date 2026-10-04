# Provenance Contract v1 (Placeholder)

**Status:** Skeleton — not yet specified. No implementation depends on this
yet.

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
  its original Source without gaps.
- How provenance records for raw vs. normalized extraction (see the Docling
  sandbox's `raw_text` / `normalized_text` precedent in
  `sandboxes/docling/adapter.py`) are to be generalized across engines.

## Status of this placeholder

This file exists only to reserve the directory and document intent, per the
IMPLEMENTATION DIRECTIVE that created it. It is **not** a working schema.
No code should depend on a schema defined here until a follow-up change
replaces this placeholder with an actual specification and a corresponding
ADR.
