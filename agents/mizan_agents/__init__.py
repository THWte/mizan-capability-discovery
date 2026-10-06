"""
MIZAN Agent Society v1

A governed multi-agent runtime skeleton that coordinates work on top of
MIZAN's existing Core Contracts v1 (``contracts/mizan_contracts/``) and
Architectural Invariants (``docs/architecture/ARCHITECTURAL_INVARIANTS.md``).

This package defines the core society of eight agents:

- Master Orchestrator (``orchestrator.py``)
- Conversation Intelligence (``conversation_intelligence.py``)
- Architecture Guardian (``architecture_guardian.py``)
- Capability Discovery (``capability_discovery.py``)
- Evidence/Provenance (``evidence_provenance.py``)
- QA/Red-Team (``qa_redteam.py``)
- Git/PR Auditor (``git_pr_auditor.py``)
- Evolution Agent (``evolution_agent.py``)

...plus the two cross-cutting mechanisms every agent is required to use:
the Handoff Contract (``handoff_contract.py``) and Governed Memory
(``memory.py``).

Scope of v1 (see ``docs/architecture/AGENT_SOCIETY.md`` for the full
record): this package implements the governance skeleton only. It does not
call Docling, PaddleOCR, Langfuse, pgvector, or any other third-party
engine; it does not perform real git/GitHub operations; and it does not
implement MIZAN's interpretation/verification layers. Those remain future
work, gated by their own ADRs.
"""

CONTRACT_VERSION = "v1"
