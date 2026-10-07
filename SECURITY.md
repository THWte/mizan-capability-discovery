# Security Policy

## Scope

This repository is public and contains MIZAN architecture, contracts, synthetic fixtures, benchmarks, and tests.

It must not be used as a storage location for real case files, personal information, credentials, private databases, or confidential legal material.

## Sensitive-data policy

Do **not** commit:

- real judgments, pleadings, exhibits, recordings, or case bundles belonging to the owner or clients;
- national identifiers, IBANs, phone numbers, private addresses, or equivalent personal data;
- access tokens, API keys, passwords, cookies, certificates, or secrets;
- local runtime databases, memory stores, or logs containing case content;
- private prompts or configuration files that embed secrets.

If sensitive data is discovered in a branch or pull request, stop normal development on that branch and remediate the exposure before further integration.

## AI / legal-intelligence security boundary

Security in MIZAN includes epistemic integrity.

The following are considered critical defects:

- unverified model output entering an Accepted Fact store;
- retrieval output being treated as evidence authority;
- loss of source provenance or source SHA-256 traceability;
- engine-owned identifiers being silently treated as MIZAN stable locators;
- cross-case information being promoted into another case without governed verification;
- simulation or training output being recorded as real case fact.

## Reporting

For sensitive vulnerabilities, do not publish secrets or private case details in a public GitHub issue.

Use a private communication channel available to the repository owner. If no private channel is available, open a minimal public issue that contains no exploit details, credentials, personal data, or case content and request a private follow-up.

## Supported baseline

Security fixes are applied to the active `main` branch and to any explicitly maintained release branch documented by the project.
