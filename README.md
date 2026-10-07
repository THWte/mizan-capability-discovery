# MIZAN Capability Discovery

[![A27-A30 Long Documents](https://github.com/THWte/mizan-capability-discovery/actions/workflows/a27-a30-long-documents.yml/badge.svg)](https://github.com/THWte/mizan-capability-discovery/actions/workflows/a27-a30-long-documents.yml)
[![A31 Real Long PDF Windows Gate](https://github.com/THWte/mizan-capability-discovery/actions/workflows/a31-real-long-pdf-windows.yml/badge.svg)](https://github.com/THWte/mizan-capability-discovery/actions/workflows/a31-real-long-pdf-windows.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**MIZAN Capability Discovery** is the public architecture, evaluation, and integration-governance repository for MIZAN: a legal-intelligence platform designed around provenance, evidence discipline, long-document processing, retrieval, reasoning, and governed agent workflows.

> **Public repository boundary:** this repository contains architecture, contracts, synthetic fixtures, benchmarks, and tests. It must not contain real case files, personal data, credentials, private local databases, or confidential runtime logs.

## Why this repository exists

MIZAN does not adopt an engine merely because it is popular or technically impressive. A capability is evaluated against explicit architectural constraints, benchmarked where possible, and assigned a deliberate integration decision such as:

`REUSE / EXTEND / CONNECT / DUAL-ENGINE / REPLACE / REJECT`

The core principle is:

> **Extraction is not evidence. Verification is not admission. Retrieval is not authority. Simulation is not fact.**

## Current status

This repository is an **active research-and-architecture program**, not a production distribution of the full private MIZAN runtime.

The merged baseline on `main` includes:

- architectural invariants and versioned contracts;
- agent-society governance and approval controls;
- document capability routing;
- evidence-resolution foundations;
- canonical document flow;
- legal citation architecture;
- retrieval and embedding benchmarks;
- hybrid retrieval fabric;
- knowledge and reasoning foundations;
- runtime/release gates;
- long-document streaming and checkpointing;
- selective OCR routing;
- hierarchical Arabic legal segmentation;
- real 100-page PDF processing on Windows CI.

See [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for the current merged baseline and intentionally unresolved areas.

## Architectural invariants

MIZAN integrations are constrained by [ARCHITECTURAL_INVARIANTS.md](docs/architecture/ARCHITECTURAL_INVARIANTS.md). Among the most important:

- `Observation != Evidence != Fact != Accepted Fact`
- `Retrieval != Evidence Authority`
- `Document Identity != File Identity`
- stable locators are owned by MIZAN, not by extraction/retrieval engines;
- source provenance must remain traceable back to a source artifact and SHA-256;
- cross-case linking must never silently import a fact into another case.

## Capability pipeline

```text
SOURCE
  -> Identity
  -> Routing
  -> Extraction Candidate
  -> Raw Observation
  -> Evidence Resolution
  -> Canonical Flow
  -> Citation
  -> Retrieval
  -> Knowledge
  -> Candidate Fact
  -> Verification
  -> Legal Reasoning
  -> Governed Runtime
```

For large documents, MIZAN adds:

```text
PDF
  -> Page Census
  -> Direct Text / Selective OCR
  -> Page-Level Checkpointing
  -> Legal Segmentation
  -> Traceable Spans
  -> Retrieval / Citation
```

## Repository structure

| Path | Purpose |
|---|---|
| `contracts/` | Versioned architecture and data contracts |
| `docs/architecture/` | Normative architecture documents and ADRs |
| `docs/architecture/adr/` | Architecture Decision Records |
| `agents/` | Governed MIZAN agent components |
| `.github/agents/` | GitHub agent profiles |
| `benchmarks/` | Reproducible capability benchmarks |
| `evaluations/` | Capability/project evaluations |
| `research/` | Research notes and comparative analysis |
| `tests/architecture/` | Architectural invariant tests |
| `tests/contracts/` | Contract acceptance tests |
| `.github/workflows/` | CI gates and benchmark workflows |

## Public / private boundary

### Safe for this repository

- architecture documents;
- contracts and schemas;
- synthetic fixtures;
- benchmark harnesses and non-sensitive results;
- test code;
- public-source capability research.

### Never commit here

- real court judgments or case files belonging to the owner;
- national IDs, IBANs, phone numbers, addresses, or other personal data;
- private MIZAN databases or case memory;
- API keys, secrets, tokens, cookies, or credentials;
- local runtime logs containing case content;
- confidential client or litigation material.

See [SECURITY.md](SECURITY.md).

## Development discipline

Material changes should normally follow:

```text
DISCOVER -> MODEL -> CONTRACT -> TEST -> BENCHMARK -> REVIEW -> MERGE
```

A green unit test is not sufficient for a consequential capability. Runtime behavior, failure modes, provenance, and architecture regressions must also be considered.

## Contributing

This repository currently represents an owner-directed R&D program. Contributions and experimental branches should follow [CONTRIBUTING.md](CONTRIBUTING.md), preserve the architecture invariants, and use the provided pull-request template.

## Security

If you discover exposed credentials, personal data, unsafe provenance handling, or a path that could promote unverified model output into trusted case knowledge, follow [SECURITY.md](SECURITY.md) and avoid publishing sensitive details in a public issue.

## License

Released under the [MIT License](LICENSE).

---

**MIZAN** — one user-facing intelligence, many independently testable engines, one governed case context.
