"""A23 — Runtime Evidence Collector v1.

Collects local runtime evidence into a deterministic manifest. It uses only
explicitly configured HTTP endpoints and local process metadata. It never
uploads case data and never marks production readiness by itself.
"""
from __future__ import annotations
import dataclasses, hashlib, json, platform, time, urllib.request
from enum import Enum
from pathlib import Path

class EvidenceStatus(str,Enum):
    PASS="PASS"; FAIL="FAIL"; UNVERIFIED="UNVERIFIED"

@dataclasses.dataclass(frozen=True,kw_only=True)
class EndpointProbe:
    name:str
    url:str
    expected_status:int=200
    timeout_seconds:float=5.0

@dataclasses.dataclass(frozen=True,kw_only=True)
class EvidenceItem:
    name:str
    status:EvidenceStatus
    evidence:str
    collected_at:float

@dataclasses.dataclass(frozen=True,kw_only=True)
class RuntimeEvidenceManifest:
    runtime_id:str
    commit_sha:str
    os_name:str
    python_version:str
    base_url:str
    checks:tuple[EvidenceItem,...]
    manifest_sha256:str

    def to_json(self)->str:
        return json.dumps(dataclasses.asdict(self),ensure_ascii=False,indent=2,sort_keys=True)

def _probe_http(p:EndpointProbe)->EvidenceItem:
    started=time.time()
    try:
        req=urllib.request.Request(p.url,method="GET")
        with urllib.request.urlopen(req,timeout=p.timeout_seconds) as r:
            body=r.read(512).decode("utf-8","replace")
            ok=(r.status==p.expected_status)
            return EvidenceItem(
                name=p.name,
                status=EvidenceStatus.PASS if ok else EvidenceStatus.FAIL,
                evidence=f"HTTP {r.status}; body_prefix={body!r}",
                collected_at=started,
            )
    except Exception as e:
        return EvidenceItem(name=p.name,status=EvidenceStatus.FAIL,evidence=f"{type(e).__name__}: {e}",collected_at=started)

def _manifest_hash(runtime_id:str,commit_sha:str,base_url:str,checks:tuple[EvidenceItem,...])->str:
    payload={
        "runtime_id":runtime_id,
        "commit_sha":commit_sha,
        "base_url":base_url,
        "checks":[dataclasses.asdict(c) for c in checks],
    }
    raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def collect_http_runtime_evidence(*,runtime_id:str,commit_sha:str,base_url:str,probes:tuple[EndpointProbe,...])->RuntimeEvidenceManifest:
    checks=tuple(_probe_http(p) for p in probes)
    return RuntimeEvidenceManifest(
        runtime_id=runtime_id,
        commit_sha=commit_sha,
        os_name=platform.system(),
        python_version=platform.python_version(),
        base_url=base_url,
        checks=checks,
        manifest_sha256=_manifest_hash(runtime_id,commit_sha,base_url,checks),
    )

def verify_manifest_integrity(m:RuntimeEvidenceManifest)->bool:
    return m.manifest_sha256==_manifest_hash(m.runtime_id,m.commit_sha,m.base_url,m.checks)

def write_manifest(m:RuntimeEvidenceManifest,path:str|Path)->None:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(m.to_json(),encoding="utf-8")
