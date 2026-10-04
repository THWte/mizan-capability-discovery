# Architecture Validation Tests

**Status:** Mixed — real, passing tests where `contracts/mizan_contracts/`
(the A1/A2 Core Contracts) now provides a reference implementation; `skip`
with an explicit reason everywhere a dependency genuinely does not exist
yet (MIZAN's interpretation/verification layers, a second engine adapter, a
retrieval engine integration). No test here is faked as passing, and no
failing test is deleted to hide a gap.

## Why some tests are still skipped, not deleted or fabricated as green

Per
[Invariant 8: Reproducibility Before Optimization](../../docs/architecture/ARCHITECTURAL_INVARIANTS.md#8-reproducibility-before-optimization)
and the general project convention established in `sandboxes/docling/`
(never hide a gap behind a workaround just to get a PASS), a test that has
nothing real to validate yet must say so explicitly (`skip` with a reason),
not be omitted or stubbed to always pass.

## Current coverage

| File | Real assertion | Still SKIP (and why) |
|---|---|---|
| `test_stable_locator_ownership.py` | Stable locators are MIZAN-owned, engine-native IDs are rejected (`contracts/mizan_contracts/stable_locator_v1.py`) | Locator survival across an *engine replacement* — only one engine adapter (Docling) exists |
| `test_provenance_traceability.py` | Structural reverse trace Observation→Span→Block→Page→Source Artifact→SHA-256 has no gaps (`contracts/mizan_contracts/provenance_v1.py`) | Full **Accepted Fact** chain, and evidence-resolution-vs-verification distinction — Candidate Fact/Verification/Accepted Fact layers do not exist yet |
| `test_retrieval_is_not_evidence_authority.py` | Neither canonical nor provenance contract accepts a retrieval_score/similarity/rank field at all | A live retrieval engine's output being tested against a verification check — no retrieval engine integrated yet |
| `test_observation_cannot_become_accepted_fact.py` | No Fact/AcceptedFact/CandidateFact type or promotion method exists anywhere in `canonical_v1` | Explicit promotion-requires-verification-call test — verification layer does not exist yet |

See `tests/contracts/` for the full A1/A2 Core Contracts acceptance-criteria
suite (AC-01..AC-17), which is where most of the real contract behavior is
exercised in depth; this directory focuses on mapping that behavior back to
each named Architectural Invariant.

## Running

```powershell
python -m pip install pytest
python -m pytest tests/architecture tests/contracts -v
```

Expected result today: a mix of **pass** (where the dependency now exists)
and **skip** (where it genuinely does not yet) — never fail, never a faked
pass. A future change should replace each remaining `pytest.skip(...)` with
a real assertion once its dependency exists (MIZAN interpretation/
verification layers, a second engine adapter, a retrieval engine
integration), and update this table accordingly.
