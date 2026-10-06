"""A26 — Full Local Runtime Gate v1.

Discovers a local FastAPI/OpenAPI surface, maps available endpoints to MIZAN's
required runtime evidence checks, executes only safe GET probes automatically,
and leaves non-safe checks UNVERIFIED unless an explicit probe contract exists.
"""
from __future__ import annotations
import dataclasses, json, urllib.request
from .runtime_evidence_collector import (
    EndpointProbe, EvidenceItem, EvidenceStatus, RuntimeEvidenceManifest,
    collect_http_runtime_evidence,
)
from .local_runtime_gate import REQUIRED_CHECKS

@dataclasses.dataclass(frozen=True,kw_only=True)
class DiscoveredEndpoint:
    path:str
    methods:tuple[str,...]
    operation_ids:tuple[str,...]

@dataclasses.dataclass(frozen=True,kw_only=True)
class DiscoveryResult:
    endpoints:tuple[DiscoveredEndpoint,...]
    source_url:str

def fetch_openapi(base_url:str,timeout:float=5.0)->dict:
    url=base_url.rstrip("/")+"/openapi.json"
    with urllib.request.urlopen(url,timeout=timeout) as r:
        if r.status!=200:
            raise RuntimeError(f"OpenAPI returned HTTP {r.status}")
        return json.loads(r.read().decode("utf-8"))

def discover_endpoints(base_url:str)->DiscoveryResult:
    spec=fetch_openapi(base_url)
    out=[]
    for path,methods in (spec.get("paths") or {}).items():
        ops=[]
        names=[]
        for method,obj in methods.items():
            m=method.upper()
            if m in {"GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"}:
                names.append(m)
                if isinstance(obj,dict) and obj.get("operationId"):
                    ops.append(obj["operationId"])
        out.append(DiscoveredEndpoint(path=path,methods=tuple(sorted(names)),operation_ids=tuple(sorted(ops))))
    return DiscoveryResult(endpoints=tuple(sorted(out,key=lambda x:x.path)),source_url=base_url.rstrip("/")+"/openapi.json")

def _match(endpoints:tuple[DiscoveredEndpoint,...],patterns:tuple[str,...],method:str="GET")->DiscoveredEndpoint|None:
    lowered=tuple(p.lower() for p in patterns)
    for e in endpoints:
        hay=(e.path+" "+" ".join(e.operation_ids)).lower()
        if method in e.methods and any(p in hay for p in lowered):
            return e
    return None

SAFE_GET_CHECKS={
    "api_health":("health","ping"),
    "database_health":("state","db","database"),
    "audit_log":("audit","log"),
}

def build_safe_get_probes(base_url:str,discovery:DiscoveryResult)->tuple[EndpointProbe,...]:
    probes=[]
    root=base_url.rstrip("/")
    for check,patterns in SAFE_GET_CHECKS.items():
        e=_match(discovery.endpoints,patterns,"GET")
        if e is not None:
            probes.append(EndpointProbe(name=check,url=root+e.path))
    return tuple(probes)

def collect_discovered_runtime_evidence(*,runtime_id:str,commit_sha:str,base_url:str)->RuntimeEvidenceManifest:
    d=discover_endpoints(base_url)
    probes=build_safe_get_probes(base_url,d)
    partial=collect_http_runtime_evidence(runtime_id=runtime_id,commit_sha=commit_sha,base_url=base_url,probes=probes)
    by={x.name:x for x in partial.checks}
    checks=[]
    for name in REQUIRED_CHECKS:
        if name in by:
            checks.append(by[name])
        else:
            checks.append(EvidenceItem(
                name=name,status=EvidenceStatus.UNVERIFIED,
                evidence="No safe automatic probe contract discovered; explicit runtime adapter required.",
                collected_at=0.0,
            ))
    from .runtime_evidence_collector import _manifest_hash
    checks=tuple(checks)
    return RuntimeEvidenceManifest(
        runtime_id=runtime_id,commit_sha=commit_sha,os_name=partial.os_name,
        python_version=partial.python_version,base_url=base_url,
        checks=checks,manifest_sha256=_manifest_hash(runtime_id,commit_sha,base_url,checks),
    )
