"""
MIZAN Agent Society v1 - Agent Role Registry

A single source of truth for the eight agent roles so that the Handoff
Contract, Governed Memory, and the Master Orchestrator all validate
``from_agent``/``to_agent``/``written_by`` against the same list. No
module outside this file may invent a new agent-role string literal.
"""
from __future__ import annotations

MASTER_ORCHESTRATOR = "master_orchestrator"
CONVERSATION_INTELLIGENCE = "conversation_intelligence"
ARCHITECTURE_GUARDIAN = "architecture_guardian"
CAPABILITY_DISCOVERY = "capability_discovery"
EVIDENCE_PROVENANCE = "evidence_provenance"
QA_RED_TEAM = "qa_red_team"
GIT_PR_AUDITOR = "git_pr_auditor"
EVOLUTION_AGENT = "evolution_agent"

KNOWN_AGENT_ROLES = (
    MASTER_ORCHESTRATOR,
    CONVERSATION_INTELLIGENCE,
    ARCHITECTURE_GUARDIAN,
    CAPABILITY_DISCOVERY,
    EVIDENCE_PROVENANCE,
    QA_RED_TEAM,
    GIT_PR_AUDITOR,
    EVOLUTION_AGENT,
)
