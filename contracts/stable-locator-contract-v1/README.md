# Stable Locator Contract v1 (Placeholder)

**Status:** Skeleton — not yet specified. No implementation depends on this
yet.

## Purpose

This directory will hold the versioned specification of MIZAN-owned stable
locators — durable identifiers for referencing a specific document, page,
region, or extracted item across time, independent of any engine's internal
IDs — implementing:

- [Invariant 3: MIZAN Owns Identity and Stable Locators](../../docs/architecture/ARCHITECTURAL_INVARIANTS.md#3-mizan-owns-identity-and-stable-locators)

## Scope (to be specified in a future change)

- The format and guarantees of a MIZAN stable locator (immutability,
  resolvability, independence from engine version/library upgrades).
- How engine-local, disposable identifiers (e.g. Docling `DocItem`
  references, file-offset tuples from a specific library version) are
  consumed as input to compute a stable locator, without ever being used as
  the stable locator itself.
- Backward-compatibility rules: what happens to previously-issued stable
  locators when an underlying engine is replaced or upgraded (answer, per
  Invariant 3: nothing — they must continue to resolve).

## Status of this placeholder

This file exists only to reserve the directory and document intent, per the
IMPLEMENTATION DIRECTIVE that created it. It is **not** a working schema.
No code should depend on a schema defined here until a follow-up change
replaces this placeholder with an actual specification and a corresponding
ADR.
