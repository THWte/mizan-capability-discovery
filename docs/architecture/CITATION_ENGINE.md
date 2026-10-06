# MIZAN Citation Engine v1

**Status:** Proposed — A8.

## Purpose

Create durable citations for canonical observations while preserving the distinction between **traceability** and **truth**.

Citation chain:

Citation -> Span -> Block -> Page -> DocumentVersion -> Document -> SourceArtifact -> SHA-256

## Rules

- Citation uses only MIZAN stable locators.
- Observation and Provenance must point to the cited Span.
- Document/Page/Block/Span hierarchy must be internally consistent.
- Source identity, provenance, and source record must agree on source artifact and SHA-256.
- Citation ID is deterministic from source SHA-256 + span locator + observation ID.
- A citation cannot carry evidentiary authority or fact status.
- Verification detects locator/source/citation-ID tampering.

## Non-goals

A8 does not decide whether quoted content is true, corroborated, legally admissible, relevant, or an Accepted Fact. It does not execute Docling/PaddleOCR and does not perform retrieval.
