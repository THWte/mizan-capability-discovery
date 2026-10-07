# Contributing to MIZAN Capability Discovery

## Purpose

This repository evaluates and integrates capabilities into MIZAN under strict architecture and provenance rules.

A contribution is not accepted solely because it works in isolation; it must preserve MIZAN's contracts and epistemic boundaries.

## Before making a change

Classify the work:

- `REUSE` — adopt an existing capability substantially as-is;
- `EXTEND` — add a missing capability while preserving the existing component;
- `CONNECT` — integrate two independently useful components;
- `DUAL-ENGINE` — retain multiple engines for specialization, comparison, or fallback;
- `REPLACE` — allowed only with explicit migration evidence and rollback;
- `REJECT` — unsuitable for MIZAN's requirements.

## Required discipline

1. Preserve existing architecture invariants.
2. Keep Observation, Evidence, Fact, and Accepted Fact distinct.
3. Preserve source provenance and stable locators.
4. Use synthetic or public test data only.
5. Add tests for material behavior changes.
6. Do not weaken tests or invariants merely to make an implementation pass.
7. Report unresolved limitations explicitly.
8. Avoid unrelated refactors in capability PRs.

## Pull requests

Use the repository pull-request template.

A consequential PR should describe:

- problem / capability gap;
- current reality;
- proposed change;
- architecture impact;
- test and benchmark evidence;
- public/private data boundary;
- unresolved limitations;
- rollback or non-destructive migration path where relevant.

## Commit style

Prefer focused commits with descriptive prefixes, for example:

- `architecture:`
- `contract:`
- `benchmark:`
- `agent:`
- `ci:`
- `docs:`
- `fix:`

## CI

Do not use GitHub Actions as an uncontrolled debugging loop. Reproduce locally or in a focused branch where possible, then use CI as a verification gate.

Superseded CI runs should be cancelled where appropriate, and independent workflows should use narrow path filters.

## Real case data

Real case material is prohibited in this public repository. Use synthetic fixtures that reproduce the technical structure without reproducing private facts.
