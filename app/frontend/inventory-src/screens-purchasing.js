// Inventory UI: supplier purchase invoices, goods receiving, supplier payments and invoice attachments.
import { t, h, clear, put, get, post, patch, del, api, qs, can, num, day, when, itemName, chip, statusChip, button, field, input, select, card, table, modal, toast, go, newKey, isAr, itemPicker } from './core.js';

const money = (v) => (v == null || v === '' ? '' : Number(v).toFixed(2));
const sumLines = (lines) => lines.reduce((s, l) => s + Math.max(0, Number(l.qty || 0) * Number(l.unit_cost || 0) - Number(l.discount || 0)), 0);

// ---- list ----------------------------------------------------------------------------------------------------------------------
export async function purchases(box, { query }) {
  const limit = 25;
  const offset = Number(query.offset || 0);
  const sups = await get('/api/suppliers');
  const status = select([['', t('كل الحالات', 'Any status')], ['draft', t('مسودة', 'Draft')], ['posted', t('مرحّلة', 'Posted')], ['cancelled', t('ملغاة', 'Cancelled')]], { value: query.status || '' });
  const sup = select([['', t('كل الموردين', 'All suppliers')], ...sups.map((s) => [s.id, s.name])], { value: query.supplier_id || '' });
  const rec = select([['', t('الاستلام: الكل', 'Receipt: any')], ['none', t('لم تُستلم', 'Not received')], ['partial', t('جزئي', 'Partial')], ['full', t('مكتمل', 'Complete')]], { value: query.receipt_status || '' });
  const pay = select([['', t('السداد: الكل', 'Payment: any')], ['unpaid', t('غير مدفوعة', 'Unpaid')], ['partial', t('جزئي', 'Partial')], ['paid', t('مدفوعة', 'Paid')]], { value: query.payment_status || '' });
  const rows = await get(`/api/inventory/purchase-invoices${qs({ status: query.status, supplier_id: query.supplier_id, receipt_status: query.receipt_status, payment_status: query.payment_status, date_from: query.date_from, date_to: query.date_to, limit, offset })}`);
  const cols = [
    { label: '#', render: (r) => h('a', { href: `#/purchases/${r.id}`, text: `PI-${String(r.number).padStart(5, '0')}` }) },
    { label: t('المورد', 'Supplier'), key: 'supplier' }, { label: t('فاتورة المورد', 'Supplier invoice'), key: 'supplier_invoice_no' }, { label: t('التاريخ', 'Date'), render: (r) => day(r.invoice_date) },
    { label: t('الحالة', 'Status'), render: (r) => statusChip(r.status) }, { label: t('الاستلام', 'Receipt'), render: (r) => (r.status === 'posted' ? statusChip(r.receipt_status) : '') },
    { label: t('السداد', 'Payment'), render: (r) => (r.status === 'posted' ? statusChip(r.payment_status) : '') },
    { label: t('الإجمالي', 'Total'), key: 'total', cls: 'n' }, { label: t('المتبقي للمورد', 'Owed'), render: (r) => (r.status === 'posted' ? r.outstanding : ''), cls: 'n' },
  ];
  const apply = () => go(`/purchases${qs({ status: status.value, supplier_id: sup.value, receipt_status: rec.value, payment_status: pay.value })}`);
  box.append(card(null, h('div', { class: 'toolbar' }, field(t('الحالة', 'Status'), status), field(t('المورد', 'Supplier'), sup), field(t('الاستلام', 'Receipt'), rec), field(t('السداد', 'Payment'), pay),
    button(t('تطبيق', 'Apply'), apply, 'secondary'), can('purchasing.write') ? button(t('+ فاتورة مشتريات', '+ Purchase invoice'), () => go('/purchases/new')) : null),
    table(cols, rows, { empty: t('لا توجد فواتير', 'No invoices') }),
    h('div', { class: 'pager' }, h('span', { text: t(`صفحة ${Math.floor(offset / limit) + 1}`, `Page ${Math.floor(offset / limit) + 1}`) }),
      h('div', {}, button(t('السابق', 'Previous'), () => go(`/purchases${qs({ ...query, offset: Math.max(0, offset - limit) || '' })}`), 'secondary', { disabled: offset === 0 }),
        button(t('التالي', 'Next'), () => go(`/purchases${qs({ ...query, offset: offset + limit })}`), 'secondary', { disabled: rows.length < limit })))));
}

// ---- goods receiving (invoices still waiting for goods) -------------------------------------------------------------------------------
export async function receiving(box) {
  const [none, partial] = await Promise.all([get('/api/inventory/purchase-invoices?status=posted&receipt_status=none&limit=100'), get('/api/inventory/purchase-invoices?status=posted&receipt_status=partial&limit=100')]);
  const rows = [...none, ...partial].sort((a, b) => b.number - a.number);
  const cols = [{ label: '#', render: (r) => `PI-${String(r.number).padStart(5, '0')}` }, { label: t('المورد', 'Supplier'), key: 'supplier' }, { label: t('فاتورة المورد', 'Supplier invoice'), key: 'supplier_invoice_no' },
    { label: t('الاستلام', 'Receipt'), render: (r) => statusChip(r.receipt_status) }, { label: t('أصناف بانتظار الاستلام', 'Lines waiting'), render: (r) => r.lines.filter((l) => Number(l.qty_open) > 0).length, cls: 'n' },
    { label: '', render: (r) => h('a', { href: `#/purchases/${r.id}`, text: t('استلام البضاعة', 'Receive goods') }) }];
  box.append(card(t('استلام البضاعة', 'Goods receiving'), h('p', { class: 'hint', text: t('المخزون لا يزيد إلا عند تسجيل الاستلام الفعلي؛ ترحيل الفاتورة وحده لا يغيّر الرصيد.', 'Stock only increases when goods are actually received; posting the invoice alone does not change the balance.') }),
    table(cols, rows, { empty: t('لا توجد فواتير بانتظار الاستلام', 'No invoices waiting for goods') })));
}

// ---- create / edit draft --------------------------------------------------------------------------------------------------------------
export async function purchaseForm(box, { params }) {
  const id = params[0] && params[0] !== 'new' ? params[0] : null;
  const existing = id ? await get(`/api/inventory/purchase-invoices/${id}`) : null;
  if (existing && existing.status !== 'draft') throw new Error(t('الفاتورة مرحّلة ولا يمكن تعديلها', 'The invoice is posted and cannot be edited'));
  const [sups, whs] = await Promise.all([get('/api/suppliers?active=true'), get('/api/inventory/warehouses')]);
  let prefill = null;
  if (!existing) { try { prefill = JSON.parse(sessionStorage.getItem('inv.draft') || 'null'); sessionStorage.removeItem('inv.draft'); } catch { prefill = null; } }
  const supplier = select(sups.map((s) => [s.id, s.name]), { value: existing?.supplier_id ?? prefill?.supplier_id ?? '' });
  const number = input({ value: existing?.supplier_invoice_no || '', required: true, maxlength: 100 });
  const date = input({ type: 'date', value: day(existing?.invoice_date) || new Date().toISOString().slice(0, 10) });
  const wh = select(whs.map((w) => [w.id, isAr ? w.name_ar : w.name_en]), { value: existing?.warehouse_id ?? '' });
  const discount = input({ type: 'number', step: '0.01', min: '0', value: existing?.discount ?? '0' });
  const tax = input({ type: 'number', step: '0.01', min: '0', max: '100', value: existing?.tax_rate ?? '0' });
  const notes = h('textarea', { rows: 2 }, existing?.notes || '');
  const lines = (existing?.lines || prefill?.lines?.map((l) => ({ item_id: l.item_id, sku: l.sku, name_en: l.name, qty_ordered: l.qty, unit_cost: '', discount: '0' })) || [])
    .map((l) => ({ item: { id: l.item_id, sku: l.sku, name_en: l.name_en, name_ar: l.name_ar }, qty: num(l.qty_ordered), unit_cost: num(l.unit_cost), discount: num(l.discount) }));
  if (!lines.length) lines.push({ item: null, qty: '1', unit_cost: '', discount: '0' });
  const key = newKey();
  const linesBox = h('div'); const totals = h('div', { class: 'totals' });
  const refresh = () => {
    const sub = sumLines(lines); const net = sub - Number(discount.value || 0); const tx = net * Number(tax.value || 0) / 100;
    clear(totals).append(h('div', {}, h('span', { text: t('المجموع', 'Subtotal') }), h('b', { text: money(sub) })), h('div', {}, h('span', { text: t('بعد الخصم', 'After discount') }), h('b', { text: money(net) })),
      h('div', {}, h('span', { text: t('الضريبة', 'Tax') }), h('b', { text: money(tx) })), h('div', { class: 'grand' }, h('span', { text: t('الإجمالي', 'Total') }), h('b', { text: money(net + tx) })));
  };
  const drawLines = () => {
    clear(linesBox);
    linesBox.append(h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {}, [t('الصنف', 'Item'), t('الكمية', 'Qty'), t('تكلفة الوحدة', 'Unit cost'), t('خصم السطر', 'Line discount'), t('الإجمالي', 'Total'), ''].map((x) => h('th', { text: x })))),
      h('tbody', {}, lines.map((l, idx) => {
        const picker = itemPicker({ onPick: (i) => { l.item = i; } }); picker.set(l.item);
        const qty = input({ type: 'number', step: '0.001', min: '0.001', value: l.qty }); const cost = input({ type: 'number', step: '0.0001', min: '0', value: l.unit_cost });
        const dis = input({ type: 'number', step: '0.01', min: '0', value: l.discount });
        const tot = h('td', { class: 'n', text: money(Math.max(0, Number(l.qty || 0) * Number(l.unit_cost || 0) - Number(l.discount || 0))) });
        const upd = () => { l.qty = qty.value; l.unit_cost = cost.value; l.discount = dis.value; tot.textContent = money(Math.max(0, Number(l.qty || 0) * Number(l.unit_cost || 0) - Number(l.discount || 0))); refresh(); };
        [qty, cost, dis].forEach((x) => x.addEventListener('input', upd));
        return h('tr', {}, h('td', {}, picker.el), h('td', {}, qty), h('td', {}, cost), h('td', {}, dis), tot,
          h('td', {}, lines.length > 1 ? button('✕', () => { lines.splice(idx, 1); drawLines(); refresh(); }, 'secondary', { 'aria-label': t('حذف السطر', 'Remove line') }) : null));
      })))));
  };
  [discount, tax].forEach((x) => x.addEventListener('input', refresh));
  drawLines(); refresh();
  const save = async () => {
    if (lines.some((l) => !l.item)) throw new Error(t('اختر الصنف في كل سطر', 'Choose an item on every line'));
    const body = { supplier_invoice_no: number.value.trim(), invoice_date: date.value, warehouse_id: Number(wh.value), discount: discount.value || '0', tax_rate: tax.value || '0', notes: notes.value || null,
      lines: lines.map((l) => ({ item_id: l.item.id, qty: l.qty, unit_cost: l.unit_cost || '0', discount: l.discount || '0' })) };
    const saved = existing ? await patch(`/api/inventory/purchase-invoices/${existing.id}`, body) : await api('/api/inventory/purchase-invoices', { method: 'POST', body: { supplier_id: Number(supplier.value), ...body }, key });
    toast(t('تم حفظ المسودة', 'Draft saved'));
    go(`/purchases/${saved.id}`);
  };
  box.append(card(existing ? t('تعديل مسودة فاتورة مشتريات', 'Edit draft purchase invoice') : t('فاتورة مشتريات جديدة', 'New purchase invoice'),
    h('div', { class: 'grid3' }, field(t('المورد', 'Supplier'), supplier), field(t('رقم فاتورة المورد', 'Supplier invoice number'), number), field(t('تاريخ الفاتورة', 'Invoice date'), date),
      field(t('المخزن', 'Warehouse'), wh), field(t('خصم على الفاتورة', 'Invoice discount'), discount), field(t('نسبة الضريبة %', 'Tax rate %'), tax)),
    linesBox, button(t('+ سطر', '+ Line'), () => { lines.push({ item: null, qty: '1', unit_cost: '', discount: '0' }); drawLines(); }, 'secondary'),
    totals, field(t('ملاحظات', 'Notes'), notes),
    h('div', { class: 'actions' }, button(t('حفظ كمسودة', 'Save draft'), save), button(t('إلغاء', 'Cancel'), () => go(existing ? `/purchases/${existing.id}` : '/purchases'), 'secondary'))));
  if (existing) supplier.disabled = true; // the supplier of a draft is fixed; create a new draft to change it
}

// ---- detail ----------------------------------------------------------------------------------------------------------------------
async function reasonModal(title, label, action) {
  modal(title, (close) => {
    const reason = h('textarea', { rows: 3, required: true });
    return h('div', { class: 'modal-body' }, field(label, reason), h('div', { class: 'actions' }, button(t('تأكيد', 'Confirm'), async () => {
      if (reason.value.trim().length < 3) throw new Error(t('اكتب السبب (3 أحرف على الأقل)', 'Enter a reason (at least 3 characters)'));
      await action(reason.value.trim()); close();
    }), button(t('إلغاء', 'Cancel'), close, 'secondary')));
  });
}

export async function purchaseDetail(box, { params }) {
  const id = params[0];
  const inv = await get(`/api/inventory/purchase-invoices/${id}`);
  const reload = () => { go(`/purchases/${id}?r=${Date.now()}`); };
  const posted = inv.status === 'posted';
  const actions = [];
  if (inv.status === 'draft' && can('purchasing.write')) {
    actions.push(button(t('تعديل', 'Edit'), () => go(`/purchases/${id}/edit`), 'secondary'));
    actions.push(button(t('ترحيل الفاتورة', 'Post invoice'), async () => { await post(`/api/inventory/purchase-invoices/${id}/post`, {}); toast(t('تم ترحيل الفاتورة (لم يتغير المخزون بعد)', 'Invoice posted (stock has not changed yet)')); reload(); }));
    actions.push(button(t('حذف المسودة', 'Delete draft'), async () => { if (!confirm(t('حذف المسودة؟', 'Delete this draft?'))) return; await del(`/api/inventory/purchase-invoices/${id}`); go('/purchases'); }, 'danger'));
  }
  if (posted && can('purchasing.write')) {
    if (inv.receipt_status !== 'full') actions.push(button(t('استلام بضاعة', 'Receive goods'), () => receiveModal(inv, reload)));
    if (Number(inv.outstanding) > 0) actions.push(button(t('دفعة للمورد', 'Pay supplier'), () => payModal(inv, reload), 'secondary'));
    actions.push(button(t('إلغاء الفاتورة', 'Cancel invoice'), () => reasonModal(t('إلغاء فاتورة المشتريات', 'Cancel purchase invoice'), t('سبب الإلغاء', 'Reason'), async (reason) => {
      await post(`/api/inventory/purchase-invoices/${id}/cancel`, { reason }); toast(t('تم الإلغاء', 'Cancelled')); reload();
    }), 'danger'));
  }
  const lineCols = [{ label: t('الصنف', 'Item'), render: (l) => h('span', {}, h('b', { text: l.sku }), ' ', itemName(l)) }, { label: t('المطلوب', 'Ordered'), key: 'qty_ordered', num: true, cls: 'n' },
    { label: t('المستلم', 'Received'), key: 'qty_received', num: true, cls: 'n' }, { label: t('المتبقي', 'Open'), key: 'qty_open', num: true, cls: 'n' },
    { label: t('تكلفة الوحدة', 'Unit cost'), key: 'unit_cost', num: true, cls: 'n' }, { label: t('الخصم', 'Discount'), key: 'discount', cls: 'n' }, { label: t('الإجمالي', 'Total'), key: 'line_total', cls: 'n' }];
  const receiptCols = [{ label: '#', render: (r) => `GRN-${String(r.number).padStart(5, '0')}` }, { label: t('التاريخ', 'Date'), render: (r) => when(r.received_at) }, { label: t('الحالة', 'Status'), render: (r) => chip(r.status === 'posted' ? t('مرحّل', 'Posted') : t('معكوس', 'Reversed'), r.status === 'posted' ? 'ok' : 'idle') },
    { label: t('ملاحظات', 'Notes'), key: 'notes' }, { label: '', render: (r) => (r.status === 'posted' && can('purchasing.write') ? button(t('عكس الاستلام', 'Reverse'), () => reasonModal(t('عكس إذن الاستلام', 'Reverse goods receipt'), t('السبب', 'Reason'), async (reason) => {
      await post(`/api/inventory/receipts/${r.id}/reverse`, { reason }); toast(t('تم عكس الاستلام', 'Receipt reversed')); reload();
    }), 'secondary') : '') }];
  const payCols = [{ label: t('التاريخ', 'Date'), render: (p) => when(p.paid_at) }, { label: t('الطريقة', 'Method'), key: 'method' }, { label: t('المرجع', 'Reference'), key: 'reference' }, { label: t('المبلغ', 'Amount'), key: 'amount', cls: 'n' }];
  const attBox = h('div');
  put(box,
    card(`PI-${String(inv.number).padStart(5, '0')} — ${inv.supplier}`,
      h('div', { class: 'summary' }, h('div', {}, h('span', { text: t('فاتورة المورد', 'Supplier invoice') }), h('b', { text: inv.supplier_invoice_no })), h('div', {}, h('span', { text: t('التاريخ', 'Date') }), h('b', { text: day(inv.invoice_date) })),
        h('div', {}, h('span', { text: t('الحالة', 'Status') }), statusChip(inv.status)), posted ? h('div', {}, h('span', { text: t('الاستلام', 'Receipt') }), statusChip(inv.receipt_status)) : null,
        posted ? h('div', {}, h('span', { text: t('السداد', 'Payment') }), statusChip(inv.payment_status)) : null),
      table(lineCols, inv.lines),
      h('div', { class: 'totals' }, h('div', {}, h('span', { text: t('المجموع', 'Subtotal') }), h('b', { text: inv.subtotal })), h('div', {}, h('span', { text: t('الخصم', 'Discount') }), h('b', { text: inv.discount })),
        h('div', {}, h('span', { text: `${t('الضريبة', 'Tax')} ${num(inv.tax_rate)}%` }), h('b', { text: inv.tax_amount })), h('div', { class: 'grand' }, h('span', { text: t('الإجمالي', 'Total') }), h('b', { text: inv.total })),
        posted ? h('div', {}, h('span', { text: t('المدفوع', 'Paid') }), h('b', { text: inv.paid })) : null, posted && Number(inv.credits) > 0 ? h('div', {}, h('span', { text: t('إشعارات المورد', 'Supplier credits') }), h('b', { text: inv.credits })) : null,
        posted ? h('div', { class: 'grand' }, h('span', { text: t('المتبقي للمورد', 'Owed to supplier') }), h('b', { text: inv.outstanding })) : null),
      inv.cancel_reason ? h('p', { class: 'error', text: `${t('سبب الإلغاء', 'Cancel reason')}: ${inv.cancel_reason}` }) : null, inv.notes ? h('p', { class: 'muted', text: inv.notes }) : null,
      h('div', { class: 'actions' }, ...actions, button(t('رجوع', 'Back'), () => go('/purchases'), 'secondary'))),
    inv.receipts.length ? card(t('أذونات الاستلام', 'Goods receipts'), table(receiptCols, inv.receipts)) : null,
    inv.payments.length ? card(t('مدفوعات المورد', 'Supplier payments'), table(payCols, inv.payments)) : null,
    card(t('مرفقات الفاتورة', 'Invoice attachments'), attBox));
  await attachments(attBox, id);
}

async function attachments(boxEl, id) {
  const render = async () => {
    const list = await get(`/api/attachments${qs({ owner_type: 'purchase_invoice', owner_id: id })}`);
    clear(boxEl);
    const file = input({ type: 'file', accept: 'image/jpeg,image/png,image/webp,image/gif,application/pdf' });
    boxEl.append(list.length ? h('ul', { class: 'plain' }, list.map((a) => h('li', {}, h('a', { href: a.url, target: '_blank', rel: 'noopener', text: a.name }), h('small', { class: 'muted', text: `  ${Math.round(a.size_bytes / 1024)} KB` })))) : h('p', { class: 'empty', text: t('لا توجد مرفقات', 'No attachments') }),
      can('purchasing.write') ? h('div', { class: 'toolbar' }, field(t('إرفاق صورة أو PDF', 'Attach an image or PDF'), file), button(t('رفع', 'Upload'), async () => {
        if (!file.files[0]) throw new Error(t('اختر ملفًا', 'Choose a file'));
        const form = new FormData(); form.append('owner_type', 'purchase_invoice'); form.append('owner_id', id); form.append('kind', 'document'); form.append('file', file.files[0]);
        await api('/api/attachments', { method: 'POST', form }); toast(t('تم الرفع', 'Uploaded')); await render();
      }, 'secondary')) : null);
  };
  try { await render(); } catch (e) { clear(boxEl).append(h('p', { class: 'muted', text: e.message })); }
}

function receiveModal(inv, done) {
  const open = inv.lines.filter((l) => Number(l.qty_open) > 0);
  modal(t('استلام بضاعة', 'Receive goods'), (close) => {
    const inputs = open.map((l) => input({ type: 'number', step: '0.001', min: '0', max: l.qty_open, value: num(l.qty_open) }));
    const notes = input({ placeholder: t('ملاحظات (اختياري)', 'Notes (optional)') });
    const key = newKey();
    return h('div', { class: 'modal-body' }, h('p', { class: 'hint', text: t('أدخل الكمية التي وصلت فعلًا (استلام جزئي مسموح). اترك صفرًا للأصناف التي لم تصل.', 'Enter what actually arrived (partial receipts are fine). Leave 0 for lines that did not arrive.') }),
      h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {}, [t('الصنف', 'Item'), t('المتبقي', 'Open'), t('المستلم الآن', 'Receive now')].map((x) => h('th', { text: x })))),
        h('tbody', {}, open.map((l, i) => h('tr', {}, h('td', {}, h('b', { text: l.sku }), ' ', itemName(l)), h('td', { class: 'n', text: num(l.qty_open) }), h('td', {}, inputs[i])))))),
      field(t('ملاحظات', 'Notes'), notes),
      h('div', { class: 'actions' }, button(t('تسجيل الاستلام', 'Post receipt'), async () => {
        const lines = open.map((l, i) => ({ invoice_line_id: l.id, qty: inputs[i].value })).filter((l) => Number(l.qty) > 0);
        if (!lines.length) throw new Error(t('أدخل كمية لصنف واحد على الأقل', 'Enter a quantity for at least one line'));
        await api(`/api/inventory/purchase-invoices/${inv.id}/receipts`, { method: 'POST', body: { lines, notes: notes.value || null }, key });
        toast(t('تم الاستلام وزاد المخزون', 'Goods received; stock increased')); close(); done();
      }), button(t('إلغاء', 'Cancel'), close, 'secondary')));
  });
}

async function payModal(inv, done) {
  const settings = await get('/api/settings');
  const methods = (settings.finance?.payment_methods || [{ key: 'cash', label: 'cash' }]).map((m) => [m.key, m.label]);
  modal(t('دفعة للمورد', 'Pay supplier'), (close) => {
    const amount = input({ type: 'number', step: '0.01', min: '0.01', max: inv.outstanding, value: inv.outstanding });
    const method = select(methods); const ref = input(); const note = input();
    const key = newKey();
    return h('div', { class: 'modal-body' }, h('p', { class: 'hint', text: t('سداد المورد لا يغيّر المخزون ولا يُعدّ مصروف تشغيل.', 'Paying the supplier does not change stock and is not an operating expense.') }),
      h('div', { class: 'grid3' }, field(t('المبلغ', 'Amount'), amount), field(t('الطريقة', 'Method'), method), field(t('المرجع', 'Reference'), ref)), field(t('ملاحظة', 'Note'), note),
      h('div', { class: 'actions' }, button(t('تسجيل الدفعة', 'Record payment'), async () => {
        await api(`/api/inventory/purchase-invoices/${inv.id}/payments`, { method: 'POST', body: { amount: amount.value, method: method.value, reference: ref.value || null, note: note.value || null }, key });
        toast(t('تم تسجيل الدفعة', 'Payment recorded')); close(); done();
      }), button(t('إلغاء', 'Cancel'), close, 'secondary')));
  });
}

// ---- supplier balances ----------------------------------------------------------------------------------------------------------------
export async function supplierBalances(box) {
  const rows = await get('/api/inventory/supplier-balances');
  box.append(card(t('أرصدة الموردين المستحقة', 'Supplier outstanding balances'), table([{ label: t('المورد', 'Supplier'), key: 'supplier' }, { label: t('الفواتير المرحّلة', 'Posted invoices'), key: 'invoiced', cls: 'n' },
    { label: t('المدفوع', 'Paid'), key: 'paid', cls: 'n' }, { label: t('إشعارات دائنة', 'Credits'), key: 'credits', cls: 'n' }, { label: t('المتبقي للمورد', 'Owed'), key: 'outstanding', cls: 'n' }], rows, { empty: t('لا توجد أرصدة', 'No balances') })));
}
