"""A18 — MIZAN Local Runtime Evidence Gate v1.

Defines what counts as verified local-runtime integration. A declared runtime is
not verified merely because unit tests pass or a developer says it is running.
"""
from __future__ import annotations
import dataclasses
from enum import Enum

class RuntimeEvidenceError(ValueError): pass

class RuntimeCheckStatus(str,Enum):
    PASS="PASS"; FAIL="FAIL"; UNVERIFIED="UNVERIFIED"

@dataclasses.dataclass(frozen=True,kw_only=True)
class RuntimeCheck:
    name:str
    status:RuntimeCheckStatus
    evidence:str
    required:bool=True
    def __post_init__(self):
        if not self.name: raise RuntimeEvidenceError("runtime check name required")
        if self.status is RuntimeCheckStatus.PASS and not self.evidence:
            raise RuntimeEvidenceError("PASS requires concrete evidence")

@dataclasses.dataclass(frozen=True,kw_only=True)
class LocalRuntimeManifest:
    runtime_id:str
    os_name:str
    python_version:str
    commit_sha:str
    checks:tuple[RuntimeCheck,...]
    externally_published:bool=False

    def __post_init__(self):
        if not self.runtime_id or not self.commit_sha:
            raise RuntimeEvidenceError("runtime_id and commit_sha are required")
        if self.externally_published:
            raise RuntimeEvidenceError("local runtime evidence must not imply external publication")
        if len({c.name for c in self.checks}) != len(self.checks):
            raise RuntimeEvidenceError("duplicate runtime check names")

REQUIRED_CHECKS=(
    "api_health",
    "database_health",
    "ingest_path",
    "canonical_flow",
    "citation_round_trip",
    "retrieval_round_trip",
    "knowledge_proposal",
    "reasoning_non_authority",
    "audit_log",
)

def verify_local_runtime(manifest:LocalRuntimeManifest)->tuple[bool,tuple[str,...]]:
    by={c.name:c for c in manifest.checks}
    blockers=[]
    for name in REQUIRED_CHECKS:
        c=by.get(name)
        if c is None:
            blockers.append(f"MISSING:{name}")
        elif c.status is not RuntimeCheckStatus.PASS:
            blockers.append(f"{name}:{c.status.value}")
    return (not blockers,tuple(blockers))
