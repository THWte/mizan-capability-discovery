# MIZAN Agent Society v1

A governed multi-agent runtime skeleton. See
[`docs/architecture/AGENT_SOCIETY.md`](../docs/architecture/AGENT_SOCIETY.md)
for the full architecture record and
[`docs/architecture/adr/ADR-0002-agent-society-v1.md`](../docs/architecture/adr/ADR-0002-agent-society-v1.md)
for the decision behind it.

## What this is

Eight agent roles, a shared Handoff Contract, and a shared Governed Memory
store -- all pure Python, pure stdlib, zero third-party dependencies, zero
network calls, zero git/GitHub operations.

| Module | Role |
|---|---|
| `orchestrator.py` | Master Orchestrator -- routes Handoffs, gates task completion on an Architecture Guardian PASS |
| `conversation_intelligence.py` | Conversation Intelligence -- classifies user-directive intent (observation only) |
| `architecture_guardian.py` | Architecture Guardian -- the only agent empowered to approve a Handoff against the Architectural Invariants |
| `capability_discovery.py` | Capability Discovery -- records REUSE/EXTEND/CONNECT/INSPIRE/REJECT decisions, each required to point at a real evidence file already in this repo |
| `evidence_provenance.py` | Evidence/Provenance -- wraps `contracts/mizan_contracts/provenance_v1.py`'s reverse-traceability check; produces Evidence, never Fact |
| `qa_redteam.py` | QA/Red-Team -- deliberately attempts known-bad operations and reports whether they were actually rejected |
| `git_pr_auditor.py` | Git/PR Auditor -- audits a changed-paths list against a declared scope; performs no real git operation |
| `evolution_agent.py` | Evolution Agent -- records proposed architecture amendments; cannot adopt its own proposal |
| `handoff_contract.py` | The Handoff Contract every inter-agent exchange must use |
| `memory.py` | Governed Memory -- namespace-scoped, append-only, shared store |
| `registry.py` | The single source of truth for the eight agent-role strings |

## What this is NOT (v1 scope)

- Does not call Docling, PaddleOCR, Langfuse, pgvector, or any other
  third-party engine.
- Does not perform real git/GitHub operations (clone, push, merge, open a
  PR) -- `git_pr_auditor.py` only audits a list of path strings it is
  given.
- Does not implement MIZAN's interpretation/verification layers (Fact /
  Accepted Fact) -- those remain out of scope, same as in
  `contracts/mizan_contracts/`.
- Does not change runtime behavior of the Docling or PaddleOCR sandboxes.

## Running the tests

```powershell
python -m pytest tests/agents -v
```

No separate virtual environment is required -- this package has zero
third-party dependencies, same as `contracts/mizan_contracts/`.
