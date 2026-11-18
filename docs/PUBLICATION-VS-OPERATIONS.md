# Source publication versus operational readiness

18 November 2026. This document supersedes any earlier checklist that treated every deployment issue as a blanket blocker to sharing source. **No publication has been authorized or performed.**

## Before public GitHub source publication

| ID | Requirement | Current disposition |
|---|---|---|
| PUB-01 | Owner has rights to publish their code/assets and chooses a license | Owner explicitly confirmed publication rights on 18 November 2026; MIT selection is retained. Root MIT does not replace third-party terms. |
| PUB-02 | Retain applicable third-party copyright/license notices and disclose identification limits | Original notices and six exact-package license texts are retained. Family-level TanStack Query, qrcode and dijkstrajs MIT texts have been added; React's MIT text covers identified JSX/Scheduler notices. Exact family versions are not invented. See the attribution review. No unlicensed component was affirmatively identified; this is not an exhaustive legal certification. Later unclear rights must be resolved or the component removed before distribution. |
| PUB-03 | Exclude secrets, customer/business records and private review material | Clean source allowlist and secret scan are verified again for this updated archive. Only fictional screenshots/examples are proposed for public use. Private review/evidence stays outside the repository. |
| PUB-04 | Describe the project honestly | README identifies recovered compiled JavaScript, tests, open advisories and limitations. No original JSX/TypeScript recovery, adoption metrics or production certification is claimed. |
| PUB-05 | Candidate is reproducible to the documented scope | Pinned frontend lockfile/build and test evidence are retained. Fresh backend installation/full workflow limits are explicit. Exact archival frontend versions and full production testing are not prerequisites to describing this as an experimental source recovery. |
| PUB-06 | Owner explicitly approves the concrete public action | **Pending.** User requested preparation without publication. Rights confirmation and choosing MIT are not approval to push, create a public repository or post on LinkedIn. |

**Assessment:** no known technical source-packaging blocker remains in the reviewed candidate. Applicable-notice checks were improved without claiming a complete original dependency inventory. This is a bounded technical assessment; new evidence of private data or unclear third-party rights would reopen the relevant gate. The remaining owner action is explicit publication approval after reviewing the actual candidate.

## Not automatic blockers to publishing this experimental source

- An upstream vulnerability advisory does not, by itself, mean this code cannot be shared. Keep the finding visible, explain applicability and avoid advertising the software as secure/production-ready. There is no claim that GitHub performed a security approval.
- The unresolved picomatch advisory is in development/build tooling, not a reason to imply that the built FastAPI application executes that package. Its execution constraints are below.
- Router version matches require documented applicability/migration work. SSR hydration is not the observed app mode; navigation-path exposure remains conditional and under review.
- Missing original JSX/TypeScript/component names or the original lockfile are reconstruction limitations, not secret-data or publication-permission failures when disclosed accurately.
- HTTPS, protected database storage and a full restore rehearsal concern operating real systems. They are not requirements to upload an inert source archive.
- A private security-reporting channel is recommended when a repository is created. It is not a reason to claim the offline review candidate cannot be prepared.

## Before real-data operation / LAN deployment

| ID | Operational requirement | Status |
|---|---|---|
| OPS-01 | Complete bootstrap locally and keep it away from remote/local-proxy exposure | Loopback guard implemented; deployment procedure must still be followed |
| OPS-02 | Use TLS/HTTPS and secure cookies before LAN/network access | Deployment task; plaintext LAN transport remains possible and is not approved for real credentials |
| OPS-03 | Protect/encrypt backups, pre-restore safety archives and retained old databases/files; define cleanup/retention | Plaintext safety artifacts remain an operational risk; recovery behavior was not redesigned |
| OPS-04 | Resolve runtime advisory applicability and incomplete exact-version inventory for the chosen threat model | Open; no embedded runtime upgrade or full dependency clearance is claimed |
| OPS-05 | Verify a fresh backend environment, permissions, financial retries/concurrency, attachments, recovery/rollback and realistic volumes | Focused tests/smoke are evidence, not the complete acceptance suite |
| OPS-06 | Apply dedicated OS/database identities, least privilege, storage ACLs and shared-device procedures | Site-specific work; use separate profiles and review privileged recovery access |

For **developers running tooling**, use trusted source/glob patterns and localhost binding; picomatch's open ReDoS advisory must be rechecked when an upstream fix is available. The build tool is not an approved production web server.

## What changed in this update

Added missing family-level attribution/license evidence, recorded the owner's rights confirmation, separated publication gates from execution constraints, and synchronized the README/security/checklists/LinkedIn status. No library version, application behavior, deployed configuration or database was changed to manufacture a clean audit result.
