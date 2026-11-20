// AutoCare Pro - inventory UI entry point: shell (header, navigation, language switch) and routes.
import { t, h, clear, isAr, lang, setLang, loadSession, can, route, startRouter, parseHash, ApiError, card, emptyState } from './core.js';
import { dashboard, items, balances, valuation, lowStock, reports } from './screens-catalog.js';
import { purchases, purchaseForm, purchaseDetail, receiving, supplierBalances } from './screens-purchasing.js';
import { issue, returns, adjustments, movements, jobParts } from './screens-stock.js';

const NAV = [
  ['/dashboard', t('لوحة المخزن', 'Inventory dashboard'), 'inventory.read'], ['/items', t('كتالوج قطع الغيار', 'Spare parts catalog'), 'inventory.read'], ['/balances', t('أرصدة المخزون', 'Stock balances'), 'inventory.read'],
  ['/purchases', t('فواتير المشتريات', 'Purchase invoices'), 'purchasing.read'], ['/receiving', t('استلام البضاعة', 'Goods receiving'), 'purchasing.read'], ['/issue', t('صرف المخزون', 'Stock issue'), 'parts.write'],
  ['/returns', t('مرتجعات المخزن', 'Stock returns'), 'parts.write'], ['/adjustments', t('التسويات والجرد', 'Adjustments & counts'), 'inventory.adjust'], ['/movements', t('حركة المخزون', 'Movement history'), 'inventory.read'],
  ['/low-stock', t('تنبيهات النقص', 'Low-stock alerts'), 'inventory.read'], ['/valuation', t('تقييم المخزون', 'Inventory valuation'), 'inventory.costs'], ['/suppliers-balance', t('أرصدة الموردين', 'Supplier balances'), 'purchasing.read'],
  ['/reports', t('تقارير المخزن', 'Inventory reports'), 'inventory.read'],
];

route(/^\/dashboard$/, dashboard, { perm: 'inventory.read' });
route(/^\/items$/, items, { perm: 'inventory.read' });
route(/^\/balances$/, balances, { perm: 'inventory.read' });
route(/^\/valuation$/, valuation, { perm: 'inventory.costs' });
route(/^\/low-stock$/, lowStock, { perm: 'inventory.read' });
route(/^\/reports$/, reports, { perm: 'inventory.read' });
route(/^\/purchases$/, purchases, { perm: 'purchasing.read' });
route(/^\/purchases\/(new)$/, purchaseForm, { perm: 'purchasing.write' });
route(/^\/purchases\/([0-9a-f-]{36})\/edit$/, purchaseForm, { perm: 'purchasing.write' });
route(/^\/purchases\/([0-9a-f-]{36})$/, purchaseDetail, { perm: 'purchasing.read' });
route(/^\/receiving$/, receiving, { perm: 'purchasing.read' });
route(/^\/suppliers-balance$/, supplierBalances, { perm: 'purchasing.read' });
route(/^\/issue$/, issue, { perm: 'parts.write' });
route(/^\/returns$/, returns, { perm: 'parts.write' });
route(/^\/adjustments$/, adjustments, { perm: 'inventory.adjust' });
route(/^\/movements$/, movements, { perm: 'inventory.read' });
route(/^\/job\/([0-9a-f-]{36})$/, jobParts, { perm: 'parts.write' });

async function boot() {
  const root = document.getElementById('app');
  document.title = t('المخزن — أوتو كير برو', 'Inventory — AutoCare Pro');
  let user;
  try { user = await loadSession(); } catch (e) {
    clear(root).append(h('main', { class: 'login-needed' }, card(t('المخزن', 'Inventory'), h('p', { text: e instanceof ApiError && e.status === 401 ? t('سجّل الدخول أولًا.', 'Please sign in first.') : e.message }),
      h('a', { class: 'btn primary', href: '/', text: t('تسجيل الدخول', 'Sign in') }))));
    return;
  }
  const content = h('main', { class: 'content', id: 'content' });
  const nav = h('nav', { 'aria-label': t('قائمة المخزن', 'Inventory menu') }, h('ul', {}, NAV.filter(([, , perm]) => can(perm)).map(([path, label]) => h('li', {}, h('a', { href: `#${path}`, 'data-path': path, text: label })))));
  const other = lang === 'ar' ? 'en' : 'ar';
  const shell = h('div', { class: 'shell' },
    h('aside', { class: 'side' }, h('a', { class: 'brand', href: '/', title: t('العودة إلى الشاشة الرئيسية', 'Back to the home screen'), 'aria-label': t('أوتو كير برو — العودة إلى الشاشة الرئيسية', 'AutoCare Pro — back to the home screen') }, h('b', { text: 'AutoCare' }), h('em', { text: ' Pro' }), h('small', { text: t('المخزن والمشتريات', 'Inventory & purchasing') })), nav,
      h('a', { class: 'back', href: '/', text: t('← العودة للتطبيق', '← Back to the app') })),
    h('div', { class: 'main' }, h('header', { class: 'top' }, h('h1', { id: 'page-title', text: t('المخزن', 'Inventory') }), h('div', { class: 'who' }, h('span', { text: user.full_name }),
      h('button', { type: 'button', class: 'btn secondary', lang: other, onclick: () => setLang(other), text: other === 'en' ? 'English' : 'العربية' }))), content));
  clear(root).append(shell);
  if (!can('inventory.read') && !can('purchasing.read') && !can('parts.write')) { content.append(card(null, emptyState(t('ليست لديك صلاحية استخدام المخزن', 'You do not have permission to use inventory')))); return; }
  if (!location.hash) location.hash = can('inventory.read') ? '/dashboard' : '/issue';
  startRouter(content, (path) => {
    const base = '/' + (path.split('/')[1] || 'dashboard');
    for (const a of nav.querySelectorAll('a')) { const on = a.dataset.path === base || (base === '/job' && false); if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); }
    const hit = NAV.find(([p]) => p === base);
    document.getElementById('page-title').textContent = hit ? hit[1] : base === '/job' ? t('مصدر القطعة في أمر الإصلاح', 'Part source on a repair order') : t('المخزن', 'Inventory');
    window.scrollTo(0, 0);
  });
}
boot();
