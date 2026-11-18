# Attribution review

Owner confirmed rights to their original code/assets on 18 November 2026 and selected MIT. That confirmation does not relicense third-party code.

| Component area | Identification evidence | Notice handling |
|---|---|---|
| React / React DOM 18.3.1 | Embedded version/signature and production headers | Full package MIT texts retained |
| React JSX runtime / Scheduler | Explicit React production-license headers | Existing React copyright/MIT text retained; exact Scheduler package version is not asserted |
| React Router / DOM 6.30.6 and Remix router 1.23.4 | Embedded version/license headers | Full exact-package MIT texts retained |
| lucide-react 1.59.0 | Embedded version/ISC headers and icons | Full exact-package license retained |
| TanStack Query React binding/cache core | Strong family inference from QueryClient context/provider, exact error text and cache/observer implementation | Official upstream MIT text added with an immutable license commit and hash; exact embedded versions remain unknown |
| Browser QR generator (`qrcode`) | Multiple distinctive QR tables, functions and error messages match official package sources | Official reference-package MIT text added; the reference version is not an embedded-version claim |
| `dijkstrajs` inside QR segmentation | Exact shortest-path function names and error fragments match official package sources | Official reference-package MIT text added; exact embedded version remains unknown |
| Tailwind CSS generated utilities/preflight | tw-prefixed utility/preflight signatures; original config/version unavailable | Official reference-package MIT text retained without asserting the original version |
| Cairo fonts | Bundled Cairo assets and supplied OFL text | Original OFL text retained with backend/public font assets |

See [IDENTIFIED-DEPENDENCIES.json](IDENTIFIED-DEPENDENCIES.json) for package/source/hash evidence. All original embedded notices remain in the recovered code and baseline.

Family-level attribution closes the previously missing Query-family notice in the available evidence; it does not recreate an original package lockfile, certify every possible transitive component or establish version-specific security clearance. If a later review identifies a different component/license or conflicting rights, resolve it before distributing that component. Exact unknown version numbers are deliberately not filled with latest package versions.

The source candidate excludes bundled Python/PostgreSQL programs and node_modules. A future installer or dependency redistribution needs its own complete component/notice review.
