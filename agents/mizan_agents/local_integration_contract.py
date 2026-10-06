"""A24 — Local Integration Contract v1.

Maps collector evidence into the existing LocalRuntimeManifest contract without
inventing unobserved checks.
"""
from __future__ import annotations
from .runtime_evidence_collector import RuntimeEvidenceManifest,EvidenceStatus,verify_manifest_integrity
from .local_runtime_gate import LocalRuntimeManifest,RuntimeCheck,RuntimeCheckStatus,REQUIRED_CHECKS

class LocalIntegrationError(ValueError): pass

def to_local_runtime_manifest(evidence:RuntimeEvidenceManifest)->LocalRuntimeManifest:
    if not verify_manifest_integrity(evidence):
        raise LocalIntegrationError("runtime evidence manifest integrity check failed")
    by={x.name:x for x in evidence.checks}
    checks=[]
    for name in REQUIRED_CHECKS:
        x=by.get(name)
        if x is None:
            checks.append(RuntimeCheck(name=name,status=RuntimeCheckStatus.UNVERIFIED,evidence=""))
        else:
            status={
                EvidenceStatus.PASS:RuntimeCheckStatus.PASS,
                EvidenceStatus.FAIL:RuntimeCheckStatus.FAIL,
                EvidenceStatus.UNVERIFIED:RuntimeCheckStatus.UNVERIFIED,
            }[x.status]
            checks.append(RuntimeCheck(name=name,status=status,evidence=x.evidence if status is RuntimeCheckStatus.PASS else x.evidence))
    return LocalRuntimeManifest(
        runtime_id=evidence.runtime_id,
        os_name=evidence.os_name,
        python_version=evidence.python_version,
        commit_sha=evidence.commit_sha,
        checks=tuple(checks),
        externally_published=False,
    )
