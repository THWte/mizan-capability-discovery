# MIZAN Agent Society v1 — Tests

Real, passing tests against the `agents/mizan_agents/` skeleton described in
[`../../docs/architecture/AGENT_SOCIETY.md`](../../docs/architecture/AGENT_SOCIETY.md).
No test here is faked as passing; every assertion exercises real behavior
of the Handoff Contract, Governed Memory, or one of the eight agents.

## Coverage

| File | What it validates |
|---|---|
| `test_handoff_contract.py` | Handoff construction rules, including the Invariant-2 forbidden-key rejection, role/stage/status validation, and negative cases |
| `test_governed_memory.py` | Namespace-scoped writes, append-only enforcement, forbidden-value rejection, audit log ordering |
| `test_master_orchestrator.py` | Routing, the architecture-approval gate, and that `complete()` cannot be bypassed |
| `test_conversation_intelligence_agent.py` | Intent classification, raw/normalized (NFKC) text separation |
| `test_architecture_guardian_agent.py` | Each named invariant-violation check, both FAIL and PASS paths |
| `test_capability_discovery_agent.py` | Decision recording requires a real, existing evidence file; rejects unknown decisions |
| `test_evidence_provenance_agent.py` | Wraps `provenance_v1.trace_to_source_sha256`; broken chains raise `AgentContractError`, not a leaked exception type |
| `test_qa_redteam_agent.py` | Each adversarial attack's expected-vs-actual rejection outcome |
| `test_git_pr_auditor_agent.py` | Scope-ownership audit, including multi-violation and cross-scope cases |
| `test_evolution_agent.py` | Proposal recording, memory-namespace isolation, and that a proposal cannot self-adopt |
| `test_agent_society_integration.py` | An end-to-end Handoff chain across multiple agents, including a deliberately-failing path that the Architecture Guardian must reject and that must then block `MasterOrchestrator.complete()` |

## Running

```powershell
python -m pytest tests/agents -v
```

No separate virtual environment is required: `agents/mizan_agents/` and
`contracts/mizan_contracts/` are both pure stdlib.
