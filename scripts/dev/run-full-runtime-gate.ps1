param(
  [string]$BaseUrl = "http://127.0.0.1:8787",
  [string]$CommitSha = "",
  [string]$Output = "runtime-evidence-full.json"
)
$ErrorActionPreference = "Stop"
if (-not $CommitSha) {
  try { $CommitSha = (git rev-parse HEAD).Trim() } catch { throw "CommitSha required when git is unavailable" }
}
$env:PYTHONPATH = "agents;contracts"
$env:MIZAN_BASE_URL = $BaseUrl
$env:MIZAN_COMMIT_SHA = $CommitSha
$env:MIZAN_EVIDENCE_OUTPUT = $Output
@'
import os
from mizan_agents.runtime_discovery import collect_discovered_runtime_evidence
from mizan_agents.runtime_evidence_collector import write_manifest
from mizan_agents.runtime_evidence_verifier import verify_runtime_evidence

m = collect_discovered_runtime_evidence(
    runtime_id="mizan-local-windows",
    commit_sha=os.environ["MIZAN_COMMIT_SHA"],
    base_url=os.environ["MIZAN_BASE_URL"],
)
write_manifest(m, os.environ["MIZAN_EVIDENCE_OUTPUT"])
v = verify_runtime_evidence(m)
print(m.to_json())
print("")
print("RUNTIME VERIFIED:", v.runtime_verified)
print("BLOCKERS:", list(v.blockers))
if not v.integrity_ok:
    raise SystemExit(2)
'@ | python -
