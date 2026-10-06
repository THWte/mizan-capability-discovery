# ADR-0006: Citation Engine v1

**Status:** Proposed
**Base:** main@4e1d5dba182a0cea836d9d05f60010449ece1698

## Decision

Introduce a MIZAN-owned Citation Engine after canonical document flow. Citations are durable traceability records anchored to MIZAN stable locators and source SHA-256.

## Critical boundary

Citation != Evidence Authority. A valid citation proves that MIZAN can return to the referenced source location and byte artifact; it does not establish factual truth or acceptance.

## Consequence

The document fabric can now produce auditable references before retrieval and reasoning are added, without delegating citation identity to an external parser, vector database, or OCR engine.
