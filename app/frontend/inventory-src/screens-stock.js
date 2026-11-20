// Inventory UI: stock issue to repair orders, stock returns, adjustments / counts / transfers / supplier returns, movement history,
// and the repair-order page where a part's SOURCE is chosen (warehouse / customer supplied / direct purchase).
import { t, h, clear, get, post, api, qs, can, num, when, itemName, chip, statusChip, typeText, TYPE_TEXT, button, field, input, select, card, table, pager, modal, toast, go, newKey, isAr, itemPicker } from './core.js';

const jobLink = (r) => h('a', { href: `/jobs/${r.visit_id}`, text: `#${r.job_no}` });
const sourceChip = (s) => (s === 'warehouse' ? chip(t('من المخزن', 'Warehouse'), 'work') : s === 'customer' ? chip(t('من العميل', 'Customer supplied'), 'wait') : chip(t('شراء مباشر', 'Direct purchase')));

// ---- stock issue -------------------------------------------------------------------------------------------------------------------
export async function issue(box) {
  const rows = (await get('/api/parts?limit=200')).filter((p) => p.source === 'warehouse' && ['requested', 'ordered', 'purchased'].includes(p.status));
  const act = (status, label, kind = 'primary') => (r) => button(label, async () => {
    await post(`/api/parts/${r.id}/status`, { status });
    toast(status === 'received' ? t('تم الصرف وخُصم من المخزون', 'Issued; stock deducted') : t('تم حجز الكمية', 'Quantity reserved')); go(`/issue?r=${Date.now()}`);
  }, kind);
  const cols = [{ label: t('أمر الإصلاح', 'Repair order'), render: jobLink }, { label: t('اللوحة', 'Plate'), key: 'plate' }, { label: t('القطعة', 'Part'), key: 'part_name' }, { label: t('الكود', 'SKU'), key: 'part_number' },
    { label: t('الكمية', 'Qty'), key: 'quantity', num: true, cls: 'n' }, { label: t('المحجوز', 'Reserved'), render: (r) => (r.reserved_qty ? num(r.reserved_qty) : '—'), cls: 'n' }, { label: t('الحالة', 'Status'), render: (r) => statusChip(r.status) },
    { label: '', render: (r) => h('div', { class: 'row-actions' }, r.status === 'requested' ? act('ordered', t('حجز', 'Reserve'), 'secondary')(r) : null, act('received', t('صرف', 'Issue'))(r)) }];
  box.append(card(t('صرف قطع من المخزن لأوامر الإصلاح', 'Issue stock to repair orders'),
    h('p', { class: 'hint', text: t('الحجز والصرف يتطلبان موافقة العميل إذا أُرسل عرض سعر. لا يُخصم المخزون إلا عند «صرف».', 'Reserving and issuing need the customer\'s approval when a quotation was sent. Stock is only deducted on «Issue».') }),
    table(cols, rows, { empty: t('لا توجد قطع مخزن بانتظار الحجز أو الصرف', 'No warehouse parts waiting to be reserved or issued') })));
}

// ---- stock returns -----------------------------------------------------------------------------------------------------------------
export async function returns(box) {
  const rows = (await get('/api/parts?limit=200')).filter((p) => p.source === 'warehouse' && Number(p.issued_qty) > 0 && Number(p.effective_quantity) > 0 && !['returned', 'cancelled'].includes(p.status));
  const cols = [{ label: t('أمر الإصلاح', 'Repair order'), render: jobLink }, { label: t('القطعة', 'Part'), key: 'part_name' }, { label: t('الكود', 'SKU'), key: 'part_number' },
    { label: t('المصروف', 'Issued'), key: 'issued_qty', num: true, cls: 'n' }, { label: t('المرتجع', 'Returned'), key: 'returned_quantity', num: true, cls: 'n' }, { label: t('الفعلي', 'On job'), key: 'effective_quantity', num: true, cls: 'n' },
    { label: t('الحالة', 'Status'), render: (r) => statusChip(r.status) }, { label: '', render: (r) => button(t('إرجاع', 'Return'), () => returnModal(r)) }];
  box.append(card(t('مرتجعات المخزن', 'Stock returns'), h('p', { class: 'hint', text: t('القطعة غير المستخدمة تعود للرف بتكلفتها؛ التالفة والمستعملة لا تعود للمخزون القابل للبيع وتبقى تكلفتها على الأمر.', 'An unused part goes back on the shelf at its cost; defective and used parts never return to sellable stock and keep their cost on the job.') }),
    table(cols, rows, { empty: t('لا توجد قطع مصروفة قابلة للإرجاع', 'No issued parts can be returned') })));
}

function returnModal(part) {
  modal(t('إرجاع قطعة للمخزن', 'Return part to warehouse'), (close) => {
    const qty = input({ type: 'number', step: '0.01', min: '0.01', max: part.effective_quantity, value: part.effective_quantity });
    const disp = select([['unused', t('غير مستخدمة — تعود للمخزون', 'Unused — back to stock')], ['defective', t('تالفة — لا تعود للمخزون', 'Defective — not restocked')], ['used', t('مستعملة — لا تعود للمخزون', 'Used — not restocked')]]);
    const reason = h('textarea', { rows: 2, required: true });
    return h('div', { class: 'modal-body' }, h('p', { class: 'muted', text: `${part.part_name} — #${part.job_no}` }),
      h('div', { class: 'grid2' }, field(t('الكمية', 'Quantity'), qty), field(t('حالة القطعة', 'Condition'), disp)), field(t('السبب', 'Reason'), reason),
      h('div', { class: 'actions' }, button(t('تأكيد الإرجاع', 'Confirm return'), async () => {
        if (reason.value.trim().length < 2) throw new Error(t('اكتب السبب', 'Enter a reason'));
        await post(`/api/parts/${part.id}/return-to-warehouse`, { quantity: qty.value, disposition: disp.value, reason: reason.value.trim() });
        toast(t('تم الإرجاع', 'Return recorded')); close(); go(`/returns?r=${Date.now()}`);
      }), button(t('إلغاء', 'Cancel'), close, 'secondary')));
  });
}

// ---- adjustments / counts / transfers / supplier returns ----------------------------------------------------------------------------
function lineEditor(valueLabel, { step = '0.001', min, showSystem = false } = {}) {
  const lines = [{ picker: null, input: null }];
  const host = h('div', { class: 'lines' });
  const draw = () => {
    clear(host);
    lines.forEach((l, i) => {
      const system = h('small', { class: 'muted' });
      l.picker = itemPicker({ onPick: (it) => { system.textContent = showSystem ? t(`رصيد النظام: ${num(it.on_hand)}`, `System: ${num(it.on_hand)}`) : ''; } });
      l.input = input({ type: 'number', step, min, placeholder: valueLabel });
      host.append(h('div', { class: 'line' }, l.picker.el, l.input, system, lines.length > 1 ? button('✕', () => { lines.splice(i, 1); draw(); }, 'secondary') : null));
    });
  };
  draw();
  return { el: h('div', {}, host, button(t('+ صنف', '+ Item'), () => { lines.push({}); draw(); }, 'secondary')),
    values() { return lines.map((l) => { const it = l.picker.value(); if (!it) throw new Error(t('اختر الصنف في كل سطر', 'Choose an item on every line')); return [it, l.input.value]; }); } };
}

export async function adjustments(box, { query }) {
  const whs = await get('/api/inventory/warehouses');
  const sups = await get('/api/suppliers?active=true');
  const tab = query.tab || 'adjustment';
  const wopts = whs.map((w) => [w.id, isAr ? w.name_ar : w.name_en]);
  const tabs = [['adjustment', t('تسوية', 'Adjustment')], ['count', t('جرد فعلي', 'Physical count')], ['transfer', t('تحويل بين المخازن', 'Warehouse transfer')], ['supplier', t('مرتجع للمورد', 'Supplier return')]];
  const key = newKey();
  let form;
  const done = (msg) => { toast(msg); go(`/adjustments?tab=${tab}&r=${Date.now()}`); };
  if (tab === 'adjustment') {
    const wh = select(wopts); const reason = input({ placeholder: t('السبب (مثال: تلف أثناء التخزين)', 'Reason (e.g. damaged in storage)') }); const ed = lineEditor(t('الفرق (+ زيادة / − نقص)', 'Change (+ / −)'), { step: '0.001' });
    form = [h('div', { class: 'grid2' }, field(t('المخزن', 'Warehouse'), wh), field(t('السبب', 'Reason'), reason)), ed.el,
      button(t('ترحيل التسوية', 'Post adjustment'), async () => {
        await post('/api/inventory/adjustments', { warehouse_id: Number(wh.value), reason: reason.value.trim(), lines: ed.values().map(([it, v]) => ({ item_id: it.id, qty_delta: v })) }, key); done(t('تم ترحيل التسوية', 'Adjustment posted'));
      })];
  } else if (tab === 'count') {
    const wh = select(wopts); const reason = input({ value: t('جرد فعلي', 'Physical count') }); const ed = lineEditor(t('الكمية المعدودة', 'Counted quantity'), { step: '0.001', min: '0', showSystem: true });
    form = [h('div', { class: 'grid2' }, field(t('المخزن', 'Warehouse'), wh), field(t('السبب', 'Reason'), reason)), ed.el,
      button(t('ترحيل الجرد', 'Post count'), async () => {
        const res = await post('/api/inventory/counts', { warehouse_id: Number(wh.value), reason: reason.value.trim(), lines: ed.values().map(([it, v]) => ({ item_id: it.id, counted_qty: v })) }, key);
        done(t(`تم الجرد: ${res.lines.filter((l) => Number(l.qty_delta) !== 0).length} فرق`, `Count posted: ${res.lines.filter((l) => Number(l.qty_delta) !== 0).length} difference(s)`));
      })];
  } else if (tab === 'transfer') {
    const from = select(wopts); const to = select(wopts, { value: whs[1]?.id ?? '' }); const reason = input({ value: t('تحويل بين المخازن', 'Warehouse transfer') }); const ed = lineEditor(t('الكمية', 'Quantity'), { step: '0.001', min: '0.001' });
    form = [whs.length < 2 ? h('p', { class: 'hint', text: t('يوجد مخزن واحد حاليًا؛ أضف مخزنًا آخر من الإعدادات لاستخدام التحويل.', 'There is only one warehouse; add another to use transfers.') }) : null,
      h('div', { class: 'grid3' }, field(t('من مخزن', 'From'), from), field(t('إلى مخزن', 'To'), to), field(t('السبب', 'Reason'), reason)), ed.el,
      button(t('ترحيل التحويل', 'Post transfer'), async () => {
        await post('/api/inventory/transfers', { from_warehouse_id: Number(from.value), to_warehouse_id: Number(to.value), reason: reason.value.trim(), lines: ed.values().map(([it, v]) => ({ item_id: it.id, qty: v })) }, key); done(t('تم التحويل', 'Transfer posted'));
      })];
  } else {
    const wh = select(wopts); const supplier = select(sups.map((s) => [s.id, s.name])); const credit = input({ type: 'number', step: '0.01', min: '0', value: '0' }); const reason = input({ placeholder: t('السبب (مثال: موديل خاطئ)', 'Reason (e.g. wrong model)') });
    const picker = itemPicker(); const qty = input({ type: 'number', step: '0.001', min: '0.001', value: '1' });
    form = [h('div', { class: 'grid3' }, field(t('الصنف', 'Item'), picker.el), field(t('الكمية', 'Quantity'), qty), field(t('المخزن', 'Warehouse'), wh)),
      h('div', { class: 'grid3' }, field(t('المورد', 'Supplier'), supplier), field(t('مبلغ إشعار المورد', 'Supplier credit amount'), credit, t('يخفّض المستحق للمورد', 'Reduces what we owe the supplier')), field(t('السبب', 'Reason'), reason)),
      button(t('ترحيل المرتجع', 'Post return'), async () => {
        const it = picker.value(); if (!it) throw new Error(t('اختر الصنف', 'Choose an item'));
        await post('/api/inventory/supplier-returns', { item_id: it.id, warehouse_id: Number(wh.value), qty: qty.value, supplier_id: Number(supplier.value), credit_amount: credit.value || '0', reason: reason.value.trim() }, key); done(t('تم تسجيل المرتجع', 'Return posted'));
      })];
  }
  box.append(card(t('التسويات والجرد والتحويلات', 'Adjustments, counts and transfers'),
    h('div', { class: 'tabs', role: 'tablist' }, tabs.map(([k, label]) => h('a', { class: k === tab ? 'tab on' : 'tab', role: 'tab', href: `#/adjustments?tab=${k}`, text: label }))), ...form));
}

// ---- movement history --------------------------------------------------------------------------------------------------------------------
export async function movements(box, { query }) {
  const limit = 50; const offset = Number(query.offset || 0);
  const data = await get(`/api/inventory/movements${qs({ item_id: query.item_id, type: query.type, date_from: query.date_from, date_to: query.date_to, part_id: query.part_id, visit_id: query.visit_id, limit, offset })}`);
  const type = select([['', t('كل الأنواع', 'All types')], ...Object.keys(TYPE_TEXT).map((k) => [k, typeText(k)])], { value: query.type || '' });
  const from = input({ type: 'date', value: query.date_from || '' }); const to = input({ type: 'date', value: query.date_to || '' });
  const picker = itemPicker({ placeholder: t('تصفية بصنف', 'Filter by item') });
  if (query.item_id) { try { picker.set(await get(`/api/inventory/items/${query.item_id}`)); } catch { /* unknown id */ } }
  const costs = data.items.length && data.items[0].unit_cost !== undefined;
  const cols = [{ label: t('التاريخ', 'Date'), render: (r) => when(r.ts) }, { label: t('النوع', 'Type'), render: (r) => chip(typeText(r.type), r.qty > 0 ? 'ok' : r.qty < 0 ? 'wait' : 'idle') },
    { label: t('الكود', 'SKU'), key: 'sku' }, { label: t('الصنف', 'Item'), key: 'item_name' }, { label: t('الكمية', 'Qty'), key: 'qty', num: true, cls: 'n' }, { label: t('تغيّر المحجوز', 'Reserved Δ'), key: 'reserved_delta', num: true, cls: 'n' },
    { label: t('الرصيد بعد', 'Balance after'), key: 'on_hand_after', num: true, cls: 'n' }, { label: t('المستند', 'Document'), render: (r) => `${r.doc_type || ''} ${r.doc_id ? String(r.doc_id).slice(0, 8) : ''}` },
    { label: t('السبب', 'Reason'), key: 'reason' }, ...(costs ? [{ label: t('تكلفة الوحدة', 'Unit cost'), key: 'unit_cost', cls: 'n' }, { label: t('القيمة', 'Value'), key: 'value_delta', cls: 'n' }] : []),
    { label: '', render: (r) => (can('inventory.adjust') && ['OPENING', 'ADJUSTMENT', 'COUNT'].includes(r.type) && !r.reverses_id ? button(t('عكس', 'Reverse'), () => reverseModal(r), 'secondary') : '') }];
  const apply = () => go(`/movements${qs({ item_id: picker.value()?.id || '', type: type.value, date_from: from.value, date_to: to.value })}`);
  box.append(card(null, h('div', { class: 'toolbar' }, field(t('الصنف', 'Item'), picker.el), field(t('النوع', 'Type'), type), field(t('من', 'From'), from), field(t('إلى', 'To'), to), button(t('تطبيق', 'Apply'), apply, 'secondary')),
    table(cols, data.items, { empty: t('لا توجد حركات', 'No movements') }), pager(data.total, offset, limit, (o) => go(`/movements${qs({ ...query, offset: o || '' })}`))));
}

function reverseModal(m) {
  modal(t('عكس حركة مخزون', 'Reverse stock movement'), (close) => {
    const reason = h('textarea', { rows: 3, required: true });
    return h('div', { class: 'modal-body' }, h('p', { class: 'hint', text: t('الحركة الأصلية لا تُعدَّل؛ تُسجَّل حركة عكسية جديدة.', 'The original movement is never edited; an opposite movement is posted.') }), field(t('السبب', 'Reason'), reason),
      h('div', { class: 'actions' }, button(t('تأكيد', 'Confirm'), async () => {
        if (reason.value.trim().length < 3) throw new Error(t('اكتب السبب', 'Enter a reason'));
        await post(`/api/inventory/movements/${m.id}/reverse`, { reason: reason.value.trim() }); toast(t('تم العكس', 'Reversed')); close(); go(`/movements?r=${Date.now()}`);
      }), button(t('إلغاء', 'Cancel'), close, 'secondary')));
  });
}

// ---- repair order: choose where the part comes from ------------------------------------------------------------------------------------------
export async function jobParts(box, { params, query }) {
  const id = params[0];
  const job = await get(`/api/jobs/${id}`);
  const parts = await get(`/api/jobs/${id}/parts`);
  const tab = query.tab || 'warehouse';
  const tabs = [['warehouse', t('من المخزن', 'From warehouse')], ['customer', t('قطعة من العميل', 'Customer supplied')], ['direct', t('شراء مباشر لأمر الإصلاح', 'Direct purchase for this order')]];
  const reload = () => go(`/job/${id}?tab=${tab}&r=${Date.now()}`);
  const head = card(`${t('أمر الإصلاح', 'Repair order')} #${job.visit_no}`, h('p', { class: 'muted', text: `${job.vehicle.make} ${job.vehicle.model} — ${job.vehicle.plate || ''} — ${job.customer.name}` }),
    h('div', { class: 'actions' }, h('a', { class: 'btn secondary', href: `/jobs/${id}`, text: t('العودة لأمر الإصلاح', 'Back to the repair order') })));
  const listCols = [{ label: t('القطعة', 'Part'), key: 'part_name' }, { label: t('المصدر', 'Source'), render: (p) => sourceChip(p.source) }, { label: t('الكمية', 'Qty'), key: 'quantity', num: true, cls: 'n' },
    { label: t('السعر', 'Price'), key: 'total_price', cls: 'n' }, { label: t('الحالة', 'Status'), render: (p) => statusChip(p.status) }];
  let body;
  if (tab === 'warehouse') {
    const whs = await get('/api/inventory/warehouses');
    const q = input({ type: 'search', placeholder: t('كود أو اسم أو باركود', 'SKU, name or barcode') }); const wh = select(whs.map((w) => [w.id, isAr ? w.name_ar : w.name_en]));
    const results = h('div');
    const search = async () => {
      const rows = await get(`/api/inventory/available${qs({ q: q.value.trim(), warehouse_id: wh.value, limit: 15 })}`);
      clear(results).append(table([{ label: t('الصنف', 'Part'), render: (r) => itemName(r) }, { label: t('الكود', 'SKU'), key: 'sku' }, { label: t('الماركة', 'Brand'), key: 'brand' },
        { label: t('المخزن', 'Warehouse'), render: (r) => (isAr ? r.warehouse.ar : r.warehouse.en) }, { label: t('المتاح', 'Available'), key: 'available', num: true, cls: 'n' }, { label: t('سعر البيع', 'Selling price'), key: 'selling_price', cls: 'n' },
        { label: '', render: (r) => { const qty = input({ type: 'number', step: '0.01', min: '0.01', value: '1', class: 'qty' }); return h('div', { class: 'row-actions' }, qty, button(t('إضافة', 'Add'), async () => {
          await post(`/api/jobs/${id}/parts/warehouse`, { item_id: r.item_id, quantity: qty.value, warehouse_id: r.warehouse_id }); toast(t('تمت إضافة القطعة من المخزن (لم يُخصم شيء بعد)', 'Warehouse part added (nothing deducted yet)')); reload();
        }, 'primary', { disabled: Number(r.available) <= 0 })); } }], rows, { empty: t('لا توجد نتائج', 'No results') }));
    };
    q.addEventListener('keydown', (e) => { if (e.key === 'Enter') search(); });
    body = card(t('إضافة قطعة من المخزن', 'Add a part from the warehouse'), h('p', { class: 'hint', text: t('يُتحقق من التوفر الآن. الحجز يتم عند موافقة العميل، والخصم من المخزون عند الصرف الفعلي.', 'Availability is checked now. Stock is reserved on the customer\'s approval and deducted when the part is actually issued.') }),
      h('div', { class: 'toolbar' }, field(t('بحث', 'Search'), q), field(t('المخزن', 'Warehouse'), wh), button(t('بحث', 'Search'), search, 'secondary')), results);
    await search();
  } else if (tab === 'customer') {
    const desc = input({ required: true, maxlength: 160, placeholder: t('مثال: تيل فرامل أمامي', 'e.g. Front brake pads') }); const qty = input({ type: 'number', step: '0.01', min: '0.01', value: '1' }); const notes = input();
    body = card(t('قطعة من العميل', 'Customer-supplied part'), h('p', { class: 'hint', text: t('لا خصم من المخزن ولا تكلفة ولا إيراد قطع. أجرة التركيب تُحاسَب كالمعتاد.', 'No warehouse deduction, no cost and no parts revenue. Installation labor is charged as usual.') }),
      h('div', { class: 'grid3' }, field(t('وصف القطعة', 'Part description'), desc), field(t('الكمية', 'Quantity'), qty), field(t('ملاحظات', 'Notes'), notes)),
      h('div', { class: 'actions' }, button(t('إضافة قطعة العميل', 'Add customer part'), async () => { await post(`/api/jobs/${id}/parts/customer-supplied`, { description: desc.value.trim(), quantity: qty.value, notes: notes.value || null }); toast(t('تمت الإضافة', 'Added')); reload(); })));
  } else {
    body = card(t('شراء مباشر لأمر الإصلاح', 'Direct purchase for this order'), h('p', { class: 'hint', text: t('القطعة تُشترى خصيصًا لهذا الأمر وتُحمَّل تكلفتها عليه، ولا تدخل المخزن العام. استخدم شاشة القطع في أمر الإصلاح.', 'The part is bought specifically for this order and its cost is charged to it; it does not enter the general warehouse. Use the parts section of the repair order.') }),
      h('div', { class: 'actions' }, h('a', { class: 'btn primary', href: `/jobs/${id}`, text: t('فتح أمر الإصلاح', 'Open the repair order') })));
  }
  box.append(head, h('div', { class: 'tabs', role: 'tablist' }, tabs.map(([k, label]) => h('a', { class: k === tab ? 'tab on' : 'tab', role: 'tab', href: `#/job/${id}?tab=${k}`, text: label }))), body,
    card(t('قطع هذا الأمر', 'Parts on this order'), table(listCols, parts, { empty: t('لا توجد قطع', 'No parts yet') })));
}
