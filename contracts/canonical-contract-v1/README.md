# Canonical Contract v1

**Status:** Reference implementation exists at
[`contracts/mizan_contracts/canonical_v1.py`](../mizan_contracts/canonical_v1.py),
exercised by [`tests/contracts/`](../../tests/contracts/) (AC-01, AC-02,
AC-03, AC-10, AC-13, AC-15, AC-16, AC-17). This document remains the
human-readable specification; the Python module is the normative,
versioned, importable contract. No engine integration (Docling or
otherwise) has been changed to depend on it yet — adoption by
`sandboxes/docling/adapter.py` is a separate, future change.

## Purpose

This directory will hold the versioned specification of MIZAN's canonical
document/content contract — the shape every engine adapter (Docling,
PaddleOCR, MinerU, or future candidates) must translate its native output
into, per
[Invariant 1: MIZAN Contract Before Engine](../../docs/architecture/ARCHITECTURAL_INVARIANTS.md#1-mizan-contract-before-engine).

## Scope (to be specified in a future change)

- The canonical representation of extracted document content (text, layout,
  tables, metadata) independent of any single engine's object model.
- The explicit distinction between Observation / Evidence / Fact / Accepted
  Fact as data states within the canonical model
  ([Invariant 2](../../docs/architecture/ARCHITECTURAL_INVARIANTS.md#2-observation--evidence--fact--accepted-fact)).
- Versioning rules for how `canonical-contract-v2` etc. would supersede this
  version without breaking existing Accepted Facts.

## Status of this document

`contracts/mizan_contracts/canonical_v1.py` now implements the 10 entities
described above (`SourceArtifact`, `Document`, `DocumentVersion`, `Page`,
`Block`, `Span`, `Section`, `Table`, `TableCell`, `RawObservation`) as a
real, importable, versioned (`CONTRACT_VERSION = "v1"`) Python module with
enforced validation, not a JSON Schema/protobuf file. It deliberately
defines no Fact / Accepted Fact type (Invariant 2, Invariant 10). See
[`tests/contracts/`](../../tests/contracts/) for the acceptance-criteria
test suite that exercises every rule above, and
[`docs/architecture/adr/`](../../docs/architecture/adr/) for the
corresponding ADR once filed.
