// AutoCare Pro - inventory UI: core (API client, language, DOM helpers, small widgets, router).
// Plain ES modules, no framework and no build step. Everything is rendered with textContent (never innerHTML).

// ---- language ---------------------------------------------------------------------------------------------------------------
const stored = (() => { try { return localStorage.getItem('autocare.lang'); } catch { return null; } })();
export const lang = stored === 'ar' || stored === 'en' ? stored : 'en';
export const isAr = lang === 'ar';
document.documentElement.lang = lang;
document.documentElement.dir = isAr ? 'rtl' : 'ltr';
export const t = (ar, en) => (isAr ? ar : en);
export function setLang(next) {
  try { localStorage.setItem('autocare.lang', next); } catch { /* private mode */ }
  location.reload();
}
// the catalog stores both names: show the one for the interface language
export const itemName = (i) => (isAr ? (i.name_ar || i.name_en) : (i.name_en || i.name_ar)) || '';

// ---- DOM helper ---------------------------------------------------------------------------------------------------------------
export function h(tag, props = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'text') el.textContent = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'value') el.value = v;
    else if (k === 'checked' || k === 'disabled' || k === 'selected' || k === 'required' || k === 'open') el[k] = !!v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  append(el, kids);
  return el;
}
function append(el, kids) {
  for (const k of kids.flat(Infinity)) {
    if (k == null || k === false) continue;
    el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
}
export const clear = (el) => { el.replaceChildren(); return el; };
// like el.append(...) but skips null / false children (the native append would print them as the text "null")
export const put = (el, ...kids) => { append(el, kids); return el; };

// ---- API client ---------------------------------------------------------------------------------------------------------------
let csrf = '';
export let me = null;
export const can = (perm) => !!me && me.permissions.includes(perm);

export class ApiError extends Error {
  constructor(message, status, code) { super(message); this.status = status; this.code = code; }
}
function errorText(body, status) {
  if (body && body.message) return body.message;
  if (body && Array.isArray(body.detail)) return body.detail.map((d) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ');
  return t(`تعذّر تنفيذ الطلب (${status})`, `The request failed (${status})`);
}
export async function api(path, { method = 'GET', body, key, form } = {}) {
  const headers = {};
  if (method !== 'GET') headers['X-CSRF-Token'] = csrf;
  if (key) headers['Idempotency-Key'] = key;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  const res = await fetch(path, { method, headers, body: payload, credentials: 'same-origin' });
  let data = null;
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('json')) data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(errorText(data, res.status), res.status, data && data.error);
  return data;
}
export const get = (p) => api(p);
export const post = (p, body, key) => api(p, { method: 'POST', body, key });
export const patch = (p, body) => api(p, { method: 'PATCH', body });
export const del = (p) => api(p, { method: 'DELETE' });
export const newKey = () => (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random());
export const qs = (obj) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) if (v !== '' && v != null && v !== false) p.set(k, v === true ? 'true' : v);
  const s = p.toString();
  return s ? `?${s}` : '';
};

export async function loadSession() {
  const data = await get('/api/auth/me'); // 401 -> ApiError
  csrf = data.csrf_token;
  me = data.user;
  return me;
}

// ---- feedback --------------------------------------------------------------------------------------------------------------------
let toastHost;
export function toast(message, kind = 'ok') {
  if (!toastHost) { toastHost = h('div', { class: 'toasts', role: 'status', 'aria-live': 'polite' }); document.body.append(toastHost); }
  const el = h('div', { class: `toast ${kind}`, text: message });
  toastHost.append(el);
  setTimeout(() => el.remove(), kind === 'bad' ? 7000 : 3500);
}
// run an action with a busy button; shows the server's message when it fails
export async function guard(button, fn) {
  if (button) button.disabled = true;
  try { return await fn(); } catch (e) { toast(e.message || String(e), 'bad'); return undefined; } finally { if (button) button.disabled = false; }
}

// ---- formatting --------------------------------------------------------------------------------------------------------------------
export const num = (v) => (v == null || v === '' ? '' : String(v).replace(/(\.\d*?[1-9])0+$|\.0+$/, '$1'));
export const when = (v) => (v ? new Date(v).toLocaleString(isAr ? 'ar-QA' : 'en-GB', { dateStyle: 'short', timeStyle: 'short' }) : '');
export const day = (v) => (v ? String(v).slice(0, 10) : '');
export function chip(text, kind = 'idle') { return h('span', { class: `chip ${kind}`, text }); }
const STATUS_KIND = { draft: 'idle', posted: 'work', cancelled: 'bad', none: 'idle', partial: 'wait', full: 'ok', unpaid: 'wait', paid: 'ok', requested: 'idle', ordered: 'work',
  purchased: 'work', received: 'work', installed: 'ok', returned: 'idle', active: 'ok', inactive: 'idle' };
const STATUS_TEXT = {
  draft: ['مسودة', 'Draft'], posted: ['مرحّلة', 'Posted'], cancelled: ['ملغاة', 'Cancelled'], none: ['لم تُستلم', 'Not received'], partial: ['جزئي', 'Partial'],
  full: ['مكتمل', 'Complete'], unpaid: ['غير مدفوعة', 'Unpaid'], paid: ['مدفوعة', 'Paid'], requested: ['مطلوبة', 'Requested'], ordered: ['محجوزة', 'Reserved'],
  purchased: ['محجوزة', 'Reserved'], received: ['مصروفة', 'Issued'], installed: ['مركّبة', 'Installed'], returned: ['مرتجعة', 'Returned'],
};
export const statusChip = (s) => chip(STATUS_TEXT[s] ? t(...STATUS_TEXT[s]) : s, STATUS_KIND[s] || 'idle');
export const TYPE_TEXT = {
  OPENING: ['رصيد افتتاحي', 'Opening balance'], GOODS_RECEIPT: ['استلام بضاعة', 'Goods receipt'], RESERVE: ['حجز', 'Reservation'], RELEASE: ['تحرير حجز', 'Reservation release'],
  ISSUE: ['صرف لأمر إصلاح', 'Issue to repair order'], RETURN_TO_WAREHOUSE: ['إرجاع للمخزن', 'Return to warehouse'], SUPPLIER_RETURN: ['مرتجع للمورد', 'Supplier return'],
  ADJUSTMENT: ['تسوية', 'Adjustment'], COUNT: ['جرد فعلي', 'Physical count'], TRANSFER_OUT: ['تحويل (خروج)', 'Transfer out'], TRANSFER_IN: ['تحويل (دخول)', 'Transfer in'],
  REVERSAL: ['عكس حركة', 'Reversal'],
};
export const typeText = (k) => (TYPE_TEXT[k] ? t(...TYPE_TEXT[k]) : k);

// ---- widgets ------------------------------------------------------------------------------------------------------------------------
export function field(label, input, hint) {
  return h('label', { class: 'field' }, h('span', { class: 'field-label', text: label }), input, hint ? h('small', { class: 'hint', text: hint }) : null);
}
export const input = (props = {}) => h('input', props);
export function select(options, props = {}) {
  const el = h('select', props);
  for (const [value, label] of options) el.append(h('option', { value, text: label, selected: String(value) === String(props.value ?? '') }));
  return el;
}
export function button(label, onClick, kind = 'primary', props = {}) {
  const el = h('button', { type: 'button', class: `btn ${kind}`, ...props }, label);
  if (onClick) el.addEventListener('click', () => guard(el, () => onClick(el)));
  return el;
}
export function card(title, ...kids) { return h('section', { class: 'card' }, title ? h('h2', { text: title }) : null, ...kids); }
export function emptyState(text) { return h('p', { class: 'empty', text }); }

// columns: [{ key | render(row), label, cls }]
export function table(columns, rows, { empty } = {}) {
  if (!rows.length) return emptyState(empty || t('لا توجد بيانات', 'No data'));
  const head = h('tr', {}, columns.map((c) => h('th', { text: c.label, class: c.cls })));
  const body = rows.map((r) => h('tr', {}, columns.map((c) => h('td', { class: c.cls }, c.render ? c.render(r) : (c.num ? num(r[c.key]) : r[c.key] ?? '')))));
  return h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, head), h('tbody', {}, body)));
}

export function pager(total, offset, limit, go) {
  const from = total ? offset + 1 : 0;
  const to = Math.min(offset + limit, total);
  return h('div', { class: 'pager' },
    h('span', { text: t(`عرض ${from}–${to} من ${total}`, `Showing ${from}-${to} of ${total}`) }),
    h('div', {}, button(t('السابق', 'Previous'), () => go(Math.max(0, offset - limit)), 'secondary', { disabled: offset === 0 }),
      button(t('التالي', 'Next'), () => go(offset + limit), 'secondary', { disabled: offset + limit >= total })));
}

// modal dialog: returns { close }. `build(close)` returns the body element.
export function modal(title, build) {
  const dlg = h('dialog', { class: 'modal' });
  const close = () => { dlg.close(); dlg.remove(); };
  dlg.append(h('header', {}, h('h2', { text: title }), h('button', { type: 'button', class: 'icon', 'aria-label': t('إغلاق', 'Close'), onclick: close, text: '✕' })), build(close));
  dlg.addEventListener('cancel', () => dlg.remove());
  document.body.append(dlg);
  dlg.showModal();
  return { close };
}

// search-as-you-type picker over /api/inventory/items. Returns { el, value() -> item | null, set(item) }
export function itemPicker({ onPick, placeholder } = {}) {
  let chosen = null;
  const box = h('input', { type: 'search', placeholder: placeholder || t('ابحث بالكود أو الاسم أو الباركود', 'Search by SKU, name or barcode'), autocomplete: 'off' });
  const list = h('ul', { class: 'suggest', hidden: true });
  const el = h('div', { class: 'picker' }, box, list);
  let timer;
  const show = (items) => {
    clear(list);
    list.hidden = !items.length;
    for (const i of items) {
      const li = h('li', { tabindex: '0' }, h('b', { text: i.sku }), ' ', itemName(i), ' ', h('small', { text: t(`المتاح ${num(i.available)}`, `available ${num(i.available)}`) }));
      const pick = () => { chosen = i; box.value = `${i.sku} — ${itemName(i)}`; list.hidden = true; if (onPick) onPick(i); };
      li.addEventListener('click', pick);
      li.addEventListener('keydown', (e) => { if (e.key === 'Enter') pick(); });
      list.append(li);
    }
  };
  box.addEventListener('input', () => {
    chosen = null;
    clearTimeout(timer);
    const q = box.value.trim();
    if (q.length < 1) { list.hidden = true; return; }
    timer = setTimeout(async () => { try { show((await get(`/api/inventory/items${qs({ q, active: true, limit: 8 })}`)).items); } catch { list.hidden = true; } }, 200);
  });
  document.addEventListener('click', (e) => { if (!el.contains(e.target)) list.hidden = true; });
  return { el, value: () => chosen, set(i) { chosen = i; box.value = i ? `${i.sku} — ${itemName(i)}` : ''; } };
}

// ---- router -----------------------------------------------------------------------------------------------------------------------
const routes = [];
export function route(pattern, render, { title, perm } = {}) { routes.push({ pattern, render, title, perm }); }
export function parseHash() {
  const raw = location.hash.replace(/^#/, '') || '/dashboard';
  const [path, query = ''] = raw.split('?');
  return { path, query: Object.fromEntries(new URLSearchParams(query)) };
}
// navigate; when the hash is unchanged (e.g. after saving) re-render the current screen so fresh data is shown
export const go = (hash) => {
  const target = hash.startsWith('#') ? hash : `#${hash}`;
  if (location.hash === target) window.dispatchEvent(new HashChangeEvent('hashchange'));
  else location.hash = target;
};
export function startRouter(container, onChange) {
  let current = 0; // only the latest render may touch the page (overlapping renders used to duplicate the screen)
  async function render() {
    const mine = ++current;
    const { path, query } = parseHash();
    for (const r of routes) {
      const m = path.match(r.pattern);
      if (!m) continue;
      onChange(path);
      clear(container);
      if (r.perm && !can(r.perm)) { container.append(card(null, emptyState(t('ليست لديك صلاحية لهذه الشاشة', 'You do not have permission for this screen')))); return; }
      const box = h('div', { class: 'screen' });
      try { await r.render(box, { params: m.slice(1), query }); } catch (e) { clear(box); box.append(card(null, h('p', { class: 'error', text: e.message || String(e) }))); }
      if (mine !== current) return; // a newer navigation took over
      clear(container).append(box);
      return;
    }
    onChange(path);
    clear(container).append(card(null, emptyState(t('الصفحة غير موجودة', 'Page not found'))));
  }
  window.addEventListener('hashchange', render);
  return render();
}
