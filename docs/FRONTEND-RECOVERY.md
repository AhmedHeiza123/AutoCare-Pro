# Frontend recovery: scope and verification

Prepared 18 November 2026. This is a **recovered compiled-JavaScript project**, not a claim that the original React authoring repository was found.

## Result

The recovered frontend can be installed from its new lockfile, served by a development server and built into a new `app/frontend/dist`. FastAPI can serve that new output in the existing same-origin layout. The UI retains its original business workflows; no replacement screens or placeholder implementations were substituted.

The original 1,262 top-level statements were separated into three dependency-checked modules: 987 in runtime.js, 13 in localization.js and 262 in application.js. The final security pass deliberately modifies provider Ub and adds src/security/session-privacy.js for account isolation. This exception is hash-pinned in recovery/security-patches.json. Formatting does not reverse minification or recreate JSX.

The recovery index identifies **27 explicit route definitions**, including the wildcard route; the home index and protected layout are additional nested route objects. It also records 98 API string/template patterns. Those counts are structural evidence, not a claim that every workflow was exercised end to end.

## What was recovered or rebuilt

| Area | Result | Remaining work |
|---|---|---|
| Executable frontend logic | Preserved from the original bundle; readable modules and explicit imports/exports reconstructed | Original variable/component names, comments and authoring file boundaries remain unavailable |
| Routing and screens | Existing route/component logic retained, with route comments and a machine-readable index | Organize into conventional feature/component files if desired; no route was manually reimplemented |
| Arabic/English text | Existing dictionaries and language logic retained in `localization.js` | Original translation source format/workflow unknown |
| CSS | Original 41,115-byte compiled stylesheet retained byte for byte | Tailwind source/configuration, theme definitions, source stylesheets and utility generation pipeline were not recovered |
| Fonts | All 18 WOFF/WOFF2 files retained byte for byte | Preserve font licensing; no visual assets were invented |
| Build/dev tooling | New `package.json`, pinned dependencies, pnpm lockfile, entry HTML and Vite config created | These are new reconstruction choices, not the original manifests |
| Embedded libraries | Original embedded implementations and notices preserved | Full original dependency graph/lockfile unavailable; no embedded runtime library upgrade was attempted |
| Original JSX/TypeScript | Not recoverable accurately from this map-free distribution | Rewrite into JSX/typed components as a separate maintainability project if needed |
| Source maps/tests | No original maps or tests found | New preservation, wiring, tooling and browser checks were added; full business regression coverage still needs work |

The source modules use compiled calls such as `s.jsx(...)`. They are editable JavaScript, but the application is not a normal recovered JSX project. New Tailwind-looking class names will not automatically generate CSS; use explicit CSS or reconstruct a styling pipeline before redesigning screens. React and related UI libraries remain embedded in the recovered runtime, so listing only build tools in the new package manifest does not mean the application has no runtime libraries.

## New source layout

```text
app/frontend/
  index.html
  package.json
  pnpm-lock.yaml
  vite.config.js
  src/
    main.js
    recovered/
      runtime.js         embedded library code and shared runtime helpers
      localization.js    translation dictionary and language behavior
      application.js     API client, authentication, UI and routes
    styles/recovered.css
  public/assets/         original fonts
  recovery/
    original-dist/       immutable baseline, not a production build input
    manifest.json        hashes, route symbols and module boundaries
    EMBEDDED-NOTICES.txt
  tools/recover.mjs
  tools/browser-check.mjs
  tests/
  validation/            generated locally; excluded from commits
  dist/                  generated locally; excluded from this source candidate
```

Some icon setup is carried across the inferred localization boundary because it shares a declaration with the original dictionary. File boundaries describe the reconstruction, not original authoring modules.

## Evidence

### Preservation and build

Eleven Node tests pass: original structure with the reviewed provider exception, CSS/fonts, notices, wiring/globals, explicit backend targeting, build independence, URL validation and private draft/cache/cross-tab behavior. Six focused backend tests cover demo inputs, bootstrap clients and public restore filtering.

The AST comparison ignores only location/comment formatting metadata and normalizes associative logical chains and braces around a single nested `if`, which Babel's printer can reformat without changing evaluation order. It does not rename application identifiers, discard statements, replace financial logic or compare minified text alone. The wiring check also demonstrates detection of an intentionally removed React import in an in-memory test copy.

A clean directory without `node_modules` or `dist` was populated from the recovered source. `pnpm install --frozen-lockfile --offline --ignore-scripts` succeeded using the previously downloaded package store, followed by a successful Vite production build. This verifies a clean local dependency installation/build from the lockfile on this Windows/Node environment, not compatibility with every operating system.

### Browser checks against the original

Eleven original-versus-rebuilt cases have equal visible text and byte-identical screenshots in the same Chrome environment: English login, Arabic login, first-run setup, authenticated home, customers, new-customer form, Arabic vehicles, workshop board, reports, Arabic mobile home and an unauthenticated deep link.

A twelfth case exercises the actual development proxy, login and language switching. A thirteenth verifies draft cleanup, sign-out in another tab and fresh next-account settings. No uncaught JavaScript errors, unexpected fixture routes or external HTTP(S) dependencies were recorded. Fixtures do not replace backend business-rule tests.

The browser check now **builds fresh output before previewing it** and records the served JavaScript hash. It was rerun after intentionally seeding `dist` with the original output, confirming that an old distribution cannot masquerade as the new build in that check.

### Real backend/database smoke check

A separate PostgreSQL 15.19 cluster was created under the task's temporary work folder. The recovered project backend applied all migrations to an empty test database and served the newly built SPA. Checks passed for database health, first-admin setup, cookie login, authenticated identity/customer/board reads, CSRF rejection, synthetic customer creation with CSRF and repeat-setup rejection. A browser logged in through the rebuilt UI and displayed the inserted fictional customer using the real API/database.

That test reused installed runtime package files and PostgreSQL binaries. It did **not** use installed application configuration or business data and does **not** constitute a clean backend dependency installation. Both disposable servers were stopped afterward. A first test-harness attempt encountered a Windows subprocess pipe/daemon-handle timeout; the harness was corrected to use file redirection and the isolated check was rerun successfully. No application source change was required for that harness issue.

## What is not verified

- Every job, quotation, invoice, payment, refund, delivery, warranty, reporting and restore interaction.
- Browser parity beyond the recorded cases, or compatibility beyond the tested Chrome/Windows environment.
- A fresh backend dependency installation or a newly assembled Windows installer.
- Recovery of original JSX/TypeScript, component design, styling sources, original frontend dependencies or source maps.
- A penetration test, complete dependency vulnerability/rights audit, performance benchmark or public-release clearance.

## Working with the source

Use pnpm build for edited source; it does not read the baseline bundle. pnpm recover is now blocked because raw regeneration would overwrite security changes. Perform future recovery in a separate copy, reapply/test fixes and update the pinned manifest deliberately. Preservation checks compare the remaining application against the immutable baseline.

MIT is included for original project code, with third-party terms preserved separately. No GitHub, LinkedIn or other publication occurred, and the installed application was not replaced.

## Final source-candidate security status

The current candidate contains deliberate bootstrap, restore-progress and account-isolation changes. See [security summary](SECURITY-REVIEW-SUMMARY.md). Raw evidence lives outside the GitHub source tree. The new build-tool advisory and embedded-router matches remain disclosed; original-structure preservation does not imply dependency security.
