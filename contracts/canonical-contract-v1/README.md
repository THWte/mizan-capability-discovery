# Canonical Contract v1 (Placeholder)

**Status:** Skeleton — not yet specified. No implementation depends on this
yet.

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

## Status of this placeholder

This file exists only to reserve the directory and document intent, per the
IMPLEMENTATION DIRECTIVE that created it. It is **not** a working schema.
No code should depend on a schema defined here until a follow-up change
replaces this placeholder with an actual specification (JSON Schema,
protobuf, or equivalent) and a corresponding ADR.
