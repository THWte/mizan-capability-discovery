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
| `orchestrator.py` | Master Orchestrator -- routes Handoffs, gates task completion on a digest-bound `GuardianApproval` re-verified against the live routed Handoff (v1.1) |
| `conversation_intelligence.py` | Conversation Intelligence -- classifies user-directive `intent` and (v1.1) `claim_type`/`verification_required` (observation only) |
| `architecture_guardian.py` | Architecture Guardian -- the only agent empowered to approve a Handoff against the Architectural Invariants; issues `GuardianVerdict`/`GuardianApproval` with explicit coverage (v1.1) |
| `capability_discovery.py` | Capability Discovery -- records REUSE/EXTEND/CONNECT/INSPIRE/REJECT/CONTINUE_BENCHMARKING decisions and a (v1.1) `lifecycle_status`, each required to point at a real evidence file already in this repo |
| `evidence_provenance.py` | Evidence/Provenance -- wraps `contracts/mizan_contracts/provenance_v1.py`'s reverse-traceability check; produces Evidence, never Fact |
| `qa_redteam.py` | QA/Red-Team -- deliberately attempts known-bad operations and reports whether they were actually rejected |
| `git_pr_auditor.py` | Git/PR Auditor -- audits a changed-paths list against a declared scope; performs no real git operation |
| `evolution_agent.py` | Evolution Agent -- records proposed architecture amendments; cannot adopt its own proposal; (v1.1) `PROTECTED_TARGETS` + structurally-fixed `requires_new_adr=true` |
| `handoff_contract.py` | The Handoff Contract every inter-agent exchange must use |
| `memory.py` | Governed Memory -- namespace-scoped, append-only, shared store; (v1.1) `SHARED_PRIVILEGED_PREFIXES` ACL for Architecture Guardian-only keys |
| `registry.py` | The single source of truth for the eight agent-role strings |
| `epistemic.py` (v1.1) | Shared, recursive forbidden-promoted-fact-key validator used by both the Handoff Contract and Governed Memory |
| `canonical_digest.py` (v1.1) | Deterministic canonical-JSON + SHA-256 digest helper underpinning `GuardianApproval` tamper resistance |
| `guardian_approval.py` (v1.1) | `GuardianApproval` -- the sole trusted object binding an Architecture Guardian review to a specific reviewed Handoff by content digest |

## GitHub Custom Agent profiles (`.github/agents/`, v1.1)

Eight `*.agent.md` profiles (`mizan-master`, `conversation-intelligence`,
`architecture-guardian`, `capability-discovery`, `evidence-provenance`,
`qa-redteam`, `git-pr-auditor`, `evolution`) let a human or GitHub Copilot
session invoke each role as a distinct, role-scoped custom agent. These
are a **separate runtime layer** from the Python modules in this
directory -- they are delegation/instruction surfaces, not an execution of
this package's logic, and this package does not depend on them. See
`docs/architecture/AGENT_SOCIETY.md`'s "Amendment v1.1" section for the
full two-layer explanation and data-flow diagram. There is no official
local validator for the GitHub custom-agent schema; `tests/agents/
test_github_agent_profiles.py` performs only an offline structural check.

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

No separate virtual environment is required for the agent-society Python
package itself -- it has zero third-party dependencies, same as
`contracts/mizan_contracts/`. `tests/agents/test_github_agent_profiles.py`
optionally uses PyYAML for stricter frontmatter parsing if it is already
installed in the environment, and falls back to a minimal built-in parser
if it is not; PyYAML is not a dependency of the package itself.
