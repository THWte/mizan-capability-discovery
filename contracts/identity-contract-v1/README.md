# Identity Contract v1

**Status:** Reference implementation exists at
[`contracts/mizan_contracts/identity_v1.py`](../mizan_contracts/identity_v1.py),
exercised by [`tests/contracts/`](../../tests/contracts/) (AC-04, AC-05,
AC-06, AC-15, AC-16). This document remains the human-readable
specification; the Python module is the normative, versioned, importable
contract.

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

## Status of this document

`contracts/mizan_contracts/identity_v1.py` now implements
`SourceArtifactIdentity` (sha256/content_fingerprint/byte_size-based file
identity), `DocumentIdentity` (`document_id` distinct from any
`source_artifact_ids`, enforced in `__post_init__`), and
`classify_duplicate_candidate()` (classifies, never auto-merges — see
Invariant 5) as real, importable, versioned (`CONTRACT_VERSION = "v1"`)
code with enforced validation, not a JSON Schema/protobuf file. See
[`tests/contracts/`](../../tests/contracts/) for the acceptance-criteria
test suite that exercises every rule above, and
[`docs/architecture/adr/`](../../docs/architecture/adr/) for the
corresponding ADR once filed.
