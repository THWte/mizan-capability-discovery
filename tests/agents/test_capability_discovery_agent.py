"""Tests for the MIZAN Agent Society v1 Capability Discovery Agent.

Evidence-doc paths used here are files that actually exist on this branch
(``main``). ``sandboxes/docling/`` and ``sandboxes/paddleocr/`` live only on
their own unmerged PR branches (PR #2, PR #5) and are intentionally never
referenced here -- this agent-society skeleton must not couple to, or
assume the existence of, content from another in-flight PR.
"""
from pathlib import Path

import pytest

from mizan_agents.capability_discovery import CapabilityDiscoveryAgent
from mizan_agents.errors import AgentContractError

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_EVIDENCE_DOC = "docs/architecture/ARCHITECTURAL_INVARIANTS.md"


def test_decision_recorded_with_real_existing_evidence_doc():
    agent = CapabilityDiscoveryAgent(repo_root=_REPO_ROOT)
    record = agent.record_decision(
        capability_name="example-capability",
        decision="CONNECT",
        evidence_doc=_REAL_EVIDENCE_DOC,
    )
    assert record.decision == "CONNECT"
    assert agent.all_records() == (record,)


def test_decision_recorded_with_roadmap_as_evidence_doc():
    agent = CapabilityDiscoveryAgent(repo_root=_REPO_ROOT)
    record = agent.record_decision(
        capability_name="another-capability",
        decision="INSPIRE",
        evidence_doc="docs/roadmap.md",
    )
    assert record.decision == "INSPIRE"


def test_decision_rejected_without_existing_evidence_file():
    agent = CapabilityDiscoveryAgent(repo_root=_REPO_ROOT)
    with pytest.raises(AgentContractError):
        agent.record_decision(
            capability_name="imaginary-engine",
            decision="REUSE",
            evidence_doc="docs/architecture/DOES_NOT_EXIST.md",
        )


def test_unknown_decision_value_rejected():
    agent = CapabilityDiscoveryAgent(repo_root=_REPO_ROOT)
    with pytest.raises(AgentContractError):
        agent.record_decision(
            capability_name="example-capability",
            decision="PROBABLY_FINE",
            evidence_doc=_REAL_EVIDENCE_DOC,
        )


def test_empty_evidence_doc_rejected():
    agent = CapabilityDiscoveryAgent(repo_root=_REPO_ROOT)
    with pytest.raises(AgentContractError):
        agent.record_decision(
            capability_name="example-capability", decision="CONNECT", evidence_doc=""
        )


def test_empty_capability_name_rejected():
    agent = CapabilityDiscoveryAgent(repo_root=_REPO_ROOT)
    with pytest.raises(AgentContractError):
        agent.record_decision(
            capability_name="", decision="CONNECT", evidence_doc=_REAL_EVIDENCE_DOC
        )


def test_multiple_decisions_accumulate_in_order():
    agent = CapabilityDiscoveryAgent(repo_root=_REPO_ROOT)
    agent.record_decision(
        capability_name="example-capability",
        decision="CONNECT",
        evidence_doc=_REAL_EVIDENCE_DOC,
    )
    agent.record_decision(
        capability_name="another-capability",
        decision="INSPIRE",
        evidence_doc="docs/roadmap.md",
    )
    names = [r.capability_name for r in agent.all_records()]
    assert names == ["example-capability", "another-capability"]
