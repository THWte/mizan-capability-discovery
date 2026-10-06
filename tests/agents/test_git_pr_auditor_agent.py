"""Tests for the MIZAN Agent Society v1 Git/PR Auditor Agent."""
import pytest

from mizan_agents.errors import AgentContractError
from mizan_agents.git_pr_auditor import GitPRAuditorAgent, AuditReport


def test_correct_declared_scope_passes():
    agent = GitPRAuditorAgent()
    report = agent.audit(
        changed_paths=("contracts/mizan_contracts/canonical_v1.py",),
        declared_scope="core_contracts",
    )
    assert report.verdict == "PASS"
    assert report.violations == ()


def test_unrelated_path_passes_regardless_of_declared_scope():
    agent = GitPRAuditorAgent()
    report = agent.audit(
        changed_paths=("agents/mizan_agents/orchestrator.py",),
        declared_scope="agent_society",
    )
    assert report.verdict == "PASS"


def test_single_scope_violation_fails():
    agent = GitPRAuditorAgent()
    report = agent.audit(
        changed_paths=("sandboxes/docling/adapter.py",),
        declared_scope="agent_society",
    )
    assert report.verdict == "FAIL"
    assert len(report.violations) == 1


def test_multiple_scope_violations_all_reported():
    agent = GitPRAuditorAgent()
    report = agent.audit(
        changed_paths=(
            "sandboxes/docling/adapter.py",
            "sandboxes/paddleocr/bridge.py",
            "agents/mizan_agents/orchestrator.py",
        ),
        declared_scope="agent_society",
    )
    assert report.verdict == "FAIL"
    assert len(report.violations) == 2


def test_windows_backslash_paths_are_normalized():
    agent = GitPRAuditorAgent()
    report = agent.audit(
        changed_paths=("sandboxes\\docling\\adapter.py",),
        declared_scope="agent_society",
    )
    assert report.verdict == "FAIL"


def test_pass_verdict_cannot_carry_violations_structurally():
    with pytest.raises(AgentContractError):
        AuditReport(verdict="PASS", violations=("bogus",))


def test_fail_verdict_requires_violations_structurally():
    with pytest.raises(AgentContractError):
        AuditReport(verdict="FAIL")
