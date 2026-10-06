"""A22 — Internal Release Candidate Builder v1."""
from __future__ import annotations
import dataclasses, hashlib, json
from .local_runtime_gate import LocalRuntimeManifest, verify_local_runtime
from .release_readiness import ReleaseStage, ReleaseCandidateReport

@dataclasses.dataclass(frozen=True,kw_only=True)
class InternalRCManifest:
    rc_id:str
    commit_sha:str
    stage:str
    runtime_verified:bool
    runtime_blockers:tuple[str,...]
    production_claimed:bool=False

    def __post_init__(self):
        if self.production_claimed:
            raise ValueError("Internal RC cannot claim production readiness")
        if self.stage!="INTERNAL_RC":
            raise ValueError("Internal RC manifest stage must be INTERNAL_RC")

def build_internal_rc(*,commit_sha:str,runtime:LocalRuntimeManifest)->InternalRCManifest:
    ok,blockers=verify_local_runtime(runtime)
    raw=f"{commit_sha}|INTERNAL_RC|{ok}|{'|'.join(blockers)}".encode()
    return InternalRCManifest(
        rc_id="IRC-"+hashlib.sha256(raw).hexdigest()[:20],
        commit_sha=commit_sha,
        stage="INTERNAL_RC",
        runtime_verified=ok,
        runtime_blockers=blockers,
    )
