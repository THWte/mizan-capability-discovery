param(
  [string]$BaseUrl = "http://127.0.0.1:8787",
  [string]$CommitSha = "",
  [string]$Output = "runtime-evidence.json"
)
$ErrorActionPreference = "Stop"
if (-not $CommitSha) {
  try { $CommitSha = (git rev-parse HEAD).Trim() } catch { throw "CommitSha required when git is unavailable" }
}
$env:PYTHONPATH = "agents;contracts"
@'
import os, sys
from mizan_agents.runtime_evidence_collector import EndpointProbe, collect_http_runtime_evidence, write_manifest
base=os.environ["MIZAN_BASE_URL"].rstrip("/")
sha=os.environ["MIZAN_COMMIT_SHA"]
out=os.environ["MIZAN_EVIDENCE_OUTPUT"]
probes=(
    EndpointProbe(name="api_health",url=base+"/health"),
    EndpointProbe(name="database_health",url=base+"/state"),
)
m=collect_http_runtime_evidence(runtime_id="mizan-local-windows",commit_sha=sha,base_url=base,probes=probes)
write_manifest(m,out)
print(m.to_json())
'@ | python -
