"""A25 — Evidence Manifest Verifier v1."""
from __future__ import annotations
import dataclasses
from .runtime_evidence_collector import RuntimeEvidenceManifest,verify_manifest_integrity
from .local_integration_contract import to_local_runtime_manifest
from .local_runtime_gate import verify_local_runtime

@dataclasses.dataclass(frozen=True,kw_only=True)
class RuntimeEvidenceVerdict:
    integrity_ok:bool
    runtime_verified:bool
    blockers:tuple[str,...]

def verify_runtime_evidence(evidence:RuntimeEvidenceManifest)->RuntimeEvidenceVerdict:
    integrity=verify_manifest_integrity(evidence)
    if not integrity:
        return RuntimeEvidenceVerdict(integrity_ok=False,runtime_verified=False,blockers=("MANIFEST_INTEGRITY_FAILED",))
    local=to_local_runtime_manifest(evidence)
    ok,blockers=verify_local_runtime(local)
    return RuntimeEvidenceVerdict(integrity_ok=True,runtime_verified=ok,blockers=blockers)
