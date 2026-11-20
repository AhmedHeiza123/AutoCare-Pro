// AutoCare Pro - integration of the inventory UI into the existing application WITHOUT editing its compiled bundles.
// This small module is loaded by the main page. It only adds DOM: (1) an "Inventory" link in the side menu, and (2) on a repair-order page,
// the "Part source" buttons (From warehouse / Customer supplied) next to the spare-parts section, pointing at the inventory UI.
// If the application's markup changes and a hook is not found, nothing is injected (the inventory UI stays reachable at /inventory.html).
const stored = (() => { try { return localStorage.getItem('autocare.lang'); } catch { return null; } })();
const ar = stored === 'ar';
const t = (a, e) => (ar ? a : e);

let allowed = null; // permissions of the signed-in user (null = unknown yet)
let csrfToken = ''; let myUsername = '';
async function loadPermissions() {
  try {
    const res = await fetch('/api/auth/me', { credentials: 'same-origin' });
    if (res.ok) { const data = await res.json(); allowed = data.user.permissions; csrfToken = data.csrf_token; myUsername = data.user.username; } else allowed = [];
  } catch { allowed = []; }
}
const has = (p) => Array.isArray(allowed) && allowed.includes(p);

function addMenuLink() {
  const nav = document.querySelector('.ac-side nav, aside nav, nav[aria-label]');
  if (!nav || nav.querySelector('[data-inventory-link]')) return;
  if (!(has('inventory.read') || has('purchasing.read') || has('parts.write'))) return;
  const list = nav.querySelector('ul');
  // copy the classes of an INACTIVE menu item: the first item is usually the selected one (white pill), which made the new link unreadable
  const sample = [...nav.querySelectorAll('li a')].find((x) => !x.hasAttribute('aria-current') && !/\bbg-white\b/.test(x.className) && !x.dataset.inventoryLink) || nav.querySelector('li a');
  if (!list || !sample) return;
  const li = document.createElement('li');
  const a = document.createElement('a');
  a.href = '/inventory.html';
  a.className = sample.className.replace(/\b(active|bg-white|text-brand-dark|shadow)\b/g, '').replace(/\s+/g, ' ').trim();
  a.setAttribute('data-nav-kind', 'inventory');
  a.dataset.inventoryLink = '1';
  // same icon treatment as the other menu items (a box), sized like the existing icons when one can be found
  const sampleIcon = sample.querySelector('svg');
  if (sampleIcon) {
    const NS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(NS, 'svg');
    for (const attr of ['class', 'width', 'height', 'stroke-width', 'stroke-linecap', 'stroke-linejoin']) if (sampleIcon.hasAttribute(attr)) svg.setAttribute(attr, sampleIcon.getAttribute(attr));
    svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor'); svg.setAttribute('aria-hidden', 'true');
    for (const d of ['M21 8l-9-5-9 5v8l9 5 9-5V8z', 'M3 8l9 5 9-5', 'M12 13v8']) { const p = document.createElementNS(NS, 'path'); p.setAttribute('d', d); svg.append(p); }
    a.append(svg);
  }
  a.append(document.createTextNode(t('المخزن والمشتريات', 'Inventory & purchasing')));
  li.append(a);
  list.append(li);
}

function addPartSourceButtons() {
  const m = location.pathname.match(/^\/jobs\/([0-9a-f-]{36})$/);
  if (!m || document.querySelector('[data-inventory-sources]') || !has('parts.write')) return;
  // find the spare-parts section by its heading text (Arabic or English)
  const heading = [...document.querySelectorAll('h2, h3')].find((el) => /قطع الغيار|spare parts/i.test(el.textContent || ''));
  if (!heading) return;
  const box = document.createElement('div');
  box.dataset.inventorySources = '1';
  box.className = 'inv-sources';
  const label = document.createElement('span');
  label.textContent = t('مصدر القطعة:', 'Part source:');
  box.append(label);
  const options = [[t('من المخزن', 'From warehouse'), 'warehouse'], [t('قطعة من العميل', 'Customer supplied'), 'customer'], [t('شراء مباشر', 'Direct purchase'), 'direct']];
  for (const [text, tab] of options) {
    const a = document.createElement('a');
    a.href = `/inventory.html#/job/${m[1]}?tab=${tab}`;
    a.textContent = text;
    box.append(a);
  }
  heading.after(box);
}

// ---- users page: several roles per user ---------------------------------------------------------------------------------------------
// The compiled Users page edits ONE (primary) role. This adds, under every user and in the "new user" form, check boxes for ADDITIONAL roles.
// A user's permissions are the union of all his roles (enforced by the server). Nothing of the compiled page is modified.
const ROLE_EN = { admin: 'Administrator', manager: 'Workshop manager', receptionist: 'Receptionist', technician: 'Technician', accountant: 'Accountant', storekeeper: 'Storekeeper' };
let roleList = null; let userList = null; let usersLoading = null;
const roleLabel = (r) => (ar ? r.label : (ROLE_EN[r.name] || r.name));

async function loadUsersData(force = false) {
  if (!force && roleList && userList) return;
  if (usersLoading) return usersLoading;
  usersLoading = (async () => {
    try {
      const [r, u] = await Promise.all([fetch('/api/roles', { credentials: 'same-origin' }), fetch('/api/users', { credentials: 'same-origin' })]);
      if (r.ok && u.ok) { roleList = await r.json(); userList = await u.json(); }
    } catch { /* keep the old data */ } finally { usersLoading = null; }
  })();
  return usersLoading;
}

function rolesGroup(primary, selected, { disabled = false, onToggle } = {}) {
  const box = document.createElement('div');
  box.className = 'mr-box'; box.dataset.multiRoles = '1';
  const title = document.createElement('span'); title.className = 'mr-title'; title.textContent = t('أدوار إضافية:', 'Additional roles:');
  box.append(title);
  for (const r of roleList.filter((x) => x.name !== primary)) {
    const label = document.createElement('label'); label.className = 'mr-opt';
    const cb = document.createElement('input'); cb.type = 'checkbox'; cb.value = r.name; cb.checked = selected.includes(r.name); cb.disabled = disabled;
    if (onToggle) cb.addEventListener('change', () => onToggle(cb, box));
    label.append(cb, document.createTextNode(` ${roleLabel(r)}`));
    box.append(label);
  }
  const status = document.createElement('span'); status.className = 'mr-status'; status.setAttribute('role', 'status'); box.append(status);
  return box;
}

function userRows() {
  if (location.pathname !== '/users') return [];
  return [...document.querySelectorAll('main li')].map((li) => {
    const tag = [...li.querySelectorAll('span')].find((s) => /^@[\w.\-]+$/.test((s.textContent || '').trim()));
    return tag ? { li, username: tag.textContent.trim().slice(1) } : null;
  }).filter(Boolean);
}

async function toggleRole(user, box, cb) {
  const status = box.querySelector('.mr-status');
  const chosen = [...box.querySelectorAll('input:checked')].map((x) => x.value);
  box.querySelectorAll('input').forEach((x) => { x.disabled = true; });
  status.textContent = t('جارٍ الحفظ…', 'Saving…'); status.className = 'mr-status';
  try {
    const res = await fetch(`/api/users/${user.id}`, { method: 'PATCH', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      body: JSON.stringify({ roles: [user.role, ...chosen] }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.message || t('تعذّر الحفظ', 'Could not save'));
    await loadUsersData(true);
    renderUserRows(true); // rebuilds the group (it shows "Saved")
    const rebuilt = userRows().find((r) => r.username === user.username)?.li.querySelector(':scope > [data-multi-roles] .mr-status');
    if (rebuilt) { rebuilt.textContent = t('تم الحفظ — سيُطلب من المستخدم تسجيل الدخول من جديد', 'Saved — the user will be asked to sign in again'); rebuilt.className = 'mr-status ok'; }
  } catch (e) {
    cb.checked = !cb.checked; // undo
    box.querySelectorAll('input').forEach((x) => { x.disabled = false; });
    status.textContent = e.message; status.className = 'mr-status bad';
  }
}

function renderUserRows(force = false) {
  if (!roleList || !userList) return;
  for (const { li, username } of userRows()) {
    const user = userList.find((u) => u.username === username);
    if (!user) continue;
    const extras = user.roles.map((r) => r.name).filter((n) => n !== user.role);
    const old = li.querySelector(':scope > [data-multi-roles]');
    const sig = `${user.role}|${extras.join(',')}`;
    if (old && !force && old.dataset.sig === sig) continue;
    old?.remove();
    const box = rolesGroup(user.role, extras, { disabled: username === myUsername, onToggle: (cb, b) => toggleRole(user, b, cb) });
    box.dataset.sig = sig;
    if (username === myUsername) box.title = t('لا يمكنك تغيير أدوارك بنفسك', 'You cannot change your own roles');
    li.append(box);
  }
}

function addNewUserRoles() {
  if (location.pathname !== '/users' || !roleList) return;
  const form = [...document.querySelectorAll('main form')].find((f) => f.querySelector('select') && f.querySelector('input[type="password"]'));
  if (!form) return;
  const select = form.querySelector('select');
  const refresh = (box) => { // the primary role (the form's own select) cannot also be an additional one
    box.querySelectorAll('.mr-opt').forEach((l) => { const cb = l.querySelector('input'); l.hidden = cb.value === select.value; if (l.hidden) cb.checked = false; });
  };
  const existing = form.querySelector('[data-multi-roles]');
  if (existing) { refresh(existing); return; }
  const box = rolesGroup('', [], {});
  box.dataset.newUser = '1';
  select.addEventListener('change', () => refresh(box)); refresh(box);
  const submit = form.querySelector('button[type="submit"]');
  box.classList.add('mr-wide');
  if (submit) submit.before(box); else form.append(box); // right above the "Add" button
}

// the compiled form posts {username, full_name, password, role}: add the additional roles to that request
const nativeFetch = window.fetch.bind(window);
window.fetch = function patchedFetch(input, init) {
  try {
    const url = typeof input === 'string' ? input : input && input.url;
    if (init && init.method === 'POST' && typeof init.body === 'string' && /\/api\/users$/.test(url || '')) {
      const box = document.querySelector('[data-multi-roles][data-new-user]');
      const body = JSON.parse(init.body);
      const extra = box ? [...box.querySelectorAll('input:checked')].map((x) => x.value).filter((n) => n !== body.role) : [];
      if (body.role && extra.length) {
        init = { ...init, body: JSON.stringify({ ...body, roles: [body.role, ...extra] }) };
        return nativeFetch(input, init).then((res) => { if (res.ok) { box.querySelectorAll('input').forEach((x) => { x.checked = false; }); loadUsersData(true).then(() => renderUserRows(true)); } return res; });
      }
    }
  } catch { /* never break the host page */ }
  return nativeFetch(input, init);
};

// A second click on a "create" button while the first request is still running created duplicates (e.g. two identical quotation drafts).
// Clicks on these buttons are ignored for a short time after the first one (capture phase, so the host app never sees the repeat).
const GUARDED = /^(new quotation|create invoice|عرض سعر جديد|إنشاء فاتورة)$/i;
const lastClick = new WeakMap();
document.addEventListener('click', (ev) => {
  const btn = ev.target instanceof Element ? ev.target.closest('button') : null;
  if (!btn || !GUARDED.test((btn.textContent || '').trim())) return;
  const now = Date.now();
  if (now - (lastClick.get(btn) || 0) < 2500) { ev.stopImmediatePropagation(); ev.preventDefault(); return; }
  lastClick.set(btn, now);
}, true);

function injectStyle() {
  if (document.getElementById('inv-integration-css')) return;
  const link = document.createElement('link');
  link.id = 'inv-integration-css';
  link.rel = 'stylesheet';
  link.href = '/assets/inventory/integration.css';
  document.head.append(link);
}

async function start() {
  injectStyle();
  await loadPermissions();
  let scheduled = false;
  const run = () => {
    scheduled = false;
    try {
      addMenuLink(); addPartSourceButtons();
      if (location.pathname === '/users' && has('users.manage')) {
        if (!roleList || !userList || userRows().some((r) => !userList.find((u) => u.username === r.username))) loadUsersData(true).then(() => { renderUserRows(); addNewUserRoles(); });
        else { renderUserRows(); addNewUserRoles(); }
      }
    } catch { /* never break the host page */ }
  };
  // the compiled page changes the PRIMARY role with its own select: refresh our check boxes afterwards
  document.addEventListener('change', (ev) => {
    if (location.pathname === '/users' && ev.target instanceof Element && ev.target.matches('main li select')) setTimeout(() => loadUsersData(true).then(() => renderUserRows(true)), 900);
  }, true);
  new MutationObserver(() => { if (!scheduled) { scheduled = true; setTimeout(run, 150); } }).observe(document.body, { childList: true, subtree: true });
  run();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
