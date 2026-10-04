# MIZAN Architectural Invariants

**Status:** Normative — Architecture Constraints, not Recommendations
**Applies to:** MIZAN Arabic Legal Document Intelligence Fabric — all engines,
adapters, sandboxes, and integrations, present and future.
**Precedence:** This document outranks any individual capability evaluation,
sandbox result, or engine recommendation. A capability (Docling, PaddleOCR,
MinerU, or any future candidate) MAY be adopted, extended, or rejected — but
it MAY NOT override, bypass, or silently violate any invariant below. Any
proposed design that conflicts with an invariant is non-compliant by
definition, regardless of how well the underlying engine performs.

This document exists so that engine selection happens **inside** a fixed set
of architectural constraints, not the other way around. See
[`docs/architecture/adr/ADR-0001-architectural-invariants.md`](adr/ADR-0001-architectural-invariants.md)
for the decision record behind this document, and the `contracts/` directory
for the versioned contracts that implement these invariants concretely.

---

## 1. MIZAN Contract Before Engine

MIZAN defines the data contracts (shapes, fields, guarantees) that every
ingestion/extraction/retrieval engine must satisfy. No engine's native output
format, object model, or API shape is allowed to become MIZAN's contract by
default or by convenience. Every third-party engine sits behind an adapter
that translates the engine's native output into a MIZAN-owned contract
(see `contracts/canonical-contract-v1/`).

**Consequence:** Adopting a new engine never requires changing MIZAN's
contracts. If an engine cannot be mapped onto an existing contract without
weakening it, that is evidence against adopting the engine as-is — not a
reason to change the contract to fit the engine.

## 2. Observation ≠ Evidence ≠ Fact ≠ Accepted Fact

Four distinct states must never be collapsed into one another implicitly:

| Stage | Definition | Who may produce it |
|---|---|---|
| **Observation** | Raw output of an engine (OCR text, parsed layout, detected table) — unverified, uninterpreted | Any adapter/engine |
| **Evidence** | An observation that has been linked to a specific, resolvable source location and preserved with provenance | Adapter + MIZAN provenance layer |
| **Fact** | An interpretation derived from evidence, not yet verified against MIZAN's verification rules | MIZAN interpretation layer only |
| **Accepted Fact** | A fact that has passed MIZAN's verification process and is authorized for downstream legal/business use | MIZAN verification layer only |

**No engine, adapter, or sandbox may promote an Observation directly to a
Fact or an Accepted Fact.** This mirrors and generalizes the
`SOURCE → RAW EXTRACTION → NORMALIZATION → INTERPRETATION → VERIFICATION →
ACCEPTED FACT` pipeline established in the Docling sandbox
(`sandboxes/docling/adapter.py`) — that pipeline is a specific instance of
this invariant, not the other way around.

## 3. MIZAN Owns Identity and Stable Locators

Document identity and stable locators (the durable identifiers used to
reference a specific document, page, region, or extracted item across time)
are assigned and owned by MIZAN, never by an external engine or file system
path. An engine's internal IDs (Docling `DocItem` references, file hashes,
page/offset tuples from a specific library version, etc.) are treated as
**engine-local, disposable identifiers** that MIZAN may consume as input to
compute its own stable locator, but never as the stable locator itself.

**Consequence:** If an engine is replaced, upgraded, or changes its internal
ID scheme, no previously-issued MIZAN stable locator may change or break.
See `contracts/stable-locator-contract-v1/`.

## 4. Retrieval ≠ Evidence Authority

A retrieval system (vector search, hybrid search, keyword search, graph
traversal) ranks and surfaces candidates for relevance. It is never, by
itself, authoritative evidence that a retrieved item is correct, complete,
or verified. Retrieval score, rank, or similarity is not a substitute for
provenance-checked evidence, and no component may treat "was retrieved" as
equivalent to "is evidence."

**Consequence:** Any future retrieval engine (pgvector, Haystack, or other
candidates in `evaluations/`) is evaluated as a ranking/surfacing capability
only. It must sit behind the same evidence-resolution boundary as any other
engine and must never be wired to write directly into a fact or accepted-fact
store.

## 5. Document Identity ≠ File Identity

A "document" in MIZAN's domain sense (a legal instrument, a filing, a
contract) is a durable, meaningful unit that can have multiple file
representations (a scanned PDF and a re-typed DOCX of the same legal
document are the same *document* but different *files*), and a single file
can contain multiple documents (a multi-document scan). File-level identity
(hash, filename, MIME type) is necessary metadata but must never be conflated
with document-level identity. Document identity is assigned and resolved by
MIZAN's identity layer, informed by — but not dictated by — file-level
signals.

## 6. Evidence Resolution Does Not Create Truth

Resolving a claim to its supporting evidence (finding the paragraph, table
cell, or OCR span that backs an assertion) is a necessary step toward
verification, but completing that resolution does not itself make the claim
true. Evidence resolution produces a traceable link; verification produces
truth-status. These are separate operations performed by separate layers,
and no component may treat "evidence was found and resolved" as equivalent
to "claim is verified."

## 7. Complete Reverse Traceability

Every Accepted Fact must be traceable backward, without gaps, through Fact →
Evidence → Raw Extraction → Source, including which engine, which engine
version/configuration (e.g. OCR language setting, model version), and which
adapter produced each intermediate stage. If reverse traceability cannot be
completed for a given item, that item cannot be an Accepted Fact, regardless
of how confident any downstream interpretation step is.

**The chain must terminate at a fixed, content-addressable Source Artifact,
not an abstract or mutable reference.** A file path, filename, or engine-local
reference alone is not a valid terminus: it can be overwritten, moved, or
re-ingested with different bytes without detection. The terminal Source
record must include a cryptographic content hash (SHA-256) of the source
artifact as it existed at extraction time, so that the chain anchors to
specific, verifiable bytes, not merely to a named location.

**Consequence:** Every adapter must preserve raw, unmodified engine output
(see the Docling sandbox's `raw_text` field as a concrete precedent) and
every transformation must be attributable to a specific, identifiable
processing step, ultimately resolving to a SHA-256-identified Source
Artifact.

## 8. Reproducibility Before Optimization

A capability is not considered validated until its output has been shown to
be reproducible (same input → same or explainably-bounded output across
repeated runs) under realistic conditions. Performance optimization,
caching, or scaling work on a capability is not permitted to begin before
its basic reproducibility has been measured and documented — optimizing an
unreproducible pipeline only hides the instability faster.

## 9. Capability First, Technology Second

Evaluation and architecture decisions are driven by the capability gap being
filled (document intelligence, provenance, identity resolution, retrieval,
etc.), not by enthusiasm for a specific technology. A technology is adopted
because it demonstrably closes a defined capability gap under MIZAN's actual
constraints (Arabic-language correctness, Windows/local-first operation,
privacy, measured quality) — never merely because it is popular, trending,
or already partially integrated.

## 10. No Engine Becomes the System

No single third-party engine, library, or framework is allowed to become
architecturally load-bearing for MIZAN as a whole. Every engine is replaceable
behind its adapter boundary (Invariant 1) without requiring changes to
MIZAN's contracts, identity scheme, or provenance model. If removing or
replacing an engine would require rewriting MIZAN's core contracts rather
than just its adapter, that engine has already become "the system" and the
integration is non-compliant with this invariant.

---

## Relationship to existing sandbox work

The Docling sandbox (`sandboxes/docling/`) is the first concrete, tested
precedent for several of these invariants (notably #1, #2, #3, and #7), and
its `COMPARISON_AND_DECISION.md` already identifies open questions (e.g.
"NEEDS COMPARISON WITH CURRENT MIZAN INGESTION") that these invariants are
designed to resolve systematically rather than case-by-case. Any Gate
re-evaluation of Docling, PaddleOCR, MinerU, or other candidates must be
checked explicitly against each invariant in this document, not evaluated
only against its own internal benchmark results.

## Enforcement

- New architecture proposals, ADRs, and capability evaluations must state
  explicitly which invariants they satisfy and how.
- Automated validation placeholders exist under `tests/architecture/` (see
  that directory's README for current coverage and known gaps) to begin
  converting these invariants into checkable constraints over time.
- This document is itself subject to amendment only via a new ADR that
  explicitly supersedes or amends specific sections — it is not edited
  silently.
