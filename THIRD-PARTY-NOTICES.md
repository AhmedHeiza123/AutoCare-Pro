# Third-party notices and provenance

The owner selected MIT and confirmed rights to their original code/assets. Root MIT does not replace third-party terms.

## Retained attribution

- Six version-identifiable embedded packages retain their original notices and full package license texts: React, React DOM, React Router, React Router DOM, Remix router and lucide-react.
- TanStack Query React/cache code is identified at family level. Its official MIT text is included with an immutable upstream license commit/hash. Exact embedded versions remain unknown.
- Browser QR generation and embedded shortest-path code match the `qrcode` and `dijkstrajs` families through multiple distinctive signatures. Their official reference-package MIT texts are included; reference versions do not assert exact embedded versions.
- Explicit React JSX/Scheduler production notices are retained under the React MIT text. No exact standalone Scheduler version is invented.
- Tailwind-style generated utility/preflight CSS has an added official family-reference MIT text; original version/configuration are not asserted.
- Cairo fonts retain the supplied OFL text in backend and public font assets.
- Original embedded notices remain in recovered code and `app/frontend/recovery/EMBEDDED-NOTICES.txt`.

See [the inventory](third_party/IDENTIFIED-DEPENDENCIES.json) and [attribution review](third_party/ATTRIBUTION-REVIEW.md) for sources, hashes, confidence and unknowns. There are six exact-package texts and four added family-reference MIT texts, not a reconstructed original lockfile.

## Scope

Python/PostgreSQL runtime programs and node_modules are excluded. A future installer or dependency redistribution needs its own complete notices review. New tooling dependencies are represented by the frontend manifest/lockfile; those do not enumerate every library already embedded in the recovered JavaScript.

Unknown versions affect version-specific security review; they do not by themselves prove missing licensing permission. This is a bounded attribution review, not an exhaustive legal certificate. If later evidence identifies an unlisted component or conflicting rights, resolve its terms or remove it before distributing that component.

See [publication versus operation](docs/PUBLICATION-VS-OPERATIONS.md) for the distinct gates. No publication has occurred.
