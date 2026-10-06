# A18-A21 Local Runtime and Release Gates v1

This bundle closes the gap between architecture tests and a release claim.

A18 defines concrete evidence required to call a local MIZAN runtime integrated: API, database, ingest, canonical flow, citation round-trip, retrieval round-trip, knowledge proposal, non-authoritative reasoning, and audit logging.

A19 defines a two-independent-reviewer plus adjudication workflow for non-synthetic Golden Dataset labels. Disagreement cannot be silently averaged or admitted.

A20 converts known Docling/PaddleOCR findings into executable hardening policy. Both remain RESTRICTED, single-concurrency, process-isolated, and not production-approved. PaddleOCR concurrent conversion is explicitly blocked.

A21 distinguishes DEVELOPMENT, INTERNAL_RC, PRODUCTION_RC and PRODUCTION. An internal release candidate may exist for engineering evaluation while production remains blocked. Production/Production RC fail closed against the Production Readiness Gate.

No real case data is committed by this bundle. PR #2 and PR #5 remain external sandbox capability branches.
