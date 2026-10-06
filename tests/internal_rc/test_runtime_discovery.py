import json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from mizan_agents.runtime_discovery import *
from mizan_agents.runtime_evidence_verifier import verify_runtime_evidence

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/openapi.json":
            body=json.dumps({"paths":{
                "/health":{"get":{"operationId":"health"}},
                "/state":{"get":{"operationId":"read_state"}},
                "/audit":{"get":{"operationId":"audit_log"}},
                "/ingest/text":{"post":{"operationId":"ingest_text"}},
            }}).encode()
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(body); return
        if self.path in ("/health","/state","/audit"):
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(b'{"ok":true}'); return
        self.send_response(404); self.end_headers()
    def log_message(self,*args): pass

def server():
    s=HTTPServer(("127.0.0.1",0),H)
    t=threading.Thread(target=s.serve_forever,daemon=True); t.start()
    return s,f"http://127.0.0.1:{s.server_port}"

def test_discovers_openapi_and_safe_get_endpoints():
    s,url=server()
    try:
        d=discover_endpoints(url)
        assert any(x.path=="/health" for x in d.endpoints)
        p=build_safe_get_probes(url,d)
        assert {x.name for x in p}=={"api_health","database_health","audit_log"}
    finally: s.shutdown()

def test_unsafe_post_ingest_is_not_auto_executed():
    s,url=server()
    try:
        m=collect_discovered_runtime_evidence(runtime_id="r",commit_sha="a"*40,base_url=url)
        by={x.name:x for x in m.checks}
        assert by["ingest_path"].status is EvidenceStatus.UNVERIFIED
        assert by["api_health"].status is EvidenceStatus.PASS
    finally: s.shutdown()

def test_partial_discovery_remains_not_runtime_verified():
    s,url=server()
    try:
        m=collect_discovered_runtime_evidence(runtime_id="r",commit_sha="a"*40,base_url=url)
        v=verify_runtime_evidence(m)
        assert v.integrity_ok
        assert not v.runtime_verified
        assert "ingest_path:UNVERIFIED" in v.blockers
    finally: s.shutdown()
