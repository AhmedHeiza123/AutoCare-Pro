// Inventory UI: dashboard, spare-parts catalog, stock balances, valuation, low-stock alerts, reports.
import { t, h, clear, get, post, patch, qs, can, num, itemName, chip, button, field, input, select, card, table, pager, modal, toast, go, newKey, isAr, day, me, when, typeText, emptyState } from './core.js';

// ---- dashboard ---------------------------------------------------------------------------------------------------------------
const SVG_NS = 'http://www.w3.org/2000/svg';
function svgEl(tag, attrs = {}, ...kids) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  for (const k of kids) if (k != null) el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  return el;
}
const ICONS = {
  items: ['M21 8l-9-5-9 5v8l9 5 9-5V8z', 'M3 8l9 5 9-5', 'M12 13v8'],
  qty: ['M12 3l9 5-9 5-9-5 9-5z', 'M3 12.5l9 5 9-5', 'M3 17l9 5 9-5'],
  value: ['M12 3a9 9 0 100 18 9 9 0 000-18z', 'M12 7v10', 'M9.5 9.6c0-1 1-1.8 2.5-1.8s2.5.8 2.5 1.8-1 1.6-2.5 1.9-2.5.9-2.5 1.9 1 1.8 2.5 1.8 2.5-.8 2.5-1.8'],
  low: ['M12 3l10 18H2L12 3z', 'M12 10v5', 'M12 18h.01'],
  out: ['M12 3a9 9 0 100 18 9 9 0 000-18z', 'M9 9l6 6', 'M15 9l-6 6'],
  received: ['M12 3v12', 'M7 10l5 5 5-5', 'M4 20h16'],
  issued: ['M12 15V3', 'M7 8l5-5 5 5', 'M4 20h16'],
  purchases: ['M6 3h12v18l-3-2-3 2-3-2-3 2V3z', 'M9 8h6', 'M9 12h6'],
};
const icon = (name) => svgEl('svg', { viewBox: '0 0 24 24', width: 26, height: 26, fill: 'none', stroke: 'currentColor', 'stroke-width': 1.8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', focusable: 'false' },
  ...ICONS[name].map((d) => svgEl('path', { d })));
const LOCALE = isAr ? 'ar-QA' : 'en-GB';
// the isolate characters keep the day/month/year order of a date intact inside right-to-left text
const fmtDate = (iso) => (iso ? `⁦${new Date(`${iso}T00:00:00`).toLocaleDateString(LOCALE, { day: '2-digit', month: '2-digit', year: 'numeric' })}⁩` : '');
const monthLabel = (y, m) => new Date(y, m - 1, 1).toLocaleDateString(LOCALE, { month: 'short', year: '2-digit' });
const iso = (y, m, d) => `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

// the last `count` calendar months ending in the month of `toIso` (the newest one stops at that date)
function lastMonths(toIso, count) {
  let y = Number(toIso.slice(0, 4)); let m = Number(toIso.slice(5, 7)); const out = [];
  for (let i = 0; i < count; i += 1) {
    const lastDay = new Date(y, m, 0).getDate();
    out.unshift({ y, m, from: iso(y, m, 1), to: i === 0 ? toIso : iso(y, m, lastDay), label: monthLabel(y, m) });
    m -= 1; if (m === 0) { y -= 1; m = 12; }
  }
  return out;
}

function barChart(months, received, issued) {
  const W = 560; const H = 230; const padL = 36; const padB = 34; const padT = 18; const plotH = H - padB - padT;
  const max = Math.max(1, ...received, ...issued);
  const slot = (W - padL - 8) / months.length; const bw = Math.min(26, slot / 2.6);
  const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, class: 'chart', role: 'img', dir: 'ltr',
    'aria-label': t('الكميات المستلمة مقابل المصروفة شهرياً', 'Stock received versus issued per month') });
  svg.append(svgEl('line', { x1: padL, y1: padT + plotH, x2: W - 4, y2: padT + plotH, class: 'axis' }));
  [0, 0.5, 1].forEach((f) => {
    const y = padT + plotH - plotH * f;
    svg.append(svgEl('line', { x1: padL, y1: y, x2: W - 4, y2: y, class: 'grid' }), svgEl('text', { x: padL - 6, y: y + 4, class: 'tick', 'text-anchor': 'end' }, num(Math.round(max * f * 10) / 10)));
  });
  months.forEach((mo, i) => {
    const cx = padL + slot * i + slot / 2;
    [[received[i], 'rec', -bw - 2], [issued[i], 'iss', 2]].forEach(([v, cls, dx]) => {
      const hgt = Math.max(v > 0 ? 2 : 0, (v / max) * plotH);
      svg.append(svgEl('rect', { x: cx + dx, y: padT + plotH - hgt, width: bw, height: hgt, rx: 3, class: `bar ${cls}` }, svgEl('title', {}, `${mo.label}: ${num(v)}`)));
      if (v > 0) svg.append(svgEl('text', { x: cx + dx + bw / 2, y: padT + plotH - hgt - 4, class: 'val', 'text-anchor': 'middle' }, num(v)));
    });
    svg.append(svgEl('text', { x: cx, y: H - 12, class: 'tick', 'text-anchor': 'middle' }, mo.label));
  });
  return svg;
}

function lineChart(points) {
  const W = 560; const H = 230; const padL = 52; const padB = 34; const padT = 18; const plotH = H - padB - padT;
  const vals = points.map((p) => Number(p.value));
  const max = Math.max(1, ...vals); const min = Math.min(0, ...vals);
  const x = (i) => padL + ((W - padL - 16) * (points.length === 1 ? 0.5 : i / (points.length - 1)));
  const y = (v) => padT + plotH - ((v - min) / (max - min || 1)) * plotH;
  const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, class: 'chart', role: 'img', dir: 'ltr', 'aria-label': t('اتجاه قيمة المخزون في نهاية كل شهر', 'Inventory value at the end of each month') });
  [0, 0.5, 1].forEach((f) => {
    const v = min + (max - min) * f; const yy = y(v);
    svg.append(svgEl('line', { x1: padL, y1: yy, x2: W - 8, y2: yy, class: f === 0 ? 'axis' : 'grid' }), svgEl('text', { x: padL - 6, y: yy + 4, class: 'tick', 'text-anchor': 'end' }, Math.round(v).toLocaleString(LOCALE)));
  });
  svg.append(svgEl('polyline', { points: vals.map((v, i) => `${x(i)},${y(v)}`).join(' '), class: 'trend' }));
  points.forEach((p, i) => {
    svg.append(svgEl('circle', { cx: x(i), cy: y(vals[i]), r: 4.5, class: 'dot' }, svgEl('title', {}, `${p.label}: ${p.value}`)),
      svgEl('text', { x: x(i), y: y(vals[i]) - 9, class: 'val', 'text-anchor': 'middle' }, Math.round(vals[i]).toLocaleString(LOCALE)),
      svgEl('text', { x: x(i), y: H - 12, class: 'tick', 'text-anchor': 'middle' }, p.label));
  });
  return svg;
}

export async function dashboard(box, { query }) {
  const d = await get(`/api/inventory/dashboard${qs({ date_from: query.date_from, date_to: query.date_to })}`);
  const defaultFrom = d.period.from; const defaultTo = d.period.to;
  const from = input({ type: 'date', value: query.date_from || defaultFrom, 'aria-label': t('من تاريخ', 'From date') });
  const to = input({ type: 'date', value: query.date_to || defaultTo, 'aria-label': t('إلى تاريخ', 'To date') });
  const msg = h('p', { class: 'error form-msg', role: 'alert', hidden: true });
  const apply = () => {
    msg.hidden = true;
    if (!from.value || !to.value) { msg.textContent = t('اختر تاريخ البداية والنهاية.', 'Choose both a start and an end date.'); msg.hidden = false; return; }
    if (from.value > to.value) { msg.textContent = t('تاريخ البداية يجب أن يسبق تاريخ النهاية.', 'The start date must not be after the end date.'); msg.hidden = false; return; }
    go(`/dashboard?date_from=${from.value}&date_to=${to.value}`);
  };
  const from0 = from.value; const to0 = to.value;
  const period = `date_from=${encodeURIComponent(from0)}&date_to=${encodeURIComponent(to0)}`;
  const qtyUnit = t('قطعة', 'pcs'); const money = t('ر.ق', 'QAR');
  const defs = [
    ['total_items', t('عدد الأصناف', 'Total spare parts'), d.total_items, t('صنف', 'items'), '/items?active=true', 'items'],
    ['total_stock_qty', t('إجمالي كمية المخزون', 'Total stock quantity'), num(d.total_stock_qty), qtyUnit, '/balances?only_stock=true', 'qty'],
    ['inventory_value', t('قيمة المخزون', 'Inventory value'), d.inventory_value, money, '/valuation', 'value'],
    ['low_stock_items', t('أصناف قاربت على النفاد', 'Low-stock items'), d.low_stock_items, t('صنف', 'items'), '/low-stock', 'low'],
    ['out_of_stock_items', t('أصناف نفدت', 'Out-of-stock items'), d.out_of_stock_items, t('صنف', 'items'), '/items?stock=out', 'out'],
    ['stock_received', t('الكمية المستلمة (الفترة)', 'Stock received (period)'), num(d.stock_received), qtyUnit, '/movements?type=GOODS_RECEIPT', 'received'],
    ['stock_issued', t('الكمية المصروفة (الفترة)', 'Stock issued (period)'), num(d.stock_issued), qtyUnit, '/movements?type=ISSUE', 'issued'],
    ['inventory_purchases', t('مشتريات المخزون (الفترة)', 'Inventory purchases (period)'), d.inventory_purchases, money, '/purchases?status=posted', 'purchases'],
  ].filter(([key]) => d[key] !== undefined);
  const PERIOD_KEYS = ['stock_received', 'stock_issued', 'inventory_purchases'];
  box.classList.add('dash-screen'); // spacing between the filter, the KPI cards and the widgets (this screen only)

  const transactions = h('div', {}, emptyState(t('جارٍ التحميل…', 'Loading…')));
  const alerts = h('div', {}, emptyState(t('جارٍ التحميل…', 'Loading…')));
  const flow = h('div', {}, emptyState(t('جارٍ التحميل…', 'Loading…')));
  const trendBox = can('inventory.costs') ? h('div', {}, emptyState(t('جارٍ التحميل…', 'Loading…'))) : null;

  box.append(
    card(null, h('div', { class: 'toolbar' },
      field(t('من', 'From'), from), field(t('إلى', 'To'), to),
      h('div', { class: 'toolbar-actions' }, button(t('تطبيق', 'Apply'), apply, 'primary'), button(t('إعادة ضبط', 'Reset'), () => go('/dashboard'), 'secondary'))),
      msg,
      h('p', { class: 'hint period-note' }, t(`الفترة المعروضة: ${fmtDate(from0)} – ${fmtDate(to0)}. الأرصدة والقيمة الحالية مستقلة عن الفترة، وتتأثر بها الكميات المستلمة والمصروفة والمشتريات فقط. الكمية المصروفة صافية بعد خصم المرتجع للمخزن.`,
        `Showing ${fmtDate(from0)} – ${fmtDate(to0)}. Current balances and value do not depend on the period; only received, issued and purchases do. Issued is net of returns to the warehouse.`))),
    h('div', { class: 'dash-kpis' }, defs.map(([key, label, value, unit, target, ic]) => {
      const withPeriod = PERIOD_KEYS.includes(key);
      return h('a', { class: `dash-kpi k-${ic}`, href: `#${target}${withPeriod ? (target.includes('?') ? '&' : '?') + period : ''}`, 'aria-label': `${label}: ${value} ${unit}. ${t('اضغط لعرض التفاصيل', 'Open the details')}` },
        h('span', { class: 'kpi-icon' }, icon(ic)),
        h('span', { class: 'kpi-label', text: label }),
        h('span', { class: 'kpi-figure' }, h('strong', { text: String(value) }), h('em', { text: unit })),
        h('small', { class: 'kpi-more', text: t('عرض التفاصيل ←', 'View details →') }));
    })),
    h('div', { class: 'dash-grid' },
      card(t('آخر حركات المخزون', 'Recent inventory transactions'), transactions),
      card(t('تنبيهات المخزون', 'Stock alerts'), alerts),
      card(t('الاستلام مقابل الصرف شهرياً', 'Monthly stock received vs issued'), flow),
      trendBox ? card(t('اتجاه قيمة المخزون', 'Inventory value trend'), trendBox) : null),
  );

  // widgets load after the page is shown; a failure in one never breaks the others
  const fill = async (target, fn) => { try { const el = await fn(); clear(target).append(el); } catch (e) { clear(target).append(h('p', { class: 'error', text: e.message || String(e) })); } };

  fill(transactions, async () => {
    const r = await get('/api/inventory/movements?limit=8&offset=0');
    if (!r.items.length) return emptyState(t('لا توجد حركات بعد', 'No transactions yet'));
    return h('div', {}, table([
      { label: t('الوقت', 'When'), render: (m) => when(m.ts) },
      { label: t('الحركة', 'Type'), render: (m) => typeText(m.type) },
      { label: t('الصنف', 'Item'), render: (m) => h('span', {}, h('b', { text: m.sku || '' }), ' ', m.item_name || '') },
      { label: t('الكمية', 'Qty'), cls: 'n', render: (m) => h('span', { class: Number(m.qty) < 0 ? 'neg' : Number(m.qty) > 0 ? 'pos' : 'muted', text: `${Number(m.qty) > 0 ? '+' : ''}${num(m.qty)}` }) },
      { label: t('الرصيد بعد', 'After'), key: 'on_hand_after', num: true, cls: 'n' },
    ], r.items), h('p', { class: 'more' }, h('a', { href: `#/movements?${period}`, text: t('كل الحركات ←', 'All transactions →') })));
  });

  fill(alerts, async () => {
    const [low, out] = await Promise.all([get('/api/inventory/low-stock'), get('/api/inventory/items?out_of_stock=true&limit=6&offset=0')]);
    const lowRows = low.filter((r) => Number(r.on_hand) > 0).slice(0, 6);
    if (!lowRows.length && !out.items.length) return h('p', { class: 'empty ok-note', text: t('لا توجد أصناف منخفضة أو نافدة.', 'No low-stock or out-of-stock items.') });
    const row = (it, kind) => h('li', {}, h('a', { href: `#/movements?item_id=${it.item_id || it.id}` }, h('b', { text: it.sku }), ' ', itemName(it)),
      h('span', { class: 'alert-qty' }, kind === 'out' ? chip(t('نفد', 'Out'), 'bad') : chip(`${num(it.on_hand)} / ${num(it.min_stock)}`, 'wait')));
    return h('div', {}, out.items.length ? h('h3', { text: t('نافدة', 'Out of stock') }) : null, out.items.length ? h('ul', { class: 'alert-list' }, out.items.map((i) => row(i, 'out'))) : null,
      lowRows.length ? h('h3', { text: t('منخفضة (الرصيد / الحد الأدنى)', 'Low (on hand / minimum)') }) : null, lowRows.length ? h('ul', { class: 'alert-list' }, lowRows.map((i) => row(i, 'low'))) : null,
      h('p', { class: 'more' }, h('a', { href: '#/low-stock', text: t('كل التنبيهات ←', 'All alerts →') })));
  });

  fill(flow, async () => {
    const months = lastMonths(to0, 6);
    const rows = await Promise.all(months.map((mo) => get(`/api/inventory/dashboard${qs({ date_from: mo.from, date_to: mo.to })}`)));
    const rec = rows.map((r) => Number(r.stock_received)); const iss = rows.map((r) => Number(r.stock_issued));
    if (rec.every((v) => v === 0) && iss.every((v) => v === 0)) return emptyState(t('لا توجد حركات استلام أو صرف في آخر 6 أشهر.', 'No receipts or issues in the last 6 months.'));
    return h('div', {}, barChart(months, rec, iss),
      h('div', { class: 'legend' }, h('span', {}, h('i', { class: 'sw rec' }), t('مستلم', 'Received')), h('span', {}, h('i', { class: 'sw iss' }), t('مصروف', 'Issued'))));
  });

  if (trendBox) {
    fill(trendBox, async () => {
      const r = await get(`/api/inventory/valuation-trend${qs({ months: 6, date_to: to0 })}`);
      const pts = r.points.map((p) => ({ ...p, label: (() => { const [yy, mm] = p.month.split('-').map(Number); return monthLabel(yy, mm); })() }));
      if (pts.every((p) => Number(p.value) === 0)) return emptyState(t('لا توجد قيمة مخزون مسجلة بعد.', 'No inventory value recorded yet.'));
      return h('div', {}, lineChart(pts), h('p', { class: 'hint', text: t('القيمة في نهاية كل شهر محسوبة من سجل حركات المخزون.', 'Value at the end of each month, taken from the stock ledger.') }));
    });
  }
}

// ---- catalog -------------------------------------------------------------------------------------------------------------------
async function suppliers() { try { return await get('/api/suppliers?active=true'); } catch { return []; } }

export async function items(box, { query }) {
  const limit = 25;
  const offset = Number(query.offset || 0);
  const cats = await get('/api/inventory/categories');
  const stock = query.stock || (query.low_stock ? 'low' : query.out_of_stock ? 'out' : '');
  const params = { q: query.q, category_id: query.category_id, active: query.active, low_stock: stock === 'low', out_of_stock: stock === 'out', in_stock: stock === 'in', limit, offset };
  const data = await get(`/api/inventory/items${qs(params)}`);
  const catName = (id) => { const c = cats.find((x) => x.id === id); return c ? (isAr ? c.name_ar : c.name_en) : ''; };
  const q = input({ type: 'search', value: query.q || '', placeholder: t('كود أو اسم أو باركود', 'SKU, name or barcode') });
  const cat = select([['', t('كل التصنيفات', 'All categories')], ...cats.filter((c) => !c.parent_id).map((c) => [c.id, isAr ? c.name_ar : c.name_en])], { value: query.category_id || '' });
  const act = select([['', t('الكل', 'All')], ['true', t('مفعّل', 'Active')], ['false', t('موقوف', 'Inactive')]], { value: query.active || '' });
  const stk = select([['', t('كل الأرصدة', 'Any stock')], ['low', t('قارب على النفاد', 'Low stock')], ['out', t('نفد', 'Out of stock')], ['in', t('متوفر', 'In stock')]], { value: stock });
  const apply = () => go(`/items${qs({ q: q.value, category_id: cat.value, active: act.value, stock: stk.value })}`);
  const costs = data.items.length && data.items[0].avg_cost !== undefined;
  const cols = [
    { label: t('الكود', 'SKU'), render: (r) => h('b', { text: r.sku }) },
    { label: t('الصنف', 'Item'), render: (r) => h('span', {}, itemName(r), r.brand ? h('small', { class: 'muted', text: `  ${r.brand}` }) : null) },
    { label: t('التصنيف', 'Category'), render: (r) => catName(r.category_id) },
    { label: t('الرصيد', 'On hand'), key: 'on_hand', num: true, cls: 'n' },
    { label: t('المحجوز', 'Reserved'), key: 'reserved', num: true, cls: 'n' },
    { label: t('المتاح', 'Available'), key: 'available', num: true, cls: 'n' },
    { label: t('الحد الأدنى', 'Min'), key: 'min_stock', num: true, cls: 'n' },
    { label: t('سعر البيع', 'Selling price'), key: 'selling_price', cls: 'n' },
    ...(costs ? [{ label: t('متوسط التكلفة', 'Avg cost'), key: 'avg_cost', cls: 'n' }, { label: t('القيمة', 'Value'), key: 'stock_value', cls: 'n' }] : []),
    { label: t('الحالة', 'Status'), render: (r) => (!r.is_active ? chip(t('موقوف', 'Inactive')) : r.out_of_stock ? chip(t('نفد', 'Out'), 'bad') : r.low_stock ? chip(t('منخفض', 'Low'), 'wait') : chip(t('متوفر', 'OK'), 'ok')) },
    { label: '', render: (r) => h('div', { class: 'row-actions' }, h('a', { href: `#/movements?item_id=${r.id}`, text: t('الحركات', 'Movements') }),
      can('inventory.write') ? button(t('تعديل', 'Edit'), () => itemForm(r, cats, done), 'secondary') : null) },
  ];
  const done = () => go(location.hash.replace(/^#/, '') || '/items');
  box.append(card(null,
    h('div', { class: 'toolbar' }, field(t('بحث', 'Search'), q), field(t('التصنيف', 'Category'), cat), field(t('الحالة', 'Status'), act), field(t('المخزون', 'Stock'), stk),
      button(t('بحث', 'Search'), apply, 'secondary'),
      can('inventory.write') ? button(t('+ صنف جديد', '+ New item'), () => itemForm(null, cats, done)) : null,
      can('inventory.write') ? button(t('التصنيفات', 'Categories'), () => categoriesModal(cats, done), 'secondary') : null),
    table(cols, data.items.map((i) => i), { empty: t('لا توجد أصناف مطابقة', 'No matching items') }),
    pager(data.total, offset, limit, (o) => go(`/items${qs({ ...query, offset: o || '' })}`))));
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') apply(); });
}

function categoriesModal(cats, done) {
  modal(t('تصنيفات المخزون', 'Inventory categories'), (close) => {
    const en = input({ required: true }); const ar = input({ required: true, dir: 'rtl' });
    const parent = select([['', t('تصنيف رئيسي', 'Top-level category')], ...cats.filter((c) => !c.parent_id).map((c) => [c.id, isAr ? c.name_ar : c.name_en])]);
    const list = h('ul', { class: 'plain' }, cats.map((c) => h('li', { text: `${c.parent_id ? '↳ ' : ''}${isAr ? c.name_ar : c.name_en}  (${isAr ? c.name_en : c.name_ar})` })));
    return h('div', { class: 'modal-body' }, list.children.length ? list : h('p', { class: 'empty', text: t('لا توجد تصنيفات بعد', 'No categories yet') }),
      h('div', { class: 'grid2' }, field('English', en), field('العربية', ar), field(t('يتبع', 'Parent'), parent)),
      h('div', { class: 'actions' }, button(t('إضافة تصنيف', 'Add category'), async () => {
        await post('/api/inventory/categories', { name_en: en.value, name_ar: ar.value, parent_id: parent.value ? Number(parent.value) : null });
        toast(t('تمت إضافة التصنيف', 'Category added')); close(); done();
      })));
  });
}

async function itemForm(item, cats, done) {
  const sups = await suppliers();
  const costs = !item || item.purchase_price !== undefined;
  const f = {
    sku: input({ value: item?.sku || '', required: true, disabled: !!item, maxlength: 60 }),
    name_en: input({ value: item?.name_en || '', required: true }), name_ar: input({ value: item?.name_ar || '', dir: 'rtl' }),
    category_id: select([['', '—'], ...cats.filter((c) => !c.parent_id).map((c) => [c.id, isAr ? c.name_ar : c.name_en])], { value: item?.category_id ?? '' }),
    subcategory_id: select([['', '—'], ...cats.filter((c) => c.parent_id).map((c) => [c.id, isAr ? c.name_ar : c.name_en])], { value: item?.subcategory_id ?? '' }),
    brand: input({ value: item?.brand || '' }), manufacturer: input({ value: item?.manufacturer || '' }),
    mfr_part_no: input({ value: item?.mfr_part_no || '' }), oem_part_no: input({ value: item?.oem_part_no || '' }), barcode: input({ value: item?.barcode || '' }),
    uom: input({ value: item?.uom || 'pcs' }),
    default_supplier_id: select([['', '—'], ...sups.map((s) => [s.id, s.name])], { value: item?.default_supplier_id ?? '' }),
    purchase_price: input({ type: 'number', step: '0.0001', min: '0', value: item?.purchase_price ?? '0' }),
    selling_price: input({ type: 'number', step: '0.01', min: '0', value: item?.selling_price ?? '0' }),
    min_stock: input({ type: 'number', step: '0.001', min: '0', value: num(item?.min_stock ?? '0') }), reorder_qty: input({ type: 'number', step: '0.001', min: '0', value: num(item?.reorder_qty ?? '0') }),
    storage_location: input({ value: item?.storage_location || '' }),
    compatibility: input({ value: (item?.compatibility || []).join(', '), placeholder: t('مثال: Toyota Camry 2018-2022, Honda Accord', 'e.g. Toyota Camry 2018-2022, Honda Accord') }),
    notes: h('textarea', { rows: 2 }, item?.notes || ''),
    is_active: input({ type: 'checkbox', checked: item ? item.is_active : true }),
  };
  modal(item ? t('تعديل صنف', 'Edit item') : t('صنف جديد', 'New item'), (close) => {
    const body = () => {
      const val = (k) => (typeof f[k].value === 'string' ? f[k].value.trim() : f[k].value);
      const out = { name_en: val('name_en'), name_ar: val('name_ar') || null, category_id: val('category_id') ? Number(val('category_id')) : null,
        subcategory_id: val('subcategory_id') ? Number(val('subcategory_id')) : null, brand: val('brand') || null, manufacturer: val('manufacturer') || null,
        mfr_part_no: val('mfr_part_no') || null, oem_part_no: val('oem_part_no') || null, barcode: val('barcode') || null, uom: val('uom') || 'pcs',
        default_supplier_id: val('default_supplier_id') ? Number(val('default_supplier_id')) : null, selling_price: val('selling_price') || '0',
        min_stock: val('min_stock') || '0', reorder_qty: val('reorder_qty') || '0', storage_location: val('storage_location') || null,
        compatibility: val('compatibility') ? val('compatibility').split(',').map((s) => s.trim()).filter(Boolean) : null, notes: val('notes') || null };
      if (costs) out.purchase_price = val('purchase_price') || '0';
      return out;
    };
    return h('div', { class: 'modal-body' },
      h('div', { class: 'grid3' },
        field(t('كود الصنف (SKU)', 'SKU'), f.sku), field(t('الاسم بالإنجليزية', 'Name (English)'), f.name_en), field(t('الاسم بالعربية', 'Name (Arabic)'), f.name_ar),
        field(t('التصنيف', 'Category'), f.category_id), field(t('التصنيف الفرعي', 'Subcategory'), f.subcategory_id), field(t('الماركة', 'Brand'), f.brand),
        field(t('الشركة المصنّعة', 'Manufacturer'), f.manufacturer), field(t('رقم المصنّع', 'Manufacturer part no.'), f.mfr_part_no), field(t('رقم OEM', 'OEM part no.'), f.oem_part_no),
        field(t('الباركود (اختياري)', 'Barcode (optional)'), f.barcode), field(t('وحدة القياس', 'Unit of measure'), f.uom), field(t('المورد الافتراضي', 'Default supplier'), f.default_supplier_id),
        costs ? field(t('سعر الشراء المرجعي', 'Reference purchase price'), f.purchase_price) : null, field(t('سعر البيع', 'Selling price'), f.selling_price),
        field(t('الحد الأدنى للمخزون', 'Minimum stock'), f.min_stock), field(t('كمية إعادة الطلب', 'Reorder quantity'), f.reorder_qty), field(t('مكان التخزين', 'Storage location'), f.storage_location)),
      field(t('توافق المركبات (اختياري)', 'Vehicle compatibility (optional)'), f.compatibility), field(t('ملاحظات', 'Notes'), f.notes),
      item ? h('label', { class: 'check' }, f.is_active, ' ', t('مفعّل', 'Active')) : null,
      h('div', { class: 'actions' }, button(t('حفظ', 'Save'), async () => {
        const payload = body();
        if (item) { await patch(`/api/inventory/items/${item.id}`, { ...payload, is_active: f.is_active.checked }); } else { await post('/api/inventory/items', { sku: f.sku.value.trim(), ...payload }); }
        toast(t('تم الحفظ', 'Saved')); close(); done();
      }), button(t('إلغاء', 'Cancel'), close, 'secondary')));
  });
}

// ---- balances ------------------------------------------------------------------------------------------------------------------
export async function balances(box, { query }) {
  const whs = await get('/api/inventory/warehouses');
  const wh = select([['', t('كل المخازن', 'All warehouses')], ...whs.map((w) => [w.id, isAr ? w.name_ar : w.name_en])], { value: query.warehouse_id || '' });
  const only = input({ type: 'checkbox', checked: query.only_stock !== 'false' });
  const rows = await get(`/api/inventory/balances${qs({ warehouse_id: query.warehouse_id, only_stock: query.only_stock !== 'false' })}`);
  const costs = rows.length && rows[0].avg_cost !== undefined;
  const cols = [{ label: t('الكود', 'SKU'), key: 'sku' }, { label: t('الصنف', 'Item'), render: (r) => itemName(r) }, { label: t('المخزن', 'Warehouse'), key: 'warehouse' },
    { label: t('الرصيد', 'On hand'), key: 'on_hand', num: true, cls: 'n' }, { label: t('المحجوز', 'Reserved'), key: 'reserved', num: true, cls: 'n' },
    { label: t('المتاح', 'Available'), key: 'available', num: true, cls: 'n' }, { label: t('الحد الأدنى', 'Min'), key: 'min_stock', num: true, cls: 'n' },
    ...(costs ? [{ label: t('متوسط التكلفة', 'Avg cost'), key: 'avg_cost', cls: 'n' }, { label: t('القيمة', 'Value'), key: 'value', cls: 'n' }] : [])];
  box.append(card(null, h('div', { class: 'toolbar' }, field(t('المخزن', 'Warehouse'), wh), h('label', { class: 'check' }, only, ' ', t('الأصناف التي بها رصيد فقط', 'Only items with stock')),
    button(t('تطبيق', 'Apply'), () => go(`/balances${qs({ warehouse_id: wh.value, only_stock: only.checked ? '' : 'false' })}`), 'secondary'),
    can('inventory.adjust') ? button(t('+ رصيد افتتاحي', '+ Opening balance'), () => openingForm(whs, () => go('/balances'))) : null),
    table(cols, rows, { empty: t('لا توجد أرصدة', 'No balances') })));
}

function openingForm(whs, done) {
  modal(t('رصيد افتتاحي', 'Opening balance'), (close) => {
    const picker = itemPicker();
    const wh = select(whs.map((w) => [w.id, isAr ? w.name_ar : w.name_en]));
    const qty = input({ type: 'number', step: '0.001', min: '0.001' }); const cost = input({ type: 'number', step: '0.0001', min: '0' });
    return h('div', { class: 'modal-body' }, field(t('الصنف', 'Item'), picker.el), h('div', { class: 'grid3' }, field(t('المخزن', 'Warehouse'), wh), field(t('الكمية', 'Quantity'), qty), field(t('تكلفة الوحدة', 'Unit cost'), cost)),
      h('p', { class: 'hint', text: t('يُسجَّل مرة واحدة لكل صنف في كل مخزن؛ التصحيح لاحقًا بتسوية.', 'Recorded once per item and warehouse; correct it later with an adjustment.') }),
      h('div', { class: 'actions' }, button(t('حفظ', 'Save'), async () => {
        const item = picker.value(); if (!item) throw new Error(t('اختر الصنف', 'Choose an item'));
        await post('/api/inventory/opening-balances', { item_id: item.id, warehouse_id: Number(wh.value), qty: qty.value, unit_cost: cost.value }, newKey());
        toast(t('تم تسجيل الرصيد الافتتاحي', 'Opening balance recorded')); close(); done();
      })));
  });
}

// ---- valuation -----------------------------------------------------------------------------------------------------------------
export async function valuation(box) {
  const d = await get('/api/inventory/valuation');
  box.append(card(null, h('div', { class: 'kpis one' }, h('div', { class: 'kpi static' }, h('span', { class: 'kpi-label', text: t('إجمالي قيمة المخزون', 'Total inventory value') }), h('strong', { text: d.total_value }),
    h('small', { text: t('طريقة التقييم: المتوسط المرجّح المستمر', 'Method: perpetual weighted average') }))),
  table([{ label: t('الكود', 'SKU'), key: 'sku' }, { label: t('الصنف', 'Item'), render: (r) => itemName(r) }, { label: t('الكمية', 'Qty'), key: 'on_hand', num: true, cls: 'n' },
    { label: t('متوسط التكلفة', 'Avg cost'), key: 'avg_cost', cls: 'n' }, { label: t('القيمة', 'Value'), key: 'value', cls: 'n' }], d.items, { empty: t('لا يوجد مخزون', 'No stock') })));
}

// ---- low stock -----------------------------------------------------------------------------------------------------------------
export async function lowStock(box) {
  const rows = await get('/api/inventory/low-stock');
  const cols = [{ label: t('الكود', 'SKU'), key: 'sku' }, { label: t('الصنف', 'Item'), render: (r) => itemName(r) }, { label: t('الرصيد', 'On hand'), key: 'on_hand', num: true, cls: 'n' },
    { label: t('المتاح', 'Available'), key: 'available', num: true, cls: 'n' }, { label: t('الحد الأدنى', 'Min'), key: 'min_stock', num: true, cls: 'n' },
    { label: t('المقترح طلبه', 'Suggested order'), key: 'suggested_order', num: true, cls: 'n' }];
  const makeDraft = async () => {
    const sups = await suppliers();
    modal(t('مسودة فاتورة مشتريات', 'Draft purchase invoice'), (close) => {
      const supplier = select(sups.map((s) => [s.id, s.name]), { value: rows.find((r) => r.default_supplier_id)?.default_supplier_id ?? '' });
      return h('div', { class: 'modal-body' }, field(t('المورد', 'Supplier'), supplier),
        h('p', { class: 'hint', text: t('ستُفتح شاشة الفاتورة بالأصناف المنخفضة والكميات المقترحة لتراجعها وتضيف الأسعار.', 'The invoice form opens with the low-stock items and suggested quantities; add the costs and review.') }),
        h('div', { class: 'actions' }, button(t('متابعة', 'Continue'), async () => {
          sessionStorage.setItem('inv.draft', JSON.stringify({ supplier_id: Number(supplier.value), lines: rows.map((r) => ({ item_id: r.item_id, sku: r.sku, name: itemName(r), qty: r.suggested_order })) }));
          close(); go('/purchases/new');
        })));
    });
  };
  box.append(card(null, h('div', { class: 'toolbar' }, h('p', { class: 'muted', text: t(`${rows.length} صنف يحتاج إعادة طلب`, `${rows.length} item(s) need reordering`) }),
    can('purchasing.write') && rows.length ? button(t('إنشاء مسودة فاتورة مشتريات', 'Create purchase draft'), makeDraft) : null), table(cols, rows, { empty: t('لا توجد أصناف منخفضة المخزون', 'No low-stock items') })));
}

// ---- reports ---------------------------------------------------------------------------------------------------------------------
const REPORTS = [
  ['inventory-stock', 'الأرصدة الحالية للمخزون', 'Current stock balances'], ['inventory-valuation', 'تقييم المخزون', 'Inventory valuation'], ['low-stock', 'أصناف أوشكت على النفاد', 'Low-stock items'],
  ['out-of-stock', 'أصناف نفدت', 'Out-of-stock items'], ['stock-movements', 'حركة المخزون', 'Stock movement history'], ['inventory-adjustments', 'تسويات وجرد المخزون', 'Stock adjustments and counts'],
  ['fast-moving', 'الأصناف الأسرع حركة', 'Fast-moving parts'], ['slow-moving', 'الأصناف بطيئة الحركة', 'Slow-moving parts'], ['purchases-by-supplier', 'المشتريات حسب المورد', 'Purchases by supplier'],
  ['supplier-invoices', 'سجل فواتير الموردين', 'Supplier invoice register'], ['supplier-balances', 'أرصدة الموردين المستحقة', 'Supplier outstanding balances'],
  ['supplier-payments', 'مدفوعات الموردين (نقدي)', 'Supplier payments (cash basis)'], ['job-parts-consumption', 'استهلاك القطع حسب أمر الإصلاح', 'Parts consumption by repair order'],
  ['parts-profit-by-source', 'ربح القطع حسب المصدر (مخزن، شراء مباشر، عميل)', 'Parts profit by source (warehouse, direct, customer)'],
];
export async function reports(box) {
  const available = new Set((await get('/api/reports')).map((r) => r.name));
  const today = new Date().toISOString().slice(0, 10);
  const from = input({ type: 'date', value: `${today.slice(0, 8)}01` }); const to = input({ type: 'date', value: today });
  const link = (name, fmt) => `/api/reports/${name}/export${qs({ format: fmt, lang, date_from: from.value, date_to: to.value })}`;
  const lang = isAr ? 'ar' : 'en';
  const accrual = new Set(['purchases-by-supplier', 'supplier-invoices', 'parts-profit-by-source', 'job-parts-consumption']);
  box.append(card(t('التقارير', 'Reports'), h('p', { class: 'hint', text: t('تقارير النقدية (مدفوعات الموردين) منفصلة عن تقارير الاستحقاق (الأرباح والمشتريات المرحّلة).', 'Cash-flow reports (supplier payments) are kept apart from accrual reports (profit and posted purchases).') }),
    h('div', { class: 'toolbar' }, field(t('من', 'From'), from), field(t('إلى', 'To'), to)),
    h('ul', { class: 'report-list' }, REPORTS.filter(([n]) => available.has(n)).map(([name, ar, en]) => h('li', {},
      h('span', {}, isAr ? ar : en, ' ', chip(name === 'supplier-payments' ? t('نقدي', 'Cash') : accrual.has(name) ? t('استحقاق', 'Accrual') : t('مخزون', 'Stock'), name === 'supplier-payments' ? 'wait' : 'idle')),
      h('div', { class: 'row-actions' }, h('a', { href: `/reports/${name}`, text: t('عرض', 'View') }), h('a', { href: link(name, 'xlsx'), text: 'Excel' }), h('a', { href: link(name, 'csv'), text: 'CSV' })))))));
}
