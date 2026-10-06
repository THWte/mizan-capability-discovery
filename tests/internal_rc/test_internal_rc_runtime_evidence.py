import dataclasses, json
from mizan_agents.runtime_evidence_collector import *
from mizan_agents.local_integration_contract import *
from mizan_agents.runtime_evidence_verifier import *
from mizan_agents.internal_rc import *
from mizan_agents.local_runtime_gate import REQUIRED_CHECKS,RuntimeCheckStatus

def evidence(items):
    checks=tuple(EvidenceItem(name=n,status=s,evidence=e,collected_at=1.0) for n,s,e in items)
    base=RuntimeEvidenceManifest(runtime_id="r",commit_sha="a"*40,os_name="Windows",python_version="3.12",base_url="http://127.0.0.1:8787",checks=checks,manifest_sha256="")
    return dataclasses.replace(base,manifest_sha256=_manifest_hash_for_test(base))

def _manifest_hash_for_test(m):
    import hashlib
    payload={"runtime_id":m.runtime_id,"commit_sha":m.commit_sha,"base_url":m.base_url,"checks":[dataclasses.asdict(c) for c in m.checks]}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def test_missing_runtime_checks_remain_unverified_not_invented():
    e=evidence([("api_health",EvidenceStatus.PASS,"HTTP 200")])
    local=to_local_runtime_manifest(e)
    by={c.name:c for c in local.checks}
    assert by["api_health"].status is RuntimeCheckStatus.PASS
    assert by["audit_log"].status is RuntimeCheckStatus.UNVERIFIED

def test_tampered_manifest_fails_integrity():
    e=evidence([("api_health",EvidenceStatus.PASS,"HTTP 200")])
    bad=dataclasses.replace(e,commit_sha="b"*40)
    v=verify_runtime_evidence(bad)
    assert not v.integrity_ok and not v.runtime_verified

def test_partial_http_probe_evidence_cannot_verify_runtime():
    e=evidence([("api_health",EvidenceStatus.PASS,"HTTP 200"),("database_health",EvidenceStatus.PASS,"HTTP 200")])
    v=verify_runtime_evidence(e)
    assert v.integrity_ok and not v.runtime_verified
    assert "MISSING:ingest_path" not in v.blockers
    assert "ingest_path:UNVERIFIED" in v.blockers

def test_complete_explicit_evidence_can_verify_internal_runtime():
    e=evidence([(n,EvidenceStatus.PASS,f"verified:{n}") for n in REQUIRED_CHECKS])
    v=verify_runtime_evidence(e)
    assert v.integrity_ok and v.runtime_verified and not v.blockers
    rc=build_internal_rc(commit_sha=e.commit_sha,runtime=to_local_runtime_manifest(e))
    assert rc.stage=="INTERNAL_RC" and rc.runtime_verified and not rc.production_claimed

def test_internal_rc_can_exist_with_unverified_runtime_but_records_blockers():
    e=evidence([("api_health",EvidenceStatus.PASS,"HTTP 200")])
    rc=build_internal_rc(commit_sha=e.commit_sha,runtime=to_local_runtime_manifest(e))
    assert not rc.runtime_verified and rc.runtime_blockers

def test_internal_rc_cannot_claim_production():
    import pytest
    with pytest.raises(ValueError):
        InternalRCManifest(rc_id="x",commit_sha="a"*40,stage="INTERNAL_RC",runtime_verified=True,runtime_blockers=(),production_claimed=True)
