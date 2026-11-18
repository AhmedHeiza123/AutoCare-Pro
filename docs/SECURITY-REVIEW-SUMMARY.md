# Security review summary

18 November 2026. **Updated disposition: technical source-preparation checks are satisfied within the stated scope; actual publication still awaits explicit owner approval. Production deployment remains a separate unapproved decision.** See [the separate gates](PUBLICATION-VS-OPERATIONS.md). This is not a penetration test or zero-vulnerability certification.

## Fixed

- First-admin setup rejects actual non-loopback clients before database work. Loopback/mapped-loopback and rejection checks pass. Do not expose setup behind a local reverse proxy, which can make remote clients appear local.
- Public restore progress whitelists key/label/status and omits raw private details/errors. A regression check confirms synthetic private content is absent.
- Logout, invalid sessions and successful account changes clear private reception drafts/query records. Other same-origin tabs receive a reset signal. Unit and two-account/cross-tab browser checks pass.
- Earlier fixed-demo-password and developer-tools-path fixes remain. Existing accounts were not changed automatically.

The modified frontend provider is hash-pinned in `app/frontend/recovery/security-patches.json`. The original bundle is provenance only; regeneration over the security changes is blocked.

## Open items

| Item | Disposition |
|---|---|
| Build tooling | `pnpm audit` reports High [GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf) for picomatch 4.0.7 through Vite/tinyglobby/fdir. The reviewed advisory and registry list no patched current version. Exposure is development/build glob processing; no app route accepting arbitrary glob input was identified. Open, not suppressed. |
| Embedded router | OSV matches [GHSA-337j-9hxr-rhxg](https://github.com/advisories/GHSA-337j-9hxr-rhxg) and [GHSA-wrjc-x8rr-h8h6](https://github.com/advisories/GHSA-wrjc-x8rr-h8h6) against React Router 6.30.6. The first concerns SSR hydration and excludes declarative mode; this app uses client-side createRoot/browser routing. The second concerns attacker-controlled navigation paths; no working application exploit was established. Applicability/migration review remains, and no vendor upgrade is claimed. |
| LAN transport | HTTP remains configurable. Use HTTPS and secure cookies for network access. Internet-facing deployment is not approved. |
| Recovery storage | Restore creates a plaintext safety archive and retains old database/files, even if scheduled backups are encrypted. Protect storage and define retention/cleanup. Recovery behavior was not redesigned. |
| Inventory and rights | Owner confirmed original-work rights. Six exact-package license texts, original notices and four family-reference MIT texts for TanStack Query, qrcode, dijkstrajs and Tailwind CSS are included. React's preserved MIT text covers identified JSX/Scheduler notices. Exact versions remain unknown; full embedded security/inventory certification is not claimed. Unknown versions alone are not a blanket source-sharing ban. |

## Scan scope

Gitleaks 8.30.1 found no credential leaks in the scanned candidate. Supplemental checks cover private configuration/data paths, removed credentials, user-specific paths and selected token/PII patterns. Test-only cookie/CSRF strings, generic placeholders and published copyright notices are not live credentials. No Git history was supplied/audited.

OSV covered 19 direct backend pins and six identifiable embedded npm packages. A separate snapshot of 45 installed Python distributions used by the smoke test returned no advisories at query time; it is not a fresh candidate lockfile. Auditing the new frontend tooling does not audit every embedded library.

Fresh backend resolution, exhaustive exploitation, all finance/concurrency/recovery workflows and every deployment configuration remain outside scope. See [VALIDATION.md](VALIDATION.md) and [SECURITY.md](../SECURITY.md).
