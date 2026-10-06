# A22-A25 — Internal RC Runtime Evidence v1

A22 creates a deterministic INTERNAL_RC manifest from the existing local-runtime contract. Internal RC never claims production.

A23 collects explicit local runtime evidence. The first Windows collector probes only endpoints that can be honestly observed generically (/health and /state); it does not fabricate ingest, citation, retrieval, knowledge, reasoning, or audit success.

A24 maps collected evidence into the A18 LocalRuntimeManifest. Missing checks become UNVERIFIED.

A25 verifies evidence-manifest integrity and the full required runtime checklist.

This makes the next local step mechanical: run the collector against the live local MIZAN service, then add endpoint-specific probes/adapters for the remaining checks based on the actual local API contract. No case data is uploaded by this architecture.
