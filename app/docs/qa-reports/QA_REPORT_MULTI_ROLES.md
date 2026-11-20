# Several roles per user (2026-11-20)

Status: implemented in the package and tested on an isolated instance. **Not installed on C:\AutoCarePro.** Needs the installer (it applies migration 0012 after saving a database copy).

## Design
* `users.role_id` stays the user's **primary** role — every existing user, API client and screen keeps working unchanged.
* New table `user_roles(user_id, role_id)` (migration `0012_user_extra_roles.py`, additive; downgrade drops only that table) holds the **additional** roles.
* Effective permissions = **union** of the permissions of all the user's roles (`User.permissions`), so every permission check in the application uses it automatically.
* API: `GET /api/users` and `/api/auth/me` return `roles` (primary first) next to the old `role`/`role_label`. `POST /api/users` accepts optional `roles`; `PATCH /api/users/{id}` accepts `roles` = the complete role set (the current primary role stays primary if kept, otherwise the first becomes primary). The old `role` field still works.
* Rules kept/added: roles must exist (422), at least one role; nobody changes his own roles (409); changing the set signs the user out everywhere; an administrator role held as an additional role counts for "at least one active administrator"; everything is in the audit trail (before/after role lists).
* Screen: the compiled Users page was not modified. `integration.js` adds an "Additional roles" check-box group under every user and in the new-user form (Arabic/English, own row disabled), and adds the chosen roles to the compiled form's create request.

## Files
`alembic/versions/0012_user_extra_roles.py` (new), `app/models/auth.py`, `app/models/__init__.py`, `app/api/auth.py`, `tests/test_multi_roles.py` (new, 6 tests), `tests/test_inventory.py` (expected migration head 0011 → 0012), `frontend/inventory-src/integration.js`, `integration.css`; rebuilt `dist/assets/inventory/*`.

## Tests executed
* Full backend suite: **124 run, 124 passed**, 0 failed (118 before + 6 new).
* New tests: union of permissions over HTTP (a purchasing endpoint only the extra role allows works; `/api/users` still 403); sessions revoked on change, unchanged set keeps sessions, dropping the primary promotes the next; empty/unknown roles 422 and non-admins 403; self change 409; admin as additional role gives administrator power; DB keeps primary in `users.role_id` and extras in `user_roles`; migration up/down/up on a database with data.
* Browser (isolated instance, built-in browser): created a user with a primary role and two additional roles through the real form (stored correctly, form cleared); ticked Storekeeper on an existing technician (saved, permissions grew, message shown); own row disabled; Arabic and English labels.

## Limits
* Playwright unavailable; built-in browser only. Not tested: other browsers, phone width of the new check-box rows.
* Changing a user's PRIMARY role still uses the compiled page's own select (unchanged); our boxes refresh about a second later.
* The extra boxes depend on the Users page markup (a list item containing `@username`); if the compiled page changes, nothing is injected and the API keeps working.
* The live system needs the installer to apply migration 0012; until then the new code must not be copied alone.
