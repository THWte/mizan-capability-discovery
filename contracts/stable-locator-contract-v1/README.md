# Stable Locator Contract v1

**Status:** Reference implementation exists at
[`contracts/mizan_contracts/stable_locator_v1.py`](../mizan_contracts/stable_locator_v1.py),
exercised by [`tests/contracts/`](../../tests/contracts/) (AC-07, AC-08,
AC-09, AC-15, AC-16) and
[`tests/architecture/test_stable_locator_ownership.py`](../../tests/architecture/test_stable_locator_ownership.py).
This document remains the human-readable specification; the Python module
is the normative, versioned, importable contract. Locator survival across
an actual engine *replacement* remains untested — only one engine adapter
(Docling) exists today.

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

## Status of this document

`contracts/mizan_contracts/stable_locator_v1.py` now implements
hierarchical, MIZAN-only locator builders (`build_document_locator`,
`build_page_locator`, `build_block_locator`, `build_span_locator`),
`validate_locator_component()` (format + banned-engine-pattern checks),
`validate_hierarchy_consistency()`, and `is_external_engine_identifier()`
(rejects Docling/MinerU/Qdrant/pgvector/PaddleOCR/raw-row IDs outright) as
real, importable, versioned (`CONTRACT_VERSION = "v1"`) code, not a JSON
Schema/protobuf file. See [`tests/contracts/`](../../tests/contracts/) for
the acceptance-criteria test suite that exercises every rule above, and
[`docs/architecture/adr/`](../../docs/architecture/adr/) for the
corresponding ADR once filed.
