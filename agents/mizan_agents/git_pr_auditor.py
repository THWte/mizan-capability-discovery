"""
MIZAN Agent Society v1 - Git/PR Auditor Agent

Audits a proposed set of changed file paths against a declared scope,
without performing any git/GitHub operation itself -- it never clones,
pushes, merges, or opens a PR (see ``docs/architecture/AGENT_SOCIETY.md``).
Pure and deterministic: fully testable without a git repository, CLI, or
network access.

This generalizes the scope-discipline that was, until now, enforced only
manually across this project's history (e.g. "do not touch PR #2 while
working on A4") into a checkable, repeatable gate any agent or human
operator can invoke before pushing.
"""
from __future__ import annotations

import dataclasses

from .errors import AgentContractError

# Paths that belong to a specific, already-gated sandbox or contracts
# package. A changeset that touches these without a matching
# `declared_scope` is flagged.
SCOPE_OWNED_PATHS = {
    "sandboxes/docling/": "docling_sandbox",
    "sandboxes/paddleocr/": "paddleocr_sandbox",
    "contracts/mizan_contracts/": "core_contracts",
}


@dataclasses.dataclass(frozen=True, kw_only=True)
class AuditReport:
    verdict: str  # "PASS" | "FAIL"
    violations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.verdict not in ("PASS", "FAIL"):
            raise AgentContractError(f"Unknown verdict: {self.verdict!r}.")
        if self.verdict == "FAIL" and not self.violations:
            raise AgentContractError("A FAIL verdict must carry at least one violation.")
        if self.verdict == "PASS" and self.violations:
            raise AgentContractError("A PASS verdict cannot carry violations.")


class GitPRAuditorAgent:
    def audit(self, changed_paths: tuple[str, ...], declared_scope: str) -> AuditReport:
        violations: list[str] = []
        for path in changed_paths:
            normalized = path.replace("\\", "/")
            for owned_prefix, owner in SCOPE_OWNED_PATHS.items():
                if normalized.startswith(owned_prefix) and owner != declared_scope:
                    violations.append(
                        f"{path!r} belongs to scope {owner!r}, but declared_scope "
                        f"is {declared_scope!r}."
                    )
        verdict = "FAIL" if violations else "PASS"
        return AuditReport(verdict=verdict, violations=tuple(violations))
