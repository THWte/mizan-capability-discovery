# Identity Contract v1 (Placeholder)

**Status:** Skeleton — not yet specified. No implementation depends on this
yet.

## Purpose

This directory will hold the versioned specification of how MIZAN assigns
and resolves **document identity**, as distinct from file identity,
implementing:

- [Invariant 5: Document Identity ≠ File Identity](../../docs/architecture/ARCHITECTURAL_INVARIANTS.md#5-document-identity--file-identity)

## Scope (to be specified in a future change)

- How a MIZAN document identity is assigned, independent of file hash,
  filename, or MIME type.
- How multiple file representations of the same legal document are linked
  to a single document identity.
- How a single file containing multiple documents (e.g. a multi-document
  scan) is decomposed into multiple document identities.
- The relationship between this contract and
  `stable-locator-contract-v1/` (identity is the "what"; stable locators are
  the durable "how to point at it").

## Status of this placeholder

This file exists only to reserve the directory and document intent, per the
IMPLEMENTATION DIRECTIVE that created it. It is **not** a working schema.
No code should depend on a schema defined here until a follow-up change
replaces this placeholder with an actual specification and a corresponding
ADR.
