# A26 — Full Local Runtime Gate v1

This stage adds automatic discovery of the live local MIZAN FastAPI surface through `/openapi.json`.

The gate auto-executes only safe GET probes (health/state/audit when discoverable). It intentionally does **not** auto-POST to ingest or mutate case data. Any required check without a safe explicit probe remains `UNVERIFIED`.

This makes the local execution path honest and mechanical:
1. Start the local MIZAN runtime.
2. Run `scripts/dev/run-full-runtime-gate.ps1`.
3. Inspect `runtime-evidence-full.json`.
4. Add explicit adapters for ingest/citation/retrieval/knowledge/reasoning only against verified local API contracts.
5. Re-run until the A18 required checklist is fully PASS.

No GitHub Action can prove a localhost runtime on the owner's Windows machine; only the local evidence manifest can do so.
