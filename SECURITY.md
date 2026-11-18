# Security and deployment scope

This is a reviewed local source candidate, not a penetration-tested or production-certified release. Evidence is limited to the recorded environment and checks in [VALIDATION.md](docs/VALIDATION.md).

## Operating boundaries

- Keep loopback binding for development and first-run setup. First-admin creation rejects non-loopback clients using the actual connection address, not forwarded headers. Do not expose/proxy bootstrap before owner setup; a local reverse proxy can make remote clients appear local.
- Configure HTTPS and secure cookies for LAN use. Private-network HTTP does not protect credentials/session tokens. Internet-facing deployment is not approved by this review.
- Use a dedicated OS/database identity, protect configuration/storage permissions and review privileged recovery operations separately.
- Treat records, browser drafts, audit data, uploads, exports and backups as confidential. Account resets clear query data/private drafts and signal other same-origin tabs to sign out. Use separate browser/OS profiles on shared computers; valid-session local drafts are not encrypted storage.
- Restore currently creates a plaintext safety archive and retains old database/file copies. Scheduled-backup encryption does not cover every recovery artifact. Use protected/encrypted storage and reviewed retention/cleanup.
- Backups can contain business data, password hashes and session/CSRF records. Omitting `.env` does not anonymize them.

## Open items and reporting

[The summary](docs/SECURITY-REVIEW-SUMMARY.md) separates upstream advisory severity from observed exposure. The original embedded graph is incomplete, and tooling audits do not cover every runtime component. Empty secret-scanner output does not certify application security.

Report sensitive findings privately to the project owner. Enabling a private reporting channel when a repository is created is recommended, not a prerequisite to preparing this offline candidate. Do not post secrets, configured environment files, customer data or unredacted evidence in public issues. No repository/contact address is invented here, and this file does not authorize publication.

Source-sharing gates and actual deployment requirements are separated in [PUBLICATION-VS-OPERATIONS.md](docs/PUBLICATION-VS-OPERATIONS.md). Open advisories remain disclosed and unsuppressed; source publication is not a claim that the software is safe for every deployment.
