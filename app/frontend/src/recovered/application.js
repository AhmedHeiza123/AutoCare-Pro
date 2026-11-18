// Recovered compiled JavaScript. Original JSX/types/filenames are unavailable.
// Do not treat inferred file boundaries as the original authoring architecture.
import { clearPrivateClientState } from '../security/session-privacy.js';
import { w, sf, s, de, c0, D0, W, V, ec, yx, Xn, es, Ds, hu, Aj, le, qj, Jj, re, Mx, sa, hb, cp, pb, mi, yl, fb, Qn, mb, xb, Bx, un, Kl, pu, Wx, Gx, vl, Ii, gb, Ke, yb, at, jl, fu, mu, Le, dp, bl, vb, xu, jb, bb, wb, Xc, kb, $i, Nb, Vl, _b, wl, bg, gu, Cb, Ai, Sb, Eb, up, Pb, Wl, Mg, Fg, ts, fn, Oi, Rb, Ag, Mb, yu, et, xi, Wn, Tb, ra, rr, Fb, Lb, Db, zb, Or, Js, Hl, ed, sy, vu, Ib, Ms, ju, $b, ns, ia } from './runtime.js';
import { Ab, Et, qi, $t, l, Z, J, qb, py } from './localization.js';
class Sr extends Error {
  constructor(t, n, r, i) {
    super(r), this.status = t, this.code = n, this.data = i;
  }
}
let td = "";
const Ro = e => {
  td = e;
};
async function Yr(e, t, n, r) {
  const i = {
    ...r
  };
  n !== void 0 && (i["Content-Type"] = "application/json"), e !== "GET" && td && (i["X-CSRF-Token"] = td);
  let a;
  try {
    a = await fetch(t, {
      method: e,
      headers: i,
      credentials: "same-origin",
      body: n === void 0 ? void 0 : JSON.stringify(n)
    });
  } catch {
    throw new Sr(0, "network", l("تعذر الاتصال بالخادم"));
  }
  const o = await a.json().catch(() => ({}));
  if (a.status === 503 && o.error === "maintenance" && window.dispatchEvent(new CustomEvent("autocare-maintenance")), !a.ok) {
    const c = typeof o.message == "string" ? J(o.message) : Array.isArray(o.detail) ? l("تأكد من البيانات المدخلة") : l("حدث خطأ");
    throw new Sr(a.status, o.error ?? "error", c, o);
  }
  return o;
}
const M = {
    get: e => Yr("GET", e),
    post: (e, t, n) => Yr("POST", e, t ?? {}, n),
    del: e => Yr("DELETE", e),
    patch: (e, t) => Yr("PATCH", e, t),
    put: (e, t) => Yr("PUT", e, t)
  },
  Re = e => {
    const t = new URLSearchParams();
    Object.entries(e).forEach(([r, i]) => {
      i != null && i !== "" && t.set(r, String(i));
    });
    const n = t.toString();
    return n ? `?${n}` : "";
  },
  os = () => typeof crypto < "u" && "randomUUID" in crypto ? crypto.randomUUID() : `k-${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`,
  fy = w.createContext(null),
  ce = () => w.useContext(fy);
function Ub({
  children: e
}) {
  const privateClient = de();
  w.useEffect(() => {
    const resetOtherTab = event => {
      if (event.key === 'autocare.session.reset') {
        privateClient.clear();
        n(null);
        Ro("");
      }
    };
    window.addEventListener('storage', resetOtherTab);
    return () => window.removeEventListener('storage', resetOtherTab);
  }, [privateClient]);
  const [t, n] = w.useState(null),
    [r, i] = w.useState(!0),
    [a, o] = w.useState(!1);
  w.useEffect(() => {
    (async () => {
      try {
        const p = await M.get("/api/auth/me");
        Ro(p.csrf_token), n(p.user);
      } catch {
        clearPrivateClientState(privateClient);
        try {
          const p = await M.get("/api/auth/setup-needed");
          o(p.setup_needed), py(p.default_language);
        } catch {}
      } finally {
        i(!1);
      }
    })();
  }, []);
  const c = async (p, m) => {
      const y = await M.post("/api/auth/login", {
        username: p,
        password: m
      });
      clearPrivateClientState(privateClient);
      Ro(y.csrf_token), n(y.user);
    },
    d = async (p, m, y, j = {}) => {
      await M.post("/api/auth/setup", {
        username: p,
        full_name: m,
        password: y,
        ...j
      }), o(!1), await c(p, y);
    },
    u = async () => {
      try {
        await M.post("/api/auth/logout");
      } finally {
        clearPrivateClientState(privateClient);
        n(null), Ro("");
      }
    },
    h = p => !!(t != null && t.permissions.includes(p));
  return s.jsx(fy.Provider, {
    value: {
      user: t,
      loading: r,
      setupNeeded: a,
      login: c,
      setup: d,
      logout: u,
      can: h
    },
    children: e
  });
}
const Qb = [{
  items: [{
    to: "/",
    icon: bg,
    label: l("الرئيسية"),
    end: !0
  }]
}, {
  title: l("الورشة"),
  items: [{
    to: "/reception",
    icon: mu,
    label: l("استقبال عربية"),
    perm: "visits.write"
  }, {
    to: "/board",
    icon: Vl,
    label: l("متابعة التصليح"),
    perm: "visits.read"
  }, {
    to: "/audit",
    icon: xi,
    label: l("سجل الورشة"),
    perm: "audit.read"
  }, {
    to: "/alerts",
    icon: Qn,
    label: l("تنبيهات الورشة"),
    anyPerm: ["visits.read", "billing.read"]
  }, {
    to: "/search",
    icon: Wn,
    label: l("بحث عن عربية"),
    perm: "vehicles.read"
  }, {
    to: "/vehicles",
    icon: un,
    label: l("العربيات"),
    perm: "vehicles.read"
  }, {
    to: "/customers",
    icon: Ms,
    label: l("العملاء"),
    perm: "customers.read"
  }, {
    to: "/suppliers",
    icon: Wl,
    label: l("قطع الغيار"),
    perm: "visits.read"
  }, {
    to: "/reminders",
    icon: Qn,
    label: l("تذكيرات الصيانة"),
    perm: "visits.read"
  }]
}, {
  title: l("المال"),
  items: [{
    to: "/invoices",
    icon: Oi,
    label: l("الفواتير"),
    perm: "billing.read"
  }, {
    to: "/expenses",
    icon: yl,
    label: l("المصروفات"),
    perm: "expenses.read"
  }, {
    to: "/finance",
    icon: pu,
    label: l("الحسابات"),
    perm: "reports.financial"
  }, {
    to: "/reports",
    icon: Kl,
    label: l("التقارير"),
    perm: "visits.read"
  }]
}, {
  title: l("الإدارة"),
  items: [{
    to: "/technicians",
    icon: wl,
    label: l("الفنيين"),
    perm: "technicians.manage"
  }, {
    to: "/users",
    icon: sy,
    label: l("المستخدمين"),
    perm: "users.manage"
  }, {
    to: "/settings",
    icon: ra,
    label: l("الإعدادات"),
    perm: "settings.manage"
  }, {
    to: "/backup",
    icon: bl,
    label: l("النسخ الاحتياطي"),
    perm: "backup.manage"
  }]
}];
function fp({
  onNavigate: e
}) {
  const {
    can: t
  } = ce();
  return s.jsx("nav", {
    "aria-label": l("القائمة"),
    className: "space-y-5",
    children: Qb.map((n, r) => {
      const i = n.items.filter(a => (!a.perm || t(a.perm)) && (!a.anyPerm || a.anyPerm.some(t)));
      return i.length ? s.jsxs("div", {
        children: [n.title && s.jsx("p", {
          className: "mb-1 px-3 text-xs font-bold uppercase tracking-wider text-white/50",
          children: n.title
        }), s.jsx("ul", {
          className: "space-y-1",
          children: i.map(({
            to: a,
            icon: o,
            label: c,
            end: d
          }) => s.jsx("li", {
            children: s.jsxs(Mx, {
              to: a,
              end: d,
              onClick: e,
              className: ({
                isActive: u
              }) => `flex min-h-[48px] items-center gap-3 rounded-xl px-3 text-base font-bold transition ${u ? "bg-white text-brand-dark shadow" : "text-white/85 hover:bg-white/10"}`,
              children: [s.jsx(o, {
                size: 22,
                "aria-hidden": !0
              }), c]
            })
          }, a))
        })]
      }, r) : null;
    })
  });
}
const Hn = [{
    key: "engine",
    label: l("موتور"),
    icon: dp
  }, {
    key: "oil",
    label: l("زيت موتور"),
    icon: jb
  }, {
    key: "brakes",
    label: l("فرامل"),
    icon: vb
  }, {
    key: "ac",
    label: l("تكييف"),
    icon: Lb
  }, {
    key: "electrical",
    label: l("كهرباء"),
    icon: Ab
  }, {
    key: "battery",
    label: l("بطارية"),
    icon: fb
  }, {
    key: "tires",
    label: l("كفرات"),
    icon: yb
  }, {
    key: "suspension",
    label: l("مقدمة وعفشة"),
    icon: ns
  }, {
    key: "transmission",
    label: l("فتيس"),
    icon: dp
  }, {
    key: "cooling",
    label: l("تبريد"),
    icon: zb
  }, {
    key: "steering",
    label: l("دركسيون"),
    icon: bb
  }, {
    key: "exhaust",
    label: l("شكمان"),
    icon: $b
  }, {
    key: "body",
    label: l("سمكرة ودهان"),
    icon: Db
  }, {
    key: "inspection",
    label: l("فحص عام"),
    icon: jl
  }],
  Er = e => Hn.find(t => t.key === e),
  Ts = {
    received: {
      label: l("تم الاستلام"),
      icon: Le,
      cls: "bg-wait-soft text-wait"
    },
    inspection_pending: {
      label: l("في انتظار الفحص"),
      icon: Le,
      cls: "bg-wait-soft text-wait"
    },
    under_inspection: {
      label: l("جاري الفحص"),
      icon: Ai,
      cls: "bg-work-soft text-work"
    },
    waiting_quotation: {
      label: l("في انتظار عرض السعر"),
      icon: Le,
      cls: "bg-wait-soft text-wait"
    },
    waiting_approval: {
      label: l("في انتظار موافقة العميل"),
      icon: Le,
      cls: "bg-wait-soft text-wait"
    },
    waiting_parts: {
      label: l("في انتظار قطع الغيار"),
      icon: Le,
      cls: "bg-wait-soft text-wait"
    },
    in_progress: {
      label: l("جاري التصليح"),
      icon: Ai,
      cls: "bg-work-soft text-work"
    },
    quality_check: {
      label: l("فحص الجودة"),
      icon: jl,
      cls: "bg-work-soft text-work"
    },
    ready: {
      label: l("جاهزة للتسليم"),
      icon: Ke,
      cls: "bg-ok-soft text-ok"
    },
    delivered: {
      label: l("تم التسليم"),
      icon: Hl,
      cls: "bg-ok-soft text-ok"
    },
    cancelled: {
      label: l("ملغي"),
      icon: mi,
      cls: "bg-idle-soft text-idle"
    },
    critical: {
      label: l("حرج"),
      icon: Js,
      cls: "bg-bad-soft text-bad"
    }
  },
  my = ["received", "inspection_pending", "under_inspection", "waiting_quotation", "waiting_approval", "waiting_parts", "in_progress", "quality_check", "ready", "delivered", "cancelled"],
  Bi = {
    requested: {
      label: l("مطلوبة"),
      icon: Le,
      cls: "bg-wait-soft text-wait"
    },
    ordered: {
      label: l("تم الطلب"),
      icon: Le,
      cls: "bg-wait-soft text-wait"
    },
    purchased: {
      label: l("تم الشراء"),
      icon: Ke,
      cls: "bg-work-soft text-work"
    },
    received: {
      label: l("وصلت الورشة"),
      icon: Hl,
      cls: "bg-work-soft text-work"
    },
    installed: {
      label: l("تم التركيب"),
      icon: ns,
      cls: "bg-ok-soft text-ok"
    },
    returned: {
      label: l("مرتجعة"),
      icon: at,
      cls: "bg-idle-soft text-idle"
    },
    cancelled: {
      label: l("ملغية"),
      icon: mi,
      cls: "bg-idle-soft text-idle"
    },
    draft: {
      label: l("مسودة"),
      icon: Le,
      cls: "bg-idle-soft text-idle"
    },
    sent: {
      label: l("مُرسل للعميل"),
      icon: Le,
      cls: "bg-wait-soft text-wait"
    },
    approved: {
      label: l("موافق عليه"),
      icon: Ke,
      cls: "bg-ok-soft text-ok"
    },
    partially_approved: {
      label: l("موافقة جزئية"),
      icon: Ai,
      cls: "bg-work-soft text-work"
    },
    rejected: {
      label: l("مرفوض"),
      icon: at,
      cls: "bg-bad-soft text-bad"
    },
    expired: {
      label: l("منتهي"),
      icon: Js,
      cls: "bg-bad-soft text-bad"
    },
    pending: {
      label: l("في الانتظار"),
      icon: Le,
      cls: "bg-wait-soft text-wait"
    },
    unpaid: {
      label: l("غير مدفوعة"),
      icon: Js,
      cls: "bg-bad-soft text-bad"
    },
    partial: {
      label: l("مدفوعة جزئياً"),
      icon: Ai,
      cls: "bg-wait-soft text-wait"
    },
    paid: {
      label: l("مدفوعة"),
      icon: Ke,
      cls: "bg-ok-soft text-ok"
    },
    overpaid: {
      label: l("مدفوع زيادة (للعميل رصيد)"),
      icon: Js,
      cls: "bg-wait-soft text-wait"
    },
    void: {
      label: l("ملغاة"),
      icon: mi,
      cls: "bg-idle-soft text-idle"
    },
    issued: {
      label: l("صادرة"),
      icon: Ke,
      cls: "bg-work-soft text-work"
    },
    active: {
      label: l("ساري"),
      icon: Ke,
      cls: "bg-ok-soft text-ok"
    },
    overdue: {
      label: l("متأخر"),
      icon: Js,
      cls: "bg-bad-soft text-bad"
    },
    due_soon: {
      label: l("قرب موعده"),
      icon: Le,
      cls: "bg-wait-soft text-wait"
    },
    upcoming: {
      label: l("قادم"),
      icon: Le,
      cls: "bg-work-soft text-work"
    },
    done: {
      label: l("تم"),
      icon: Ke,
      cls: "bg-ok-soft text-ok"
    },
    dismissed: {
      label: l("تم تجاهله"),
      icon: mi,
      cls: "bg-idle-soft text-idle"
    },
    open: {
      label: l("مفتوحة"),
      icon: Le,
      cls: "bg-wait-soft text-wait"
    }
  };
function Xe({
  status: e
}) {
  const t = Bi[e] ?? {
      label: e,
      icon: at,
      cls: "bg-idle-soft text-idle"
    },
    n = t.icon;
  return s.jsxs("span", {
    className: `inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold ring-1 ring-inset ring-current/20 ${t.cls}`,
    children: [s.jsx(n, {
      size: 16
    }), t.label]
  });
}
function Pr({
  status: e
}) {
  const t = Ts[e] ?? {
      label: e,
      icon: at,
      cls: "bg-idle-soft text-idle"
    },
    n = t.icon;
  return s.jsxs("span", {
    className: `inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold ring-1 ring-inset ring-current/20 ${t.cls}`,
    children: [s.jsx(n, {
      size: 16
    }), t.label]
  });
}
function Mo({
  to: e,
  icon: t,
  label: n,
  tone: r = "brand"
}) {
  const i = {
    brand: "from-brand to-blue-700",
    ok: "from-emerald-600 to-ok",
    wait: "from-orange-500 to-wait",
    idle: "from-slate-600 to-slate-700"
  };
  return s.jsxs(re, {
    to: e,
    className: `group flex min-h-[150px] flex-col items-center justify-center gap-3 rounded-3xl bg-gradient-to-br p-5 text-white shadow-lift transition active:scale-95 hover:-translate-y-0.5 hover:brightness-110 ${i[r]}`,
    children: [s.jsx("span", {
      className: "flex h-16 w-16 items-center justify-center rounded-2xl bg-white/20 ring-1 ring-white/30",
      children: s.jsx(t, {
        size: 36,
        strokeWidth: 1.9,
        "aria-hidden": !0
      })
    }), s.jsx("span", {
      className: "text-center text-xl font-extrabold leading-tight",
      children: n
    })]
  });
}
function We({
  to: e,
  icon: t,
  label: n,
  tone: r = "brand"
}) {
  const i = {
    brand: "bg-brand-soft text-brand",
    ok: "bg-ok-soft text-ok",
    wait: "bg-wait-soft text-wait",
    idle: "bg-slate-100 text-slate-600"
  }[r];
  return s.jsxs(re, {
    to: e,
    className: "flex min-h-[72px] items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-card transition hover:-translate-y-0.5 hover:border-brand/40 active:scale-95",
    children: [s.jsx("span", {
      className: `flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${i}`,
      children: s.jsx(t, {
        size: 26,
        "aria-hidden": !0
      })
    }), s.jsx("span", {
      className: "text-lg font-bold leading-tight",
      children: n
    })]
  });
}
function P({
  children: e,
  onClick: t,
  type: n = "button",
  kind: r = "primary",
  disabled: i,
  icon: a
}) {
  const o = {
    primary: "bg-brand text-white shadow-lift hover:bg-brand-dark",
    secondary: "bg-white text-ink border-2 border-slate-200 shadow-sm hover:border-brand/40 hover:bg-slate-50",
    danger: "bg-bad text-white shadow-sm hover:brightness-110"
  }[r];
  return s.jsxs("button", {
    type: n,
    onClick: t,
    disabled: i,
    className: `inline-flex min-h-[56px] max-w-full items-center justify-center gap-2 rounded-2xl px-5 text-lg font-bold sm:px-6 sm:text-xl transition active:scale-95 disabled:opacity-50 ${o}`,
    children: [a && s.jsx(a, {
      size: 24,
      "aria-hidden": !0
    }), e]
  });
}
function E({
  label: e,
  error: t,
  children: n
}) {
  return s.jsxs("div", {
    children: [s.jsxs("label", {
      className: "block",
      children: [s.jsx("span", {
        className: "mb-1 block text-base font-semibold",
        children: e
      }), n]
    }), t && s.jsx("p", {
      role: "alert",
      className: "mt-1 text-base font-semibold text-bad",
      children: t
    })]
  });
}
function B({
  title: e,
  children: t,
  action: n
}) {
  return s.jsxs("section", {
    className: "rounded-3xl border border-slate-200/70 bg-white p-5 shadow-card sm:p-6",
    children: [(e || n) && s.jsxs("div", {
      className: "mb-4 flex flex-wrap items-center justify-between gap-3",
      children: [e ? s.jsxs("h2", {
        className: "flex items-center gap-2 text-xl font-extrabold sm:text-2xl",
        children: [s.jsx("span", {
          className: "h-6 w-1.5 rounded-full bg-brand",
          "aria-hidden": !0
        }), e]
      }) : s.jsx("span", {}), n]
    }), t]
  });
}
function Ie({
  icon: e = Wn,
  text: t
}) {
  return s.jsxs("div", {
    className: "flex flex-col items-center gap-3 rounded-2xl bg-slate-50 py-10 text-slate-500",
    children: [s.jsx("span", {
      className: "flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-card",
      children: s.jsx(e, {
        size: 40,
        "aria-hidden": !0
      })
    }), s.jsx("p", {
      className: "text-lg font-semibold",
      children: t
    })]
  });
}
function $({
  message: e
}) {
  return e ? s.jsxs("div", {
    role: "alert",
    className: "flex items-center gap-2 rounded-2xl bg-bad-soft p-4 text-lg font-bold text-bad",
    children: [s.jsx(at, {
      size: 24
    }), e]
  }) : null;
}
function ie() {
  return s.jsx("div", {
    className: "flex justify-center py-10",
    children: s.jsx(Ai, {
      className: "animate-spin text-brand",
      size: 48
    })
  });
}
const $e = e => e ? new Date(e).toLocaleDateString($t, {
    year: "numeric",
    month: "long",
    day: "numeric"
  }) : "—",
  Gn = e => e == null ? "—" : Z("{0} كم", e.toLocaleString($t));
// Recovered route component for /account; original filename/name unknown.
function Kb() {
  var o;
  const {
      user: e
    } = ce(),
    [t, n] = w.useState({
      current_password: "",
      new_password: "",
      again: ""
    }),
    r = V({
      mutationFn: () => M.post("/api/auth/change-password", {
        current_password: t.current_password,
        new_password: t.new_password
      }),
      onSuccess: () => n({
        current_password: "",
        new_password: "",
        again: ""
      })
    }),
    i = t.again !== "" && t.again !== t.new_password,
    a = c => {
      c.preventDefault(), i || r.mutate();
    };
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "text-3xl font-extrabold",
      children: [l("حسابي —"), " ", e == null ? void 0 : e.full_name]
    }), s.jsx(B, {
      title: l("تغيير كلمة المرور"),
      children: s.jsxs("form", {
        onSubmit: a,
        className: "grid max-w-xl gap-4",
        children: [s.jsx(E, {
          label: l("كلمة المرور الحالية"),
          children: s.jsx("input", {
            type: "password",
            value: t.current_password,
            onChange: c => n({
              ...t,
              current_password: c.target.value
            }),
            dir: "ltr",
            required: !0,
            autoComplete: "current-password"
          })
        }), s.jsx(E, {
          label: l("كلمة المرور الجديدة (٨ أحرف على الأقل)"),
          children: s.jsx("input", {
            type: "password",
            value: t.new_password,
            onChange: c => n({
              ...t,
              new_password: c.target.value
            }),
            dir: "ltr",
            required: !0,
            minLength: 8,
            autoComplete: "new-password"
          })
        }), s.jsx(E, {
          label: l("أعد كتابتها"),
          error: i ? l("غير متطابقة") : void 0,
          children: s.jsx("input", {
            type: "password",
            value: t.again,
            onChange: c => n({
              ...t,
              again: c.target.value
            }),
            dir: "ltr",
            required: !0,
            autoComplete: "new-password"
          })
        }), s.jsx($, {
          message: (o = r.error) == null ? void 0 : o.message
        }), r.isSuccess && s.jsx("p", {
          className: "font-bold text-ok",
          children: l("✔ تم تغيير كلمة المرور. أجهزتك الأخرى سُجّل خروجها.")
        }), s.jsx(P, {
          type: "submit",
          icon: gu,
          disabled: r.isPending || i,
          children: l("تغيير")
        })]
      })
    })]
  });
}
const ku = [{
    label: "الورشة",
    items: [["job.", "أوامر الشغل"], ["operation.", "أعمال التصليح"], ["inspection.", "الفحص الأولي"], ["qc.", "فحص الجودة"], ["qc.passed", "اجتياز فحص الجودة"], ["qc.failed", "رفض فحص الجودة"], ["delivery.", "التسليم"], ["part.", "قطع الغيار"], ["quote.", "عروض الأسعار"], ["vehicle.", "العربيات"], ["visit.", "الزيارات"], ["customer.", "العملاء"], ["supplier.", "الموردون"], ["warranty.", "الضمان"], ["reminder.", "تذكيرات الصيانة"], ["attachment.", "المرفقات"]]
  }, {
    label: "المالية",
    items: [["invoice.", "الفواتير"], ["payment.", "المدفوعات"], ["deposit.", "العربون"], ["refund.", "المبالغ المستردة"], ["credit_note.", "الإشعارات الدائنة"], ["expense.", "المصروفات"], ["expense_category.", "تصنيفات المصروفات"]]
  }, {
    label: "الإدارة",
    items: [["user.", "المستخدمون"], ["login.", "تسجيل الدخول"], ["logout", "تسجيل الخروج"], ["password.", "كلمات المرور"], ["technician.", "الفنيون"], ["settings.", "الإعدادات"], ["backup.", "النسخ الاحتياطي"], ["restore.", "استعادة النسخ"], ["report.", "التقارير"], ["setup.", "إعداد النظام"]]
  }],
  To = {
    job: "أمر شغل",
    operation: "عملية تصليح",
    inspection: "فحص أولي",
    part: "قطعة غيار",
    quotation: "عرض سعر",
    vehicle: "عربية",
    visit: "زيارة",
    customer: "عميل",
    supplier: "مورد",
    warranty: "ضمان",
    reminder: "تذكير",
    invoice: "فاتورة",
    payment: "دفعة",
    refund: "مبلغ مسترد",
    credit_note: "إشعار دائن",
    expense: "مصروف",
    expense_category: "تصنيف مصروف",
    user: "مستخدم",
    technician: "فني",
    settings: "إعدادات",
    backup: "نسخة احتياطية",
    report: "تقرير"
  },
  mp = {
    create: "إضافة",
    update: "تعديل",
    receive: "استلام",
    status: "تغيير الحالة",
    assign: "تعيين فني",
    unassign: "إلغاء تعيين فني",
    complete: "إتمام",
    override: "استثناء إداري",
    return: "إرجاع",
    send: "إرسال",
    approval: "قرار العميل",
    item_add: "إضافة بند",
    item_remove: "حذف بند",
    print: "طباعة",
    delete_draft: "حذف مسودة",
    issue: "إصدار",
    cancel: "إلغاء",
    void: "إلغاء",
    change_owner: "تغيير المالك",
    claim: "تسجيل مطالبة",
    claim_decide: "قرار المطالبة",
    upload: "رفع ملف",
    remove: "حذف",
    success: "نجاح",
    failed: "فشل",
    change: "تغيير",
    change_failed: "فشل التغيير",
    reset: "إعادة تعيين",
    download: "تنزيل",
    settings: "تعديل الإعدادات",
    recovery_secret_generated: "إنشاء مفتاح استعادة",
    denied: "رفض",
    start: "بدء",
    export: "تصدير",
    first_admin: "إنشاء المدير الأول",
    sent: "تم الإرسال",
    dismissed: "تجاهل",
    done: "مكتمل"
  };
function Vb(e) {
  if (e === "job.status.auto") return l("تغيير الحالة تلقائياً");
  if (e === "qc.passed") return l("اجتياز فحص الجودة");
  if (e === "qc.failed") return l("رفض فحص الجودة");
  if (e === "logout") return l("تسجيل الخروج");
  const [t, n] = e.split("."),
    r = ku.flatMap(i => i.items).find(([i]) => i === `${t}.`);
  return r && mp[n] ? `${l(r[1])} · ${l(mp[n])}` : e;
}
const Wb = e => {
    var t;
    return l(((t = ku.flatMap(n => n.items).find(([n]) => n === e)) == null ? void 0 : t[1]) ?? e);
  },
  Hb = {
    status: "الحالة",
    notes: "الملاحظات",
    override: "الاستثناء الإداري",
    name: "الاسم",
    full_name: "الاسم الكامل",
    username: "اسم المستخدم",
    role: "الصلاحية",
    is_active: "نشط",
    amount: "المبلغ",
    total: "الإجمالي",
    description: "الوصف",
    mileage: "قراءة العداد",
    final_mileage: "العداد عند التسليم",
    final_condition: "الحالة عند التسليم",
    ack_name: "اسم المستلم",
    plate: "رقم اللوحة",
    make: "الماركة",
    model: "الموديل",
    model_year: "سنة الصنع",
    color: "اللون",
    vin: "رقم الهيكل",
    mobile: "الموبايل",
    phone: "الهاتف",
    email: "البريد الإلكتروني",
    address: "العنوان",
    vehicle_id: "مرجع العربية",
    customer_id: "مرجع العميل",
    technician_id: "مرجع الفني",
    job_id: "مرجع أمر الشغل",
    invoice_id: "مرجع الفاتورة",
    job: "رقم أمر الشغل",
    invoice: "رقم الفاتورة",
    invoice_no: "رقم الفاتورة",
    quote_no: "رقم عرض السعر",
    quantity: "الكمية",
    unit_price: "سعر الوحدة",
    cost: "التكلفة",
    unit_cost: "تكلفة الوحدة",
    category: "التصنيف",
    method: "طريقة الدفع",
    reason: "السبب",
    date: "التاريخ",
    format: "الصيغة",
    rows: "عدد الصفوف",
    id: "المرجع",
    size: "الحجم",
    lang: "اللغة",
    mode: "نوع الطباعة",
    deposits_applied: "العربون المستخدم",
    decisions: "القرارات",
    complaint: "شكوى العميل",
    warranty: "الضمان",
    kind: "النوع",
    end: "تاريخ النهاية",
    claim: "المطالبة",
    decision: "القرار",
    currency: "العملة",
    blockers: "متطلبات غير مكتملة"
  },
  Gb = e => l(Hb[e] ?? e.replace(/_/g, " "));
function xp(e, t) {
  var n, r;
  return t == null || t === "" ? "—" : typeof t == "boolean" ? l(t ? "نعم" : "لا") : e === "status" && typeof t == "string" ? ((n = Ts[t]) == null ? void 0 : n.label) ?? ((r = Bi[t]) == null ? void 0 : r.label) ?? t : typeof t == "object" ? JSON.stringify(t, null, 2) : String(t);
}
function gp(e) {
  return `${e.getFullYear()}-${String(e.getMonth() + 1).padStart(2, "0")}-${String(e.getDate()).padStart(2, "0")}`;
}
const Fo = {
    action: "",
    username: "",
    date_from: "",
    date_to: "",
    entity_type: "",
    entity_id: ""
  },
  Ca = 50,
  Jb = {
    job: ["/jobs/", "visits.read"],
    vehicle: ["/vehicles/", "vehicles.read"],
    invoice: ["/invoices/", "billing.read"],
    quotation: ["/quotations/", "visits.read"]
  };
// Recovered route component for /audit; original filename/name unknown.
function Yb() {
  var v, N, x;
  const {
      can: e
    } = ce(),
    [t, n] = w.useState(Fo),
    [r, i] = w.useState(Fo),
    [a, o] = w.useState(0),
    [c, d] = w.useState(null),
    [u, h] = w.useState(""),
    p = W({
      queryKey: ["audit", r, a],
      queryFn: () => M.get(`/api/audit${Re({
        ...r,
        limit: Ca,
        offset: a
      })}`)
    });
  function m(f = t) {
    if (f.date_from && f.date_to && f.date_from > f.date_to) {
      h(l("تاريخ النهاية يجب أن يكون بعد تاريخ البداية أو مساوياً له"));
      return;
    }
    const g = {
      ...f,
      username: f.username.trim().toLowerCase()
    };
    h(""), n(g), i(g), o(0), d(null);
  }
  function y(f) {
    const g = new Date(),
      b = new Date(g);
    f === "month" ? b.setDate(1) : b.setDate(b.getDate() - f + 1), m({
      ...t,
      date_from: gp(b),
      date_to: gp(g)
    });
  }
  const j = ((v = p.data) == null ? void 0 : v.total) ?? 0;
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("header", {
      className: "flex flex-wrap items-start justify-between gap-3",
      children: [s.jsxs("div", {
        children: [s.jsxs("h1", {
          className: "flex items-center gap-2 text-3xl font-extrabold",
          children: [s.jsx(xi, {
            className: "shrink-0 text-brand",
            size: 34
          }), l("سجل الورشة")]
        }), s.jsx("p", {
          className: "mt-2 text-slate-600",
          children: l("كل العمليات المسجّلة للورشة والمالية والإدارة، من الأحدث للأقدم.")
        })]
      }), s.jsx(P, {
        kind: "secondary",
        icon: Rb,
        disabled: p.isFetching,
        onClick: () => p.refetch(),
        children: l("تحديث السجل")
      })]
    }), s.jsx(B, {
      title: l("البحث في السجل"),
      children: s.jsxs("form", {
        onSubmit: f => {
          f.preventDefault(), m();
        },
        children: [s.jsxs("div", {
          className: "grid gap-4 sm:grid-cols-2 xl:grid-cols-3",
          children: [s.jsx(E, {
            label: l("نوع العملية"),
            children: s.jsxs("select", {
              value: t.action,
              onChange: f => n({
                ...t,
                action: f.target.value
              }),
              children: [s.jsx("option", {
                value: "",
                children: l("كل العمليات")
              }), ku.map(f => s.jsx("optgroup", {
                label: l(f.label),
                children: f.items.map(([g, b]) => s.jsx("option", {
                  value: g,
                  children: l(b)
                }, g))
              }, f.label))]
            })
          }), s.jsx(E, {
            label: l("اسم المستخدم"),
            children: s.jsx("input", {
              value: t.username,
              placeholder: l("اسم الدخول بالكامل"),
              onChange: f => n({
                ...t,
                username: f.target.value
              }),
              autoComplete: "off",
              dir: "ltr"
            })
          }), s.jsx(E, {
            label: l("نوع السجل"),
            children: s.jsxs("select", {
              value: t.entity_type,
              onChange: f => n({
                ...t,
                entity_type: f.target.value,
                entity_id: ""
              }),
              children: [s.jsx("option", {
                value: "",
                children: l("كل السجلات")
              }), Object.entries(To).map(([f, g]) => s.jsx("option", {
                value: f,
                children: l(g)
              }, f))]
            })
          }), s.jsx(E, {
            label: l("من تاريخ"),
            children: s.jsx("input", {
              type: "date",
              value: t.date_from,
              onChange: f => n({
                ...t,
                date_from: f.target.value
              }),
              dir: "ltr"
            })
          }), s.jsx(E, {
            label: l("إلى تاريخ"),
            children: s.jsx("input", {
              type: "date",
              value: t.date_to,
              onChange: f => n({
                ...t,
                date_to: f.target.value
              }),
              dir: "ltr"
            })
          }), s.jsx("div", {
            className: "flex flex-wrap items-end gap-2 pb-1",
            children: [[1, "عمليات اليوم"], [7, "آخر 7 أيام"], ["month", "هذا الشهر"]].map(([f, g]) => s.jsx("button", {
              type: "button",
              className: "min-h-[44px] rounded-xl border border-slate-200 px-3 text-sm font-bold text-brand hover:bg-slate-50",
              onClick: () => y(f),
              children: l(String(g))
            }, g))
          })]
        }), u && s.jsx("p", {
          role: "alert",
          className: "mt-3 font-semibold text-bad",
          children: u
        }), s.jsxs("div", {
          className: "mt-5 flex flex-wrap gap-3",
          children: [s.jsx(P, {
            type: "submit",
            icon: Nb,
            children: l("تطبيق الفلاتر")
          }), s.jsx(P, {
            kind: "secondary",
            onClick: () => m(Fo),
            children: l("مسح الفلاتر")
          })]
        })]
      })
    }), Object.values(r).some(Boolean) && s.jsxs("div", {
      className: "flex flex-wrap items-center gap-2 rounded-xl bg-work-soft p-3 text-sm text-work",
      children: [s.jsx("strong", {
        children: l("الفلاتر المطبّقة:")
      }), Object.entries(r).filter(([, f]) => f).map(([f, g]) => s.jsx("span", {
        className: "max-w-full break-all rounded-lg bg-white px-3 py-1",
        children: f === "action" ? Wb(g) : f === "entity_type" ? l(To[g] ?? g) : f === "date_from" ? `${l("من تاريخ")}: ${g}` : f === "date_to" ? `${l("إلى تاريخ")}: ${g}` : g
      }, f))]
    }), p.isLoading ? s.jsx(ie, {}) : p.isError ? s.jsxs(B, {
      children: [s.jsx($, {
        message: p.error.message
      }), s.jsx("div", {
        className: "mt-3",
        children: s.jsx(P, {
          kind: "secondary",
          onClick: () => p.refetch(),
          children: l("إعادة المحاولة")
        })
      })]
    }) : s.jsxs(B, {
      title: Z("{0} عملية", j),
      children: [s.jsx("p", {
        className: "mb-4 text-sm text-slate-500",
        children: l("افتح أي عملية لعرض تفاصيل التغيير. الفلاتر تشمل السجل بالكامل.")
      }), (N = p.data) != null && N.items.length ? s.jsx("ol", {
        className: "space-y-3",
        children: p.data.items.map(f => {
          var S, T, R, F, X;
          const g = [...new Set([...Object.keys(f.before ?? {}), ...Object.keys(f.after ?? {})])].filter(te => {
              var L, I;
              return JSON.stringify((L = f.before) == null ? void 0 : L[te]) !== JSON.stringify((I = f.after) == null ? void 0 : I[te]);
            }),
            b = f.entity_type ? Jb[f.entity_type] : void 0,
            k = ((S = f.after) == null ? void 0 : S.plate) ?? ((T = f.before) == null ? void 0 : T.plate) ?? ((R = f.after) == null ? void 0 : R.description) ?? ((F = f.after) == null ? void 0 : F.name) ?? ((X = f.after) == null ? void 0 : X.full_name),
            _ = c === f.id;
          return s.jsxs("li", {
            className: `overflow-hidden rounded-2xl border ${_ ? "border-brand/40" : "border-slate-200"}`,
            children: [s.jsxs("button", {
              type: "button",
              "aria-expanded": _,
              "aria-controls": `audit-${f.id}`,
              onClick: () => d(_ ? null : f.id),
              className: "flex w-full items-start gap-3 p-4 text-start hover:bg-slate-50",
              children: [s.jsx("span", {
                className: `mt-1 rounded-xl p-2 ${f.action === "qc.passed" ? "bg-ok-soft text-ok" : f.action.endsWith("failed") ? "bg-bad-soft text-bad" : "bg-work-soft text-work"}`,
                children: s.jsx(xi, {
                  size: 21
                })
              }), s.jsxs("span", {
                className: "min-w-0 flex-1",
                children: [s.jsx("span", {
                  className: "block break-words font-extrabold",
                  children: Vb(f.action)
                }), s.jsxs("span", {
                  className: "mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-slate-600",
                  children: [s.jsx("span", {
                    children: f.username ?? l("النظام")
                  }), s.jsx("time", {
                    dateTime: f.ts,
                    children: new Date(f.ts).toLocaleString($t)
                  }), f.entity_type && s.jsx("span", {
                    className: "font-semibold text-brand",
                    children: l(To[f.entity_type] ?? f.entity_type)
                  })]
                }), typeof k == "string" && s.jsx("span", {
                  className: "mt-2 block break-words text-sm text-slate-700",
                  children: k
                })]
              }), s.jsx(Gx, {
                size: 20,
                className: `mt-1 shrink-0 text-slate-400 transition ${_ ? "rotate-180" : ""}`
              })]
            }), f.reason && s.jsxs("p", {
              className: "break-words px-4 pb-3 text-sm text-slate-700",
              children: [l("السبب:"), " ", J(f.reason)]
            }), _ && s.jsxs("div", {
              id: `audit-${f.id}`,
              className: "border-t border-slate-200 bg-slate-50 p-4",
              children: [g.length ? s.jsx("div", {
                className: "space-y-2",
                children: g.map(te => {
                  var L, I;
                  return s.jsxs("div", {
                    className: "grid gap-2 rounded-xl bg-white p-3 sm:grid-cols-[1fr_2fr_2fr]",
                    children: [s.jsx("strong", {
                      className: "break-words text-sm",
                      children: Gb(te)
                    }), s.jsxs("div", {
                      className: "min-w-0",
                      children: [s.jsx("span", {
                        className: "text-xs font-bold text-slate-500",
                        children: l("قبل")
                      }), s.jsx("p", {
                        className: "mt-1 whitespace-pre-wrap break-words text-sm text-slate-600",
                        children: xp(te, (L = f.before) == null ? void 0 : L[te])
                      })]
                    }), s.jsxs("div", {
                      className: "min-w-0",
                      children: [s.jsx("span", {
                        className: "text-xs font-bold text-brand",
                        children: l("بعد")
                      }), s.jsx("p", {
                        className: "mt-1 whitespace-pre-wrap break-words text-sm font-semibold",
                        children: xp(te, (I = f.after) == null ? void 0 : I[te])
                      })]
                    })]
                  }, te);
                })
              }) : s.jsx("p", {
                className: "text-sm text-slate-600",
                children: l("تم تسجيل الحدث بدون تفاصيل تغيير إضافية.")
              }), s.jsxs("div", {
                className: "mt-4 flex flex-wrap gap-3",
                children: [b && f.entity_id && e(b[1]) && s.jsx(re, {
                  className: "inline-flex min-h-[44px] items-center rounded-xl bg-brand px-4 font-bold text-white",
                  to: `${b[0]}${encodeURIComponent(f.entity_id)}`,
                  children: l("فتح السجل المرتبط")
                }), f.entity_type && f.entity_id && s.jsx("button", {
                  className: "min-h-[44px] rounded-xl border border-slate-300 bg-white px-4 font-bold",
                  onClick: () => m({
                    ...r,
                    entity_type: f.entity_type,
                    entity_id: f.entity_id
                  }),
                  children: l("عمليات هذا السجل فقط")
                })]
              }), s.jsxs("details", {
                className: "mt-3 text-xs text-slate-500",
                children: [s.jsx("summary", {
                  className: "cursor-pointer py-2",
                  children: l("معلومات التتبع")
                }), s.jsxs("p", {
                  dir: "ltr",
                  className: "break-all",
                  children: ["#", f.id, " · ", f.action, " · ", f.entity_type, " ", f.entity_id]
                }), f.ip && s.jsxs("p", {
                  dir: "ltr",
                  className: "mt-1",
                  children: ["IP: ", f.ip]
                })]
              })]
            })]
          }, f.id);
        })
      }) : s.jsx(Ie, {
        icon: xi,
        text: l("لا توجد عمليات تطابق الفلاتر")
      }), s.jsxs("div", {
        className: "mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4",
        children: [s.jsx("p", {
          className: "text-sm text-slate-600",
          role: "status",
          children: j ? Z("عرض {0}–{1} من {2}", Math.min(a + 1, j), Math.min(a + (((x = p.data) == null ? void 0 : x.items.length) ?? 0), j), j) : l("لا توجد نتائج")
        }), s.jsxs("div", {
          className: "flex gap-2",
          children: [s.jsx(P, {
            kind: "secondary",
            disabled: a === 0 || p.isFetching,
            onClick: () => {
              o(Math.max(0, a - Ca)), d(null);
            },
            children: l("السابق")
          }), s.jsx(P, {
            kind: "secondary",
            disabled: a + Ca >= j || p.isFetching,
            onClick: () => {
              o(a + Ca), d(null);
            },
            children: l("التالي")
          })]
        })]
      })]
    })]
  });
}
async function Zb(e) {
  const t = [];
  for (let n = 0; n < e.length; n += 4) {
    const r = await Promise.all(e.slice(n, n + 4).map(async i => {
      const a = await M.get(`/api/jobs/${i.id}/delivery-readiness`),
        o = new Set(a.blockers.map(c => c.code));
      return ["no_invoice", "draft_invoice", "unbilled_items"].some(c => o.has(c)) ? {
        job: i,
        draftId: a.draft_invoice_id,
        partial: o.has("unbilled_items")
      } : null;
    }));
    for (const i of r) i && t.push(i);
  }
  return t;
}
async function Xb() {
  const e = new Map();
  for (const t of ["unpaid", "partial"]) for (let n = 0;; n += 200) {
    const r = await M.get(`/api/invoices${Re({
      status: "issued",
      payment_status: t,
      limit: 200,
      offset: n
    })}`);
    for (const i of r) i.status === "issued" && Number(i.outstanding) > 0 && e.set(i.id, i);
    if (r.length < 200) break;
  }
  return [...e.values()];
}
function e2() {
  const {
      can: e
    } = ce(),
    t = e("visits.read"),
    n = e("billing.read"),
    r = W({
      queryKey: ["board"],
      enabled: t,
      queryFn: () => M.get("/api/board"),
      refetchInterval: 6e4
    }),
    i = (r.data ?? []).filter(c => c.status === "ready"),
    a = W({
      queryKey: ["workshop-alerts", "missing", i.map(c => c.id)],
      enabled: t && n && !!r.data && !r.isError,
      queryFn: () => Zb(i),
      refetchInterval: 6e4
    }),
    o = W({
      queryKey: ["workshop-alerts", "outstanding"],
      enabled: n,
      queryFn: Xb,
      refetchInterval: 6e4
    });
  return {
    workshop: t,
    billing: n,
    board: r,
    ready: i,
    missing: a,
    outstanding: o
  };
}
const yp = {
  ready: "جاهزة ولم تُسلّم",
  missing: "جاهزة وتحتاج استكمال الفوترة",
  outstanding: "فواتير عليها مبالغ متبقية"
};
// Recovered route component for /alerts; original filename/name unknown.
function xy({
  full: e = !1
}) {
  var v, N;
  const t = e2(),
    [n] = sa(),
    [r, i] = w.useState(""),
    [a, o] = w.useState(50),
    c = [{
      key: "ready",
      allowed: t.workshop,
      icon: un,
      count: t.ready.length,
      loading: t.board.isPending,
      failed: t.board.isError,
      color: "text-work bg-work-soft",
      description: "اجتازت فحص الجودة وتنتظر تسليم العميل"
    }, {
      key: "missing",
      allowed: t.workshop && t.billing,
      icon: Oi,
      count: ((v = t.missing.data) == null ? void 0 : v.length) ?? 0,
      loading: t.board.isPending || t.missing.isPending,
      failed: t.board.isError || t.missing.isError,
      color: "text-wait bg-wait-soft",
      description: "تشمل الأوامر بدون فاتورة صادرة أو ببنود غير مفوترة"
    }, {
      key: "outstanding",
      allowed: t.billing,
      icon: ju,
      count: ((N = t.outstanding.data) == null ? void 0 : N.length) ?? 0,
      loading: t.outstanding.isPending,
      failed: t.outstanding.isError,
      color: "text-bad bg-bad-soft",
      description: "تشمل غير المدفوعة والمدفوعة جزئياً، حتى بعد التسليم"
    }].filter(x => x.allowed);
  if (!c.length) return e ? s.jsx(Ie, {
    icon: Qn,
    text: l("ليس لديك صلاحية عرض هذه التنبيهات")
  }) : null;
  const d = c.find(x => x.key === n.get("type")) ?? c[0],
    u = t.board.isFetching || t.missing.isFetching || t.outstanding.isFetching,
    h = () => {
      t.workshop && t.board.refetch(), t.workshop && t.billing && t.board.data && !t.board.isError && t.missing.refetch(), t.billing && t.outstanding.refetch();
    },
    p = r.trim().toLowerCase(),
    m = (d.key === "missing" ? t.missing.data ?? [] : t.ready.map(x => ({
      job: x,
      draftId: void 0,
      partial: !1
    }))).filter(({
      job: x
    }) => `${x.plate ?? ""} ${x.customer} ${x.job_no} ${x.make} ${x.model}`.toLowerCase().includes(p)),
    y = (t.outstanding.data ?? []).filter(x => `${x.number} ${x.customer.name} ${x.vehicle.plate ?? ""}`.toLowerCase().includes(p)),
    j = d.key === "outstanding" ? y.length : m.length;
  return s.jsxs(s.Fragment, {
    children: [e && s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(Qn, {
        size: 34
      }), l("تنبيهات الورشة")]
    }), s.jsxs(B, {
      title: l(e ? "المتابعة المطلوبة" : "تنبيهات تحتاج متابعة"),
      action: s.jsx(P, {
        kind: "secondary",
        disabled: u,
        onClick: h,
        children: l("تحديث")
      }),
      children: [s.jsx("p", {
        className: "mb-4 text-sm text-slate-600",
        children: l("تتحدّث تلقائياً كل دقيقة أثناء فتح الصفحة. يختفي التنبيه بعد معالجة سببه وتحديث البيانات.")
      }), s.jsx("div", {
        className: "grid gap-3 md:grid-cols-3",
        children: c.map(x => {
          const f = x.icon;
          return s.jsxs(re, {
            to: `/alerts?type=${x.key}`,
            onClick: () => {
              i(""), o(50);
            },
            className: `rounded-2xl border-2 p-4 transition hover:shadow-md ${e && d.key === x.key ? "border-brand" : "border-transparent"} ${x.color}`,
            children: [s.jsxs("div", {
              className: "flex items-center justify-between gap-3",
              children: [s.jsx(f, {
                size: 28
              }), s.jsx("strong", {
                className: "text-3xl",
                children: x.failed ? "—" : x.loading ? "…" : x.count
              })]
            }), s.jsx("h3", {
              className: "mt-3 font-extrabold",
              children: l(yp[x.key])
            }), s.jsx("p", {
              className: "mt-1 text-sm",
              children: x.failed ? l("تعذر تحديث التنبيهات") : l(x.description)
            })]
          }, x.key);
        })
      })]
    }), e && s.jsxs(B, {
      title: l(yp[d.key]),
      children: [s.jsx("div", {
        className: "mb-4 max-w-xl",
        children: s.jsx(E, {
          label: l("بحث باللوحة أو العميل أو الرقم"),
          children: s.jsx("input", {
            value: r,
            onChange: x => {
              i(x.target.value), o(50);
            }
          })
        })
      }), d.failed ? s.jsxs(s.Fragment, {
        children: [s.jsx($, {
          message: l("تعذر تحديث التنبيهات. أعد المحاولة للتأكد من القائمة الحالية.")
        }), s.jsx(P, {
          kind: "secondary",
          onClick: h,
          children: l("إعادة المحاولة")
        })]
      }) : d.loading ? s.jsx(ie, {}) : j ? s.jsxs(s.Fragment, {
        children: [s.jsx("p", {
          className: "mb-3 text-sm text-slate-500",
          children: Z("{0} نتيجة", j)
        }), s.jsx("ul", {
          className: "space-y-3",
          children: d.key === "outstanding" ? y.slice(0, a).map(x => s.jsx("li", {
            children: s.jsxs(re, {
              to: `/invoices/${x.id}`,
              className: "flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-red-100 bg-bad-soft p-4 hover:shadow",
              children: [s.jsxs("div", {
                children: [s.jsxs("p", {
                  className: "font-extrabold",
                  children: [x.number, " · ", s.jsx("span", {
                    dir: "ltr",
                    children: x.vehicle.plate ?? "—"
                  })]
                }), s.jsx("p", {
                  className: "text-sm",
                  children: x.customer.name
                }), s.jsx("p", {
                  className: "mt-1 text-sm",
                  children: x.payment_status === "partial" ? l("مدفوعة جزئياً") : l("غير مدفوعة")
                })]
              }), s.jsxs("div", {
                className: "text-end",
                children: [s.jsxs("p", {
                  className: "font-extrabold text-bad",
                  children: [l("المتبقي"), " ", x.outstanding, " ", x.currency]
                }), s.jsx("p", {
                  className: "mt-1 text-sm font-bold text-brand",
                  children: l("فتح الفاتورة للتحصيل")
                })]
              })]
            })
          }, x.id)) : m.slice(0, a).map(({
            job: x,
            draftId: f,
            partial: g
          }) => s.jsxs("li", {
            className: "flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 p-4",
            children: [s.jsxs("div", {
              children: [s.jsx("p", {
                className: "text-xl font-extrabold",
                dir: "ltr",
                children: x.plate ?? "—"
              }), s.jsxs("p", {
                className: "font-semibold",
                children: [x.make, " ", x.model, " · ", x.customer]
              }), s.jsx("p", {
                className: "text-sm text-slate-500",
                children: Z("أمر شغل #{0}", x.job_no)
              }), d.key === "missing" && s.jsx("p", {
                className: "mt-1 text-sm text-wait",
                children: l(f ? "توجد مسودة تحتاج إصداراً" : g ? "توجد إصلاحات أو قطع غيار لم تصدر لها فاتورة" : "لا توجد فاتورة سارية")
              })]
            }), s.jsx(re, {
              className: "inline-flex min-h-[44px] items-center rounded-xl bg-brand px-4 font-bold text-white",
              to: f ? `/invoices/${f}` : `/jobs/${x.id}${d.key === "missing" ? "#job-invoices" : ""}`,
              children: d.key === "ready" ? l("فتح أمر الشغل للتسليم") : l(f ? "استكمال الفاتورة" : "فتح أمر الشغل للفوترة")
            })]
          }, x.id))
        }), j > a && s.jsx("div", {
          className: "mt-4",
          children: s.jsx(P, {
            kind: "secondary",
            onClick: () => o(a + 50),
            children: l("عرض المزيد")
          })
        })]
      }) : s.jsx(Ie, {
        icon: Qn,
        text: l("لا توجد تنبيهات مطابقة")
      })]
    })]
  });
}
const t2 = {
    manual: l("يدوية"),
    schedule: l("مجدولة"),
    pre_restore: l("أمان قبل استعادة"),
    imported: l("مستوردة")
  },
  vp = {
    verified: {
      label: l("تم التحقق ✔"),
      icon: Ke,
      cls: "bg-ok-soft text-ok"
    },
    failed: {
      label: l("فشلت"),
      icon: at,
      cls: "bg-bad-soft text-bad"
    },
    running: {
      label: l("جارية…"),
      icon: Le,
      cls: "bg-work-soft text-work"
    },
    unverified: {
      label: l("لم يتم التحقق"),
      icon: Js,
      cls: "bg-wait-soft text-wait"
    }
  },
  Ua = e => e == null ? "—" : e > 1e9 ? Z("{0} جيجا", (e / 1e9).toFixed(1)) : e > 1e6 ? Z("{0} ميجا", (e / 1e6).toFixed(1)) : Z("{0} كيلو", Math.max(1, Math.round(e / 1e3))),
  Ys = e => e ? new Date(e).toLocaleString($t) : "—";
function n2({
  s: e
}) {
  const t = vp[e] ?? vp.unverified,
    n = t.icon;
  return s.jsxs("span", {
    className: `inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold ${t.cls}`,
    children: [s.jsx(n, {
      size: 16
    }), t.label]
  });
}
function s2({
  items: e,
  onClose: t
}) {
  var x, f, g, b, k;
  const [n, r] = w.useState(null),
    [i, a] = w.useState(""),
    [o, c] = w.useState(null),
    [d, u] = w.useState({
      phrase: "",
      pw: ""
    }),
    [h, p] = w.useState(!1),
    m = V({
      mutationFn: () => M.post("/api/restore/preview", {
        id: n.id,
        passphrase: i || null
      }),
      onSuccess: c
    }),
    y = V({
      mutationFn: () => M.post("/api/restore", {
        id: n.id,
        passphrase: i || null,
        confirm: d.phrase,
        admin_password: d.pw
      }),
      onSuccess: () => p(!0)
    }),
    v = W({
      queryKey: ["restore-status"],
      enabled: h,
      refetchInterval: 1500,
      queryFn: () => M.get("/api/restore/status")
    }).data,
    N = v && ["done", "failed", "rolled_back"].includes(v.state);
  return s.jsxs(B, {
    title: l("استعادة نسخة احتياطية"),
    action: !h || N ? s.jsx(P, {
      kind: "secondary",
      onClick: t,
      children: l("إغلاق")
    }) : void 0,
    children: [!h && s.jsxs("div", {
      className: "space-y-4",
      children: [s.jsx("p", {
        className: "rounded-2xl bg-wait-soft p-4 text-lg font-bold text-wait",
        children: l("⚠️ الاستعادة تستبدل البيانات الحالية بالكامل. يتم عمل نسخة أمان أولاً، والنظام يتوقف مؤقتاً أثناء الاستعادة.")
      }), s.jsx("p", {
        className: "text-xl font-extrabold",
        children: l("١) اختار النسخة")
      }), s.jsx("ul", {
        className: "space-y-2",
        children: e.filter(_ => _.status !== "failed").map(_ => s.jsx("li", {
          children: s.jsxs("button", {
            onClick: () => {
              r(_), c(null);
            },
            "aria-pressed": (n == null ? void 0 : n.id) === _.id,
            className: `flex w-full flex-wrap items-center justify-between gap-2 rounded-2xl border-4 p-3 text-start ${(n == null ? void 0 : n.id) === _.id ? "border-brand bg-brand-soft" : "border-slate-200"}`,
            children: [s.jsx("span", {
              className: "font-bold",
              dir: "ltr",
              children: _.name
            }), s.jsxs("span", {
              children: [Ys(_.created_at), " · ", Ua(_.size_bytes), " ", _.encrypted && "🔒"]
            })]
          })
        }, _.id))
      }), n && s.jsxs(s.Fragment, {
        children: [n.encrypted && s.jsx(E, {
          label: l("كلمة سر التشفير"),
          children: s.jsx("input", {
            type: "password",
            value: i,
            onChange: _ => a(_.target.value),
            dir: "ltr"
          })
        }), s.jsx(P, {
          icon: rr,
          disabled: m.isPending,
          onClick: () => m.mutate(),
          children: l("٢) فحص النسخة")
        }), s.jsx($, {
          message: (x = m.error) == null ? void 0 : x.message
        })]
      }), o && s.jsxs("div", {
        className: "space-y-2",
        children: [s.jsx("ul", {
          className: "space-y-1",
          children: o.checks.map(_ => s.jsxs("li", {
            className: `flex items-center gap-2 font-semibold ${_.ok ? "text-ok" : "text-bad"}`,
            children: [_.ok ? s.jsx(Ke, {
              size: 20
            }) : s.jsx(at, {
              size: 20
            }), J(_.detail)]
          }, _.name))
        }), o.ok ? s.jsxs("div", {
          className: "space-y-3 rounded-2xl border-2 border-bad p-4",
          children: [s.jsxs("p", {
            className: "text-lg font-bold",
            children: [l("النسخة من"), " ", Ys(o.created_at), " ", l("· عملاء:"), " ", (f = o.row_counts) == null ? void 0 : f.customers, " ", l("· عربيات:"), " ", (g = o.row_counts) == null ? void 0 : g.vehicles, " ", l("· فواتير:"), " ", (b = o.row_counts) == null ? void 0 : b.invoices]
          }), s.jsx("p", {
            className: "text-xl font-extrabold",
            children: l("٣) تأكيد الاستعادة")
          }), s.jsxs("div", {
            className: "grid gap-3 sm:grid-cols-2",
            children: [s.jsx(E, {
              label: l("اكتب RESTORE للتأكيد"),
              children: s.jsx("input", {
                value: d.phrase,
                onChange: _ => u({
                  ...d,
                  phrase: _.target.value
                }),
                dir: "ltr"
              })
            }), s.jsx(E, {
              label: l("كلمة مرور المدير"),
              children: s.jsx("input", {
                type: "password",
                value: d.pw,
                onChange: _ => u({
                  ...d,
                  pw: _.target.value
                }),
                dir: "ltr",
                autoComplete: "current-password"
              })
            })]
          }), s.jsx($, {
            message: (k = y.error) == null ? void 0 : k.message
          }), s.jsx(P, {
            kind: "danger",
            icon: yu,
            disabled: d.phrase !== "RESTORE" || !d.pw || y.isPending,
            onClick: () => y.mutate(),
            children: l("ابدأ الاستعادة")
          })]
        }) : s.jsx("p", {
          className: "font-bold text-bad",
          children: l("النسخة لم تجتز الفحص، لا يمكن استعادتها.")
        })]
      })]
    }), h && s.jsxs("div", {
      className: "space-y-3",
      children: [s.jsx("ol", {
        className: "space-y-2",
        children: ((v == null ? void 0 : v.steps) ?? []).map(_ => s.jsxs("li", {
          className: "flex items-center gap-3 rounded-xl bg-slate-50 p-3 text-lg font-semibold",
          children: [_.status === "done" ? s.jsx(Ke, {
            className: "text-ok"
          }) : _.status === "failed" ? s.jsx(at, {
            className: "text-bad"
          }) : _.status === "running" ? s.jsx(Le, {
            className: "animate-pulse text-work"
          }) : s.jsx("span", {
            className: "inline-block w-6 text-center text-slate-400",
            children: "○"
          }), J(_.label), s.jsx("span", {
            className: "text-sm font-normal text-slate-500",
            children: J(_.detail)
          })]
        }, _.key))
      }), (v == null ? void 0 : v.state) === "done" && s.jsxs("div", {
        className: "rounded-2xl bg-ok-soft p-4 text-xl font-bold text-ok",
        children: [l("✔ تمت الاستعادة بنجاح. سجّل الدخول من جديد."), " ", v.old_database && s.jsxs("span", {
          className: "block text-base font-normal",
          dir: "ltr",
          children: ["previous: ", v.old_database]
        }), s.jsx("div", {
          className: "mt-3",
          children: s.jsx(P, {
            onClick: () => {
              window.location.href = "/login";
            },
            children: l("تسجيل الدخول")
          })
        })]
      }), v && ["failed", "rolled_back"].includes(v.state) && s.jsxs("div", {
        className: "rounded-2xl bg-bad-soft p-4 text-lg font-bold text-bad",
        children: [l("✖ فشلت الاستعادة"), v.state === "rolled_back" ? l(" وتم الرجوع للوضع السابق") : l(" ولم يتغير شيء"), ": ", J(v.error)]
      }), !N && s.jsx("p", {
        className: "text-slate-600",
        children: l("النظام تحت الصيانة. لا تغلق الجهاز.")
      })]
    })]
  });
}
function r2({
  s: e,
  onSaved: t
}) {
  var c;
  const [n, r] = w.useState(e),
    i = V({
      mutationFn: () => M.put("/api/backup-settings", {
        ...n,
        dir: n.dir || null
      }),
      onSuccess: t
    }),
    a = n.schedule,
    o = d => Number(d) || 0;
  return s.jsxs(B, {
    title: l("إعدادات النسخ التلقائي"),
    children: [s.jsxs("div", {
      className: "grid gap-4 sm:grid-cols-2",
      children: [s.jsx("div", {
        className: "sm:col-span-2",
        children: s.jsx(E, {
          label: l("مكان حفظ النسخ (اتركه فارغاً للمكان الافتراضي) — يُفضّل فلاشة أو قرص خارجي"),
          children: s.jsx("input", {
            value: n.dir ?? "",
            onChange: d => r({
              ...n,
              dir: d.target.value
            }),
            dir: "ltr",
            placeholder: "D:\\Backups"
          })
        })
      }), s.jsxs("label", {
        className: "flex min-h-[56px] items-center gap-3 rounded-xl bg-slate-50 px-4 text-lg font-semibold",
        children: [s.jsx("input", {
          type: "checkbox",
          className: "!h-7 !w-7",
          checked: a.enabled,
          onChange: d => r({
            ...n,
            schedule: {
              ...a,
              enabled: d.target.checked
            }
          })
        }), l("تشغيل النسخ التلقائي")]
      }), s.jsx(E, {
        label: l("التكرار"),
        children: s.jsxs("select", {
          value: a.frequency,
          onChange: d => r({
            ...n,
            schedule: {
              ...a,
              frequency: d.target.value
            }
          }),
          children: [s.jsx("option", {
            value: "daily",
            children: l("يومياً")
          }), s.jsx("option", {
            value: "weekly",
            children: l("أسبوعياً")
          }), s.jsx("option", {
            value: "monthly",
            children: l("شهرياً")
          })]
        })
      }), s.jsx(E, {
        label: l("الوقت"),
        children: s.jsx("input", {
          type: "time",
          value: a.time,
          onChange: d => r({
            ...n,
            schedule: {
              ...a,
              time: d.target.value
            }
          }),
          dir: "ltr"
        })
      }), a.frequency === "weekly" && s.jsx(E, {
        label: l("اليوم"),
        children: s.jsx("select", {
          value: a.weekday,
          onChange: d => r({
            ...n,
            schedule: {
              ...a,
              weekday: Number(d.target.value)
            }
          }),
          children: [l("الإثنين"), l("الثلاثاء"), l("الأربعاء"), l("الخميس"), l("الجمعة"), l("السبت"), l("الأحد")].map((d, u) => s.jsx("option", {
            value: u,
            children: d
          }, u))
        })
      }), a.frequency === "monthly" && s.jsx(E, {
        label: l("يوم الشهر"),
        children: s.jsx("input", {
          type: "number",
          min: 1,
          max: 28,
          value: a.day,
          onChange: d => r({
            ...n,
            schedule: {
              ...a,
              day: o(d.target.value)
            }
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("نحتفظ بآخر (يومي)"),
        children: s.jsx("input", {
          type: "number",
          min: 0,
          value: n.retention.daily,
          onChange: d => r({
            ...n,
            retention: {
              ...n.retention,
              daily: o(d.target.value)
            }
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("أسبوعي"),
        children: s.jsx("input", {
          type: "number",
          min: 0,
          value: n.retention.weekly,
          onChange: d => r({
            ...n,
            retention: {
              ...n.retention,
              weekly: o(d.target.value)
            }
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("شهري"),
        children: s.jsx("input", {
          type: "number",
          min: 0,
          value: n.retention.monthly,
          onChange: d => r({
            ...n,
            retention: {
              ...n.retention,
              monthly: o(d.target.value)
            }
          }),
          dir: "ltr"
        })
      })]
    }), s.jsx("p", {
      className: "mt-3 text-slate-600",
      children: l("النظام لا يحذف أبداً آخر نسخة صالحة. يُنصح بنسخة واحدة على الأقل على جهاز مختلف (فلاشة أو قرص خارجي).")
    }), s.jsxs("div", {
      className: "mt-3 space-y-2",
      children: [s.jsx($, {
        message: (c = i.error) == null ? void 0 : c.message
      }), s.jsx(P, {
        icon: ra,
        disabled: i.isPending,
        onClick: () => i.mutate(),
        children: l("حفظ الإعدادات")
      })]
    })]
  });
}
// Recovered route component for /backup; original filename/name unknown.
function i2() {
  var N, x, f, g, b;
  const e = de(),
    [t, n] = w.useState(""),
    [r, i] = w.useState(""),
    [a, o] = w.useState(""),
    c = W({
      queryKey: ["backups"],
      queryFn: () => M.get("/api/backups"),
      refetchInterval: k => {
        var _;
        return (_ = k.state.data) != null && _.items.some(S => S.status === "running") ? 2e3 : 15e3;
      }
    }),
    d = () => e.invalidateQueries({
      queryKey: ["backups"]
    }),
    u = V({
      mutationFn: () => M.post("/api/backups", {
        passphrase: r || null
      }),
      onSuccess: () => {
        i(""), d();
      }
    }),
    h = V({
      mutationFn: k => M.post(`/api/backups/${k.id}/verify`, {
        passphrase: k.passphrase || null,
        deep: !0
      }),
      onSuccess: d
    }),
    p = V({
      mutationFn: () => M.post("/api/backups/recovery-secret"),
      onSuccess: k => o(k.secret)
    }),
    m = V({
      mutationFn: () => M.post("/api/backups/rescan"),
      onSuccess: d
    });
  if (c.isLoading) return s.jsx(ie, {});
  if (c.error || !c.data) return s.jsx($, {
    message: (N = c.error) == null ? void 0 : N.message
  });
  const y = c.data,
    j = y.items.some(k => k.status === "running"),
    v = y.free_bytes != null && y.free_bytes < 2e9;
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(bl, {
        size: 36
      }), l("النسخ الاحتياطي")]
    }), s.jsxs("div", {
      className: "grid gap-4 sm:grid-cols-2 lg:grid-cols-4",
      children: [s.jsxs("div", {
        className: "rounded-3xl bg-ok-soft p-4",
        children: [s.jsx("p", {
          className: "font-bold text-ok",
          children: l("آخر نسخة ناجحة")
        }), s.jsx("p", {
          className: "text-xl font-extrabold",
          children: y.last_success ? Ys(y.last_success.created_at) : l("لا يوجد!")
        }), y.last_success && s.jsxs("p", {
          className: "text-sm",
          children: [Ua(y.last_success.size_bytes), " ", l("· تم التحقق ✔")]
        })]
      }), s.jsxs("div", {
        className: `rounded-3xl p-4 ${y.last_failure ? "bg-bad-soft" : "bg-slate-100"}`,
        children: [s.jsx("p", {
          className: "font-bold",
          children: l("آخر محاولة فاشلة")
        }), s.jsx("p", {
          className: "text-xl font-extrabold",
          children: y.last_failure ? Ys(y.last_failure.created_at) : l("لا يوجد")
        })]
      }), s.jsxs("div", {
        className: "rounded-3xl bg-work-soft p-4",
        children: [s.jsx("p", {
          className: "font-bold text-work",
          children: l("الموعد القادم")
        }), s.jsx("p", {
          className: "text-xl font-extrabold",
          children: y.next_scheduled ? Ys(y.next_scheduled) : l("التلقائي موقوف")
        })]
      }), s.jsxs("div", {
        className: `rounded-3xl p-4 ${v ? "bg-wait-soft" : "bg-slate-100"}`,
        children: [s.jsxs("p", {
          className: "flex items-center gap-1 font-bold",
          children: [s.jsx(_b, {
            size: 18
          }), l("المساحة الفارغة")]
        }), s.jsx("p", {
          className: "text-xl font-extrabold",
          children: Ua(y.free_bytes)
        }), s.jsx("p", {
          className: "break-all text-xs",
          dir: "ltr",
          children: y.directory
        })]
      })]
    }), !y.last_success && s.jsx("p", {
      className: "rounded-2xl bg-bad-soft p-4 text-xl font-bold text-bad",
      children: l("⚠️ لا توجد نسخة احتياطية صالحة! اعمل نسخة الآن.")
    }), s.jsxs(B, {
      children: [s.jsxs("div", {
        className: "grid gap-3 sm:grid-cols-2 lg:grid-cols-4",
        children: [s.jsx(P, {
          icon: bl,
          disabled: u.isPending || j,
          onClick: () => u.mutate(),
          children: l(j ? "جاري النسخ…" : "عمل نسخة الآن")
        }), s.jsx(P, {
          kind: "secondary",
          icon: ra,
          onClick: () => n(t === "settings" ? "" : "settings"),
          children: l("النسخ التلقائي")
        }), s.jsx(P, {
          kind: "secondary",
          icon: Mb,
          onClick: () => n(t === "history" ? "" : "history"),
          children: l("سجل النسخ")
        }), s.jsx(P, {
          kind: "danger",
          icon: yu,
          onClick: () => n("restore"),
          children: l("استعادة نسخة")
        })]
      }), s.jsxs("div", {
        className: "mt-4 grid gap-3 sm:grid-cols-2",
        children: [s.jsx(E, {
          label: l("تشفير هذه النسخة (اختياري): كلمة سر ٨ أحرف على الأقل"),
          children: s.jsx("input", {
            type: "password",
            value: r,
            onChange: k => i(k.target.value),
            dir: "ltr",
            autoComplete: "new-password"
          })
        }), s.jsx("div", {
          className: "flex flex-col justify-end gap-2",
          children: s.jsx(P, {
            kind: "secondary",
            icon: gu,
            onClick: () => p.mutate(),
            children: l("توليد كلمة سر قوية")
          })
        })]
      }), a && s.jsxs("p", {
        className: "mt-3 rounded-2xl bg-wait-soft p-4 text-lg font-bold",
        dir: "ltr",
        children: [a, s.jsx("span", {
          className: "block text-base font-normal",
          dir: "rtl",
          children: l("احفظها الآن في مكان آمن خارج هذا الجهاز — لن تظهر مرة أخرى، ولا يمكن استعادة نسخة مشفرة بدونها.")
        })]
      }), s.jsx($, {
        message: ((x = u.error) == null ? void 0 : x.message) ?? ((f = p.error) == null ? void 0 : f.message)
      })]
    }), t === "settings" && s.jsx(r2, {
      s: y.settings,
      onSaved: () => {
        d(), n("");
      }
    }), t === "restore" && s.jsx(s2, {
      items: y.items,
      onClose: () => {
        n(""), d();
      }
    }), (t === "history" || t === "") && s.jsxs(B, {
      title: l("سجل النسخ"),
      action: s.jsx(P, {
        kind: "secondary",
        onClick: () => m.mutate(),
        children: l("البحث عن نسخ في المجلد")
      }),
      children: [!y.items.length && s.jsx("p", {
        className: "text-slate-500",
        children: l("لا توجد نسخ بعد")
      }), s.jsx("ul", {
        className: "space-y-3",
        children: y.items.map(k => s.jsxs("li", {
          className: "space-y-2 rounded-2xl bg-slate-50 p-4",
          children: [s.jsxs("div", {
            className: "flex flex-wrap items-center justify-between gap-2",
            children: [s.jsx("span", {
              className: "font-bold",
              dir: "ltr",
              children: k.name
            }), s.jsx(n2, {
              s: k.status
            })]
          }), s.jsxs("p", {
            className: "text-slate-600",
            children: [t2[k.trigger] ?? k.trigger, " · ", Ys(k.created_at), " · ", Ua(k.size_bytes), " ", k.encrypted && l("· 🔒 مشفرة")]
          }), k.error && s.jsx("p", {
            className: "font-semibold text-bad",
            children: J(k.error)
          }), k.checks && s.jsx("p", {
            className: "text-sm text-slate-600",
            children: k.checks.map(_ => `${_.ok ? "✔" : "✖"} ${_.name}`).join("  ")
          }), k.status !== "running" && s.jsxs("div", {
            className: "flex flex-wrap gap-2",
            children: [s.jsx(P, {
              kind: "secondary",
              icon: rr,
              disabled: h.isPending,
              onClick: () => {
                const _ = k.encrypted ? prompt(l("كلمة سر التشفير؟")) : void 0;
                k.encrypted && !_ || h.mutate({
                  id: k.id,
                  passphrase: _ ?? void 0
                });
              },
              children: l("فحص واستعادة تجريبية")
            }), s.jsxs("a", {
              href: `/api/backups/${k.id}/download`,
              className: "inline-flex min-h-[56px] items-center gap-2 rounded-2xl border-2 border-slate-300 bg-white px-6 text-xl font-bold",
              children: [s.jsx(xu, {
                size: 22
              }), l("تحميل")]
            })]
          })]
        }, k.id))
      }), s.jsx($, {
        message: ((g = h.error) == null ? void 0 : g.message) ?? ((b = m.error) == null ? void 0 : b.message)
      }), s.jsxs("span", {
        className: "hidden",
        children: [s.jsx(Xe, {
          status: "done"
        }), $e(void 0)]
      })]
    })]
  });
}
// Recovered route component for /board; original filename/name unknown.
function a2() {
  var u;
  const [e, t] = w.useState(""),
    [n, r] = sa(),
    i = n.get("group") ?? "",
    a = h => !i || (i === "waiting" ? h.startsWith("waiting") : h === i),
    o = W({
      queryKey: ["board"],
      queryFn: () => M.get("/api/board"),
      refetchInterval: 3e4
    });
  if (o.isLoading) return s.jsx(ie, {});
  if (o.error) return s.jsx($, {
    message: o.error.message
  });
  const c = (o.data ?? []).filter(h => (!e || h.status === e) && a(h.status)),
    d = (o.data ?? []).reduce((h, p) => ({
      ...h,
      [p.status]: (h[p.status] ?? 0) + 1
    }), {});
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(Vl, {
        size: 36
      }), l("لوحة الورشة ("), ((u = o.data) == null ? void 0 : u.length) ?? 0, ")"]
    }), s.jsxs("div", {
      className: "flex flex-wrap gap-2",
      children: [i && s.jsxs("button", {
        onClick: () => r({}),
        "aria-label": l("إلغاء الفلتر"),
        className: "inline-flex min-h-[48px] items-center gap-2 rounded-xl bg-ok px-4 font-bold text-white",
        children: [i === "waiting" ? l("في الانتظار") : Ts.ready.label, s.jsx(ia, {
          size: 18
        })]
      }), s.jsx("button", {
        onClick: () => t(""),
        className: `min-h-[48px] rounded-xl px-4 font-bold ${e ? "bg-white" : "bg-brand text-white"}`,
        children: l("الكل")
      }), my.filter(h => d[h]).map(h => s.jsxs("button", {
        onClick: () => t(h),
        className: `min-h-[48px] rounded-xl px-4 font-bold ${e === h ? "bg-brand text-white" : "bg-white"}`,
        children: [Ts[h].label, " (", d[h], ")"]
      }, h))]
    }), c.length ? s.jsx("div", {
      className: "grid gap-4 sm:grid-cols-2 lg:grid-cols-3",
      children: c.map(h => s.jsxs(re, {
        to: `/jobs/${h.id}`,
        className: `space-y-2 rounded-3xl border-4 bg-white p-5 shadow transition hover:shadow-lg ${h.delayed ? "border-bad" : "border-transparent"}`,
        children: [s.jsxs("div", {
          className: "flex items-start justify-between gap-2",
          children: [s.jsx("p", {
            className: "text-3xl font-extrabold",
            dir: "ltr",
            children: h.plate ?? "—"
          }), s.jsxs("span", {
            className: "text-slate-500",
            children: ["#", h.job_no]
          })]
        }), s.jsxs("p", {
          className: "text-xl font-bold",
          children: [h.make, " ", h.model]
        }), s.jsx(Pr, {
          status: h.status
        }), s.jsxs("p", {
          className: "flex items-center gap-2 text-slate-700",
          children: [s.jsx(Ib, {
            size: 18
          }), h.technicians.join(l("، ")) || l("لم يُحدد فني")]
        }), s.jsxs("p", {
          className: "flex items-center gap-2 text-slate-700",
          children: [s.jsx(mb, {
            size: 18
          }), l("في الورشة"), " ", h.days_in_workshop, " ", l("يوم")]
        }), h.expected_completion_at && s.jsxs("p", {
          className: `flex items-center gap-2 font-semibold ${h.delayed ? "text-bad" : "text-slate-700"}`,
          children: [s.jsx(hb, {
            size: 18
          }), l("التسليم المتوقع"), " ", $e(h.expected_completion_at), h.delayed && l(" — متأخر")]
        })]
      }, h.id))
    }) : s.jsx(Ie, {
      icon: ns,
      text: l("مفيش عربيات في الورشة دلوقتي")
    })]
  });
}
function l2({
  c: e,
  onDone: t
}) {
  var o;
  const n = de(),
    [r, i] = w.useState({
      full_name: e.full_name,
      mobile: e.mobile,
      email: e.email ?? "",
      city: e.city ?? "",
      is_active: e.is_active
    }),
    a = V({
      mutationFn: () => M.patch(`/api/customers/${e.id}`, {
        ...r,
        email: r.email || null,
        city: r.city || null
      }),
      onSuccess: () => {
        n.invalidateQueries({
          queryKey: ["customers"]
        }), t();
      }
    });
  return s.jsxs("div", {
    className: "mt-3 w-full space-y-3 rounded-2xl bg-slate-50 p-4",
    children: [s.jsxs("div", {
      className: "grid gap-3 sm:grid-cols-2",
      children: [s.jsx(E, {
        label: l("الاسم"),
        children: s.jsx("input", {
          value: r.full_name,
          onChange: c => i({
            ...r,
            full_name: c.target.value
          })
        })
      }), s.jsx(E, {
        label: l("الموبايل"),
        children: s.jsx("input", {
          value: r.mobile,
          onChange: c => i({
            ...r,
            mobile: c.target.value
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("البريد"),
        children: s.jsx("input", {
          value: r.email,
          onChange: c => i({
            ...r,
            email: c.target.value
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("المدينة"),
        children: s.jsx("input", {
          value: r.city,
          onChange: c => i({
            ...r,
            city: c.target.value
          })
        })
      })]
    }), s.jsxs("label", {
      className: "flex min-h-[48px] items-center gap-3 font-bold",
      children: [s.jsx("input", {
        type: "checkbox",
        className: "!h-6 !w-6",
        checked: r.is_active,
        onChange: c => i({
          ...r,
          is_active: c.target.checked
        })
      }), l("عميل نشط (إلغاء التفعيل لا يحذف أي سجل)")]
    }), s.jsx($, {
      message: (o = a.error) == null ? void 0 : o.message
    }), s.jsxs("div", {
      className: "flex gap-3",
      children: [s.jsx(P, {
        icon: et,
        disabled: a.isPending,
        onClick: () => a.mutate(),
        children: l("حفظ")
      }), s.jsx(P, {
        kind: "secondary",
        onClick: t,
        children: l("إلغاء")
      })]
    })]
  });
}
const jp = {
  full_name: "",
  mobile: "",
  email: "",
  city: ""
};
function o2({
  onDone: e
}) {
  var h;
  const t = de(),
    [n, r] = w.useState(jp),
    [i, a] = w.useState([]),
    o = V({
      mutationFn: p => M.post(`/api/customers${p ? "?force=true" : ""}`, {
        ...n,
        email: n.email || null,
        city: n.city || null
      }),
      onSuccess: () => {
        t.invalidateQueries({
          queryKey: ["customers"]
        }), r(jp), a([]), e();
      },
      onError: p => {
        p instanceof Sr && p.code === "possible_duplicate" && a(p.data.duplicates);
      }
    }),
    c = p => m => r({
      ...n,
      [p]: m.target.value
    }),
    d = p => {
      p.preventDefault(), a([]), o.mutate(!1);
    },
    u = o.error instanceof Sr && o.error.code === "possible_duplicate";
  return s.jsx(B, {
    title: l("عميل جديد"),
    children: s.jsxs("form", {
      onSubmit: d,
      className: "grid gap-4 sm:grid-cols-2",
      children: [s.jsx(E, {
        label: l("الاسم"),
        children: s.jsx("input", {
          value: n.full_name,
          onChange: c("full_name"),
          required: !0,
          minLength: 2
        })
      }), s.jsx(E, {
        label: l("رقم الموبايل"),
        children: s.jsx("input", {
          value: n.mobile,
          onChange: c("mobile"),
          required: !0,
          minLength: 5,
          dir: "ltr",
          inputMode: "tel"
        })
      }), s.jsx(E, {
        label: l("البريد الإلكتروني (اختياري)"),
        children: s.jsx("input", {
          value: n.email,
          onChange: c("email"),
          type: "email",
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("المدينة (اختياري)"),
        children: s.jsx("input", {
          value: n.city,
          onChange: c("city")
        })
      }), s.jsxs("div", {
        className: "sm:col-span-2 space-y-3",
        children: [!u && s.jsx($, {
          message: (h = o.error) == null ? void 0 : h.message
        }), u && s.jsxs("div", {
          className: "rounded-2xl bg-wait-soft p-4 text-wait",
          children: [s.jsx("p", {
            className: "mb-2 text-lg font-bold",
            children: l("⚠️ فيه عميل بنفس الاسم أو الموبايل:")
          }), s.jsx("ul", {
            className: "mb-3 space-y-1",
            children: i.map(p => s.jsxs("li", {
              className: "font-semibold",
              children: [p.full_name, " — ", s.jsx("span", {
                dir: "ltr",
                children: p.mobile
              })]
            }, p.id))
          }), s.jsx(P, {
            kind: "secondary",
            onClick: () => o.mutate(!0),
            children: l("ده عميل جديد فعلاً، احفظ")
          })]
        }), s.jsx(P, {
          type: "submit",
          icon: et,
          disabled: o.isPending,
          children: l("حفظ")
        })]
      })]
    })
  });
}
// Recovered route component for /customers; original filename/name unknown.
function c2() {
  var u;
  const {
      can: e
    } = ce(),
    [t, n] = sa(),
    [r, i] = w.useState(""),
    [a, o] = w.useState(null),
    c = t.get("new") === "1" && e("customers.write"),
    d = W({
      queryKey: ["customers", r],
      queryFn: () => M.get(`/api/customers${Re({
        q: r
      })}`)
    });
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("div", {
      className: "flex flex-wrap items-center justify-between gap-3",
      children: [s.jsxs("h1", {
        className: "flex items-center gap-2 text-3xl font-extrabold",
        children: [s.jsx(Ms, {
          size: 36
        }), l("العملاء")]
      }), e("customers.write") && !c && s.jsx(P, {
        icon: vu,
        onClick: () => n({
          new: "1"
        }),
        children: l("عميل جديد")
      })]
    }), c && s.jsx(o2, {
      onDone: () => n({})
    }), s.jsxs(B, {
      children: [s.jsx("input", {
        value: r,
        onChange: h => i(h.target.value),
        placeholder: l("ابحث بالاسم أو الموبايل"),
        className: "mb-4",
        "aria-label": l("بحث في العملاء")
      }), d.isLoading ? s.jsx(ie, {}) : d.error ? s.jsx($, {
        message: d.error.message
      }) : (u = d.data) != null && u.items.length ? s.jsx("ul", {
        className: "divide-y",
        children: d.data.items.map(h => s.jsxs("li", {
          className: "flex flex-wrap items-center justify-between gap-3 py-3",
          children: [s.jsxs("div", {
            children: [s.jsxs("p", {
              className: "text-xl font-bold",
              children: [h.full_name, " ", s.jsxs("span", {
                className: "text-sm font-semibold text-slate-500",
                children: ["#", h.customer_no]
              })]
            }), s.jsxs("p", {
              className: "flex items-center gap-1 text-slate-600",
              dir: "ltr",
              children: [s.jsx(Fg, {
                size: 16
              }), h.mobile]
            })]
          }), s.jsxs("div", {
            className: "flex gap-2",
            children: [e("customers.write") && s.jsx(P, {
              kind: "secondary",
              onClick: () => o(a === h.id ? null : h.id),
              children: l("تعديل")
            }), s.jsxs(re, {
              to: `/vehicles?customer=${h.id}`,
              className: "flex min-h-[48px] items-center gap-2 rounded-xl bg-brand-soft px-4 font-bold text-brand",
              children: [s.jsx(un, {
                size: 20
              }), l("عربياته")]
            })]
          }), a === h.id && s.jsx(l2, {
            c: h,
            onDone: () => o(null)
          })]
        }, h.id))
      }) : s.jsx(Ie, {
        icon: Ms,
        text: l("مفيش عملاء بعد")
      })]
    })]
  });
}
function zs() {
  const {
    user: e
  } = ce();
  return W({
    queryKey: ["settings"],
    enabled: !!e,
    staleTime: 6e4,
    queryFn: () => M.get("/api/settings")
  });
}
function d2() {
  var t;
  const e = zs();
  return w.useEffect(() => {
    var n;
    document.documentElement.dataset.theme = ((n = e.data) == null ? void 0 : n.general.theme) ?? "light";
  }, [(t = e.data) == null ? void 0 : t.general.theme]), w.useEffect(() => {
    e.data && py(e.data.general.language);
  }, [e.data]), null;
}
function qr() {
  var i, a;
  const e = zs(),
    t = W({
      queryKey: ["logo"],
      queryFn: () => M.get("/api/attachments?owner_type=workshop&owner_id=logo")
    }),
    n = (i = e.data) == null ? void 0 : i.workshop;
  if (!n) return null;
  const r = (a = t.data) != null && a.length ? t.data[t.data.length - 1].url : null;
  return s.jsxs("div", {
    className: "hidden items-center gap-4 border-b-2 pb-3 print:flex",
    children: [r && s.jsx("img", {
      src: r,
      alt: "",
      className: "h-16 w-16 object-contain"
    }), s.jsxs("div", {
      children: [s.jsx("p", {
        className: "text-2xl font-extrabold",
        children: J(n.name)
      }), n.name_en && s.jsx("p", {
        dir: "ltr",
        className: "text-sm",
        children: n.name_en
      }), s.jsxs("p", {
        className: "text-sm",
        children: [[n.address, n.phone, n.email].filter(Boolean).join(" · "), n.tax_number && Z(" · الرقم الضريبي {0}", n.tax_number)]
      })]
    })]
  });
}
// Recovered route component for /jobs/:id/delivery-report; original filename/name unknown.
function u2() {
  var i;
  const {
      id: e = ""
    } = Ds(),
    t = W({
      queryKey: ["delivery-report", e],
      queryFn: () => M.get(`/api/jobs/${e}/delivery-report`)
    });
  if (t.isLoading) return s.jsx(ie, {});
  if (t.error || !t.data) return s.jsx($, {
    message: (i = t.error) == null ? void 0 : i.message
  });
  const n = t.data,
    r = n.invoices ?? (n.invoice ? [n.invoice] : []);
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("div", {
      className: "no-print flex gap-3",
      children: [s.jsx(P, {
        icon: fn,
        onClick: () => window.print(),
        children: l("طباعة تقرير التسليم")
      }), s.jsx(re, {
        to: `/jobs/${e}`,
        className: "inline-flex min-h-[56px] items-center rounded-2xl border-2 border-slate-300 bg-white px-6 text-xl font-bold",
        children: l("أمر الصيانة")
      })]
    }), s.jsxs("article", {
      className: "space-y-4 rounded-3xl bg-white p-8 shadow print:shadow-none",
      children: [s.jsx(qr, {}), s.jsxs("h1", {
        className: "border-b-2 pb-3 text-3xl font-extrabold",
        children: [l("تقرير تسليم عربية — أمر #"), n.job_no]
      }), s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("العميل:")
        }), " ", n.customer.name, " — ", s.jsx("span", {
          dir: "ltr",
          children: n.customer.mobile
        })]
      }), s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("العربية:")
        }), " ", n.vehicle.make, " ", n.vehicle.model, " — ", s.jsx("span", {
          dir: "ltr",
          children: n.vehicle.plate
        })]
      }), s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("الاستلام:")
        }), " ", $e(n.arrival_at), " (", Gn(n.arrival_mileage), ") · ", s.jsx("b", {
          children: l("التسليم:")
        }), " ", new Date(n.delivered_at).toLocaleString($t), " (", Gn(n.final_mileage), ")"]
      }), s.jsxs("div", {
        children: [s.jsx("b", {
          children: l("الأعمال:")
        }), s.jsx("ul", {
          className: "list-inside list-disc",
          children: n.operations.map((a, o) => s.jsx("li", {
            children: J(a.description)
          }, o))
        })]
      }), n.installed_parts.length > 0 && s.jsxs("div", {
        children: [s.jsx("b", {
          children: l("القطع المركّبة:")
        }), s.jsx("ul", {
          className: "list-inside list-disc",
          children: n.installed_parts.map((a, o) => s.jsxs("li", {
            children: [a.name, " ", a.brand, " ", s.jsx("span", {
              dir: "ltr",
              children: a.part_number
            })]
          }, o))
        })]
      }), n.quality_check && s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("فحص الجودة:")
        }), " ", n.quality_check.result === "passed" ? l("اجتاز ✔") : l("لم يجتز"), n.quality_check.notes && ` — ${n.quality_check.notes}`]
      }), r.length > 0 && s.jsxs("div", {
        children: [s.jsx("b", {
          children: l("الفواتير وقت التسليم")
        }), s.jsx("ul", {
          className: "mt-2 divide-y divide-slate-200",
          children: r.map(a => {
            var o;
            return s.jsxs("li", {
              className: "flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-2",
              children: [s.jsx("b", {
                dir: "ltr",
                children: a.number
              }), s.jsxs("span", {
                dir: "ltr",
                children: [a.total, " ", a.currency]
              }), s.jsx("span", {
                children: ((o = Bi[a.payment_status]) == null ? void 0 : o.label) ?? a.payment_status
              }), Number(a.outstanding) > 0 && s.jsxs("span", {
                children: [l("المتبقي"), " ", s.jsxs("b", {
                  dir: "ltr",
                  children: [a.outstanding, " ", a.currency]
                })]
              })]
            }, a.number);
          })
        })]
      }), n.warranties.length > 0 && s.jsxs("div", {
        children: [s.jsx("b", {
          children: l("الضمان:")
        }), s.jsx("ul", {
          className: "list-inside list-disc",
          children: n.warranties.map((a, o) => s.jsxs("li", {
            children: [J(a.description), " ", l("حتى"), " ", $e(a.end_date), a.mileage_limit && Z(" (حد {0} كم)", a.mileage_limit)]
          }, o))
        })]
      }), n.final_condition && s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("حالة العربية عند التسليم:")
        }), " ", n.final_condition]
      }), n.override_reason && s.jsxs("p", {
        className: "font-bold text-bad",
        children: [l("تسليم باستثناء إداري:"), " ", n.override_reason]
      }), s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("استلمها:")
        }), " ", n.acknowledged_by]
      }), s.jsxs("div", {
        className: "grid grid-cols-2 gap-8 pt-10 text-center",
        children: [s.jsx("p", {
          className: "border-t-2 pt-2",
          children: l("توقيع المستلم")
        }), s.jsx("p", {
          className: "border-t-2 pt-2",
          children: l("توقيع موظف الورشة")
        })]
      })]
    })]
  });
}
function Ns() {
  const e = new Date();
  return `${e.getFullYear()}-${String(e.getMonth() + 1).padStart(2, "0")}-${String(e.getDate()).padStart(2, "0")}`;
}
// Recovered route component for /expenses; original filename/name unknown.
function h2() {
  var N, x, f, g, b, k, _;
  const {
      can: e
    } = ce(),
    t = de(),
    [n, r] = w.useState({
      category_id: "",
      amount: "",
      expense_date: Ns(),
      description: "",
      payee: ""
    }),
    [i, a] = w.useState({
      date_from: Ns().slice(0, 8) + "01",
      date_to: Ns()
    }),
    [o, c] = w.useState(0),
    d = 50,
    u = W({
      queryKey: ["exp-cats"],
      queryFn: () => M.get("/api/expense-categories")
    }),
    h = W({
      queryKey: ["expenses", i, o],
      queryFn: () => M.get(`/api/expenses${Re({
        ...i,
        offset: o,
        limit: d
      })}`)
    }),
    p = () => (c(0), t.invalidateQueries({
      queryKey: ["expenses"]
    })),
    m = V({
      mutationFn: () => M.post("/api/expenses", {
        ...n,
        category_id: Number(n.category_id),
        payee: n.payee || null
      }),
      onSuccess: () => {
        r({
          ...n,
          amount: "",
          description: "",
          payee: ""
        }), p();
      }
    }),
    y = V({
      mutationFn: S => M.post(`/api/expenses/${S.id}/void`, {
        reason: S.reason
      }),
      onSuccess: p
    }),
    j = S => {
      S.preventDefault(), m.mutate();
    },
    v = S => {
      const T = prompt(l("سبب إلغاء المصروف؟"));
      T && T.trim().length >= 3 && y.mutate({
        id: S,
        reason: T.trim()
      });
    };
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(yl, {
        size: 36
      }), l("مصروفات الورشة")]
    }), e("expenses.write") && s.jsx(B, {
      title: l("مصروف جديد"),
      children: s.jsxs("form", {
        onSubmit: j,
        className: "grid gap-4 sm:grid-cols-2 lg:grid-cols-3",
        children: [s.jsx(E, {
          label: l("النوع"),
          children: s.jsxs("select", {
            value: n.category_id,
            onChange: S => r({
              ...n,
              category_id: S.target.value
            }),
            required: !0,
            children: [s.jsx("option", {
              value: "",
              children: l("اختار")
            }), (N = u.data) == null ? void 0 : N.map(S => s.jsx("option", {
              value: S.id,
              children: J(S.name)
            }, S.id))]
          })
        }), s.jsx(E, {
          label: l("المبلغ"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            value: n.amount,
            onChange: S => r({
              ...n,
              amount: S.target.value
            }),
            dir: "ltr",
            required: !0
          })
        }), s.jsx(E, {
          label: l("التاريخ"),
          children: s.jsx("input", {
            type: "date",
            value: n.expense_date,
            onChange: S => r({
              ...n,
              expense_date: S.target.value
            }),
            dir: "ltr",
            required: !0
          })
        }), s.jsx("div", {
          className: "sm:col-span-2",
          children: s.jsx(E, {
            label: l("البيان"),
            children: s.jsx("input", {
              value: n.description,
              onChange: S => r({
                ...n,
                description: S.target.value
              }),
              required: !0,
              minLength: 2
            })
          })
        }), s.jsx(E, {
          label: l("المدفوع له (اختياري)"),
          children: s.jsx("input", {
            value: n.payee,
            onChange: S => r({
              ...n,
              payee: S.target.value
            })
          })
        }), s.jsxs("div", {
          className: "sm:col-span-2 lg:col-span-3 space-y-2",
          children: [s.jsx($, {
            message: (x = m.error) == null ? void 0 : x.message
          }), s.jsx(P, {
            type: "submit",
            icon: et,
            disabled: m.isPending,
            children: l("حفظ المصروف")
          })]
        })]
      })
    }), s.jsxs(B, {
      title: Z("المصروفات — الإجمالي {0}", ((f = h.data) == null ? void 0 : f.total) ?? "0.00"),
      children: [s.jsxs("div", {
        className: "mb-4 grid gap-3 sm:grid-cols-2",
        children: [s.jsx(E, {
          label: l("من"),
          children: s.jsx("input", {
            type: "date",
            value: i.date_from,
            onChange: S => {
              a({
                ...i,
                date_from: S.target.value
              }), c(0);
            },
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("إلى"),
          children: s.jsx("input", {
            type: "date",
            value: i.date_to,
            onChange: S => {
              a({
                ...i,
                date_to: S.target.value
              }), c(0);
            },
            dir: "ltr"
          })
        })]
      }), h.isLoading ? s.jsx(ie, {}) : h.error ? s.jsx($, {
        message: h.error.message
      }) : (g = h.data) != null && g.items.length ? s.jsx("ul", {
        className: "divide-y",
        children: h.data.items.map(S => s.jsxs("li", {
          className: "flex flex-wrap items-center justify-between gap-3 py-3",
          children: [s.jsxs("div", {
            children: [s.jsx("p", {
              className: "text-lg font-bold",
              children: S.description
            }), s.jsxs("p", {
              className: "text-slate-600",
              children: [J(S.category), " · ", $e(S.expense_date), S.payee && ` · ${S.payee}`]
            })]
          }), s.jsxs("div", {
            className: "flex items-center gap-3",
            children: [s.jsx("span", {
              className: "text-xl font-extrabold",
              children: S.amount
            }), e("expenses.write") && s.jsx(P, {
              kind: "secondary",
              onClick: () => v(S.id),
              children: l("إلغاء")
            })]
          })]
        }, S.id))
      }) : s.jsx(Ie, {
        icon: yl,
        text: l("مفيش مصروفات في الفترة دي")
      }), s.jsx($, {
        message: (b = y.error) == null ? void 0 : b.message
      }), s.jsxs("div", {
        className: "mt-4 flex items-center justify-between gap-3",
        children: [s.jsx(P, {
          kind: "secondary",
          disabled: o === 0 || h.isFetching,
          onClick: () => c(Math.max(0, o - d)),
          children: l("السابق")
        }), s.jsxs("span", {
          children: [Math.floor(o / d) + 1, " / ", Math.max(1, Math.ceil((((k = h.data) == null ? void 0 : k.total_count) ?? 0) / d))]
        }), s.jsx(P, {
          kind: "secondary",
          disabled: h.isFetching || o + d >= (((_ = h.data) == null ? void 0 : _.total_count) ?? 0),
          onClick: () => c(o + d),
          children: l("التالي")
        })]
      })]
    })]
  });
}
function qe({
  label: e,
  value: t,
  strong: n,
  note: r
}) {
  return s.jsxs("div", {
    className: `flex items-baseline justify-between gap-3 border-b py-2 ${n ? "text-2xl font-extrabold" : "text-lg"}`,
    children: [s.jsxs("span", {
      children: [e, r && s.jsx("span", {
        className: "block text-sm font-normal text-slate-500",
        children: r
      })]
    }), s.jsx("span", {
      dir: "ltr",
      children: t
    })]
  });
}
// Recovered route component for /finance; original filename/name unknown.
function p2() {
  var i;
  const [e, t] = w.useState({
      date_from: Ns().slice(0, 8) + "01",
      date_to: Ns()
    }),
    n = W({
      queryKey: ["fin", e],
      queryFn: () => M.get(`/api/reports/financial-summary${Re(e)}`)
    }),
    r = n.data;
  return s.jsxs(s.Fragment, {
    children: [s.jsx(qr, {}), s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(pu, {
        size: 36
      }), l("الملخص المالي")]
    }), s.jsx(B, {
      children: s.jsxs("div", {
        className: "no-print grid gap-3 sm:grid-cols-3",
        children: [s.jsx(E, {
          label: l("من"),
          children: s.jsx("input", {
            type: "date",
            value: e.date_from,
            onChange: a => t({
              ...e,
              date_from: a.target.value
            }),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("إلى"),
          children: s.jsx("input", {
            type: "date",
            value: e.date_to,
            onChange: a => t({
              ...e,
              date_to: a.target.value
            }),
            dir: "ltr"
          })
        }), s.jsx("div", {
          className: "flex items-end",
          children: s.jsx(P, {
            kind: "secondary",
            icon: fn,
            onClick: () => window.print(),
            children: l("طباعة")
          })
        })]
      })
    }), n.isLoading ? s.jsx(ie, {}) : n.error || !r ? s.jsx($, {
      message: (i = n.error) == null ? void 0 : i.message
    }) : s.jsxs("div", {
      className: "grid gap-5 lg:grid-cols-2",
      children: [s.jsxs(B, {
        title: l("الإيرادات (فواتير صادرة)"),
        children: [s.jsx(qe, {
          label: l("أجور"),
          value: r.labor_billed
        }), s.jsx(qe, {
          label: l("قطع غيار"),
          value: r.parts_billed
        }), Number(r.other_billed) > 0 && s.jsx(qe, {
          label: l("أخرى"),
          value: r.other_billed
        }), s.jsx(qe, {
          label: l("إيراد الفواتير بعد الخصم (بدون ضريبة)"),
          value: r.revenue_invoiced_ex_tax
        }), s.jsx(qe, {
          label: l("إشعارات دائنة"),
          value: `- ${r.credit_notes}`
        }), s.jsx(qe, {
          label: l("صافي الإيراد"),
          value: r.net_revenue_ex_tax,
          strong: !0
        }), s.jsx(qe, {
          label: l("ضريبة محصّلة بالفواتير"),
          value: r.tax_invoiced,
          note: l("ليست إيراداً")
        }), s.jsxs("p", {
          className: "mt-2 text-slate-500",
          children: [l("عدد الفواتير:"), " ", r.invoices_issued]
        })]
      }), s.jsxs(B, {
        title: l("الأرباح"),
        children: [s.jsx(qe, {
          label: l("صافي الإيراد"),
          value: r.net_revenue_ex_tax
        }), s.jsx(qe, {
          label: l("تكلفة قطع الغيار"),
          value: `- ${r.direct_costs_parts}`
        }), s.jsx(qe, {
          label: l("مجمل الربح"),
          value: r.gross_profit,
          strong: !0
        }), s.jsx(qe, {
          label: l("مصروفات التشغيل"),
          value: `- ${r.operating_expenses}`
        }), s.jsx(qe, {
          label: l("صافي الربح التقديري"),
          value: r.estimated_net_profit,
          strong: !0,
          note: l("تقديري: لا يشمل رواتب غير مسجلة كمصروف")
        })]
      }), s.jsxs(B, {
        title: l("النقدية (ما تم تحصيله فعلاً)"),
        children: [s.jsx(qe, {
          label: l("مقبوضات"),
          value: r.cash_received
        }), s.jsx(qe, {
          label: l("مستردات للعملاء"),
          value: `- ${r.refunds_paid}`
        }), s.jsx(qe, {
          label: l("صافي النقدية"),
          value: r.net_cash_collected,
          strong: !0
        })]
      }), s.jsx(B, {
        title: l("مستحقات عند العملاء"),
        children: s.jsx(qe, {
          label: l("إجمالي المتبقي على الفواتير الصادرة"),
          value: r.receivables_outstanding,
          strong: !0,
          note: l("حتى الآن (لا يتأثر بالفترة)")
        })
      })]
    })]
  });
}
var Br = {},
  f2 = function () {
    return typeof Promise == "function" && Promise.prototype && Promise.prototype.then;
  },
  gy = {},
  yt = {};
let Nu;
const m2 = [0, 26, 44, 70, 100, 134, 172, 196, 242, 292, 346, 404, 466, 532, 581, 655, 733, 815, 901, 991, 1085, 1156, 1258, 1364, 1474, 1588, 1706, 1828, 1921, 2051, 2185, 2323, 2465, 2611, 2761, 2876, 3034, 3196, 3362, 3532, 3706];
yt.getSymbolSize = function (t) {
  if (!t) throw new Error('"version" cannot be null or undefined');
  if (t < 1 || t > 40) throw new Error('"version" should be in range from 1 to 40');
  return t * 4 + 17;
};
yt.getSymbolTotalCodewords = function (t) {
  return m2[t];
};
yt.getBCHDigit = function (e) {
  let t = 0;
  for (; e !== 0;) t++, e >>>= 1;
  return t;
};
yt.setToSJISFunction = function (t) {
  if (typeof t != "function") throw new Error('"toSJISFunc" is not a valid function.');
  Nu = t;
};
yt.isKanjiModeEnabled = function () {
  return typeof Nu < "u";
};
yt.toSJIS = function (t) {
  return Nu(t);
};
var Gl = {};
(function (e) {
  e.L = {
    bit: 1
  }, e.M = {
    bit: 0
  }, e.Q = {
    bit: 3
  }, e.H = {
    bit: 2
  };
  function t(n) {
    if (typeof n != "string") throw new Error("Param is not a string");
    switch (n.toLowerCase()) {
      case "l":
      case "low":
        return e.L;
      case "m":
      case "medium":
        return e.M;
      case "q":
      case "quartile":
        return e.Q;
      case "h":
      case "high":
        return e.H;
      default:
        throw new Error("Unknown EC Level: " + n);
    }
  }
  e.isValid = function (r) {
    return r && typeof r.bit < "u" && r.bit >= 0 && r.bit < 4;
  }, e.from = function (r, i) {
    if (e.isValid(r)) return r;
    try {
      return t(r);
    } catch {
      return i;
    }
  };
})(Gl);
function yy() {
  this.buffer = [], this.length = 0;
}
yy.prototype = {
  get: function (e) {
    const t = Math.floor(e / 8);
    return (this.buffer[t] >>> 7 - e % 8 & 1) === 1;
  },
  put: function (e, t) {
    for (let n = 0; n < t; n++) this.putBit((e >>> t - n - 1 & 1) === 1);
  },
  getLengthInBits: function () {
    return this.length;
  },
  putBit: function (e) {
    const t = Math.floor(this.length / 8);
    this.buffer.length <= t && this.buffer.push(0), e && (this.buffer[t] |= 128 >>> this.length % 8), this.length++;
  }
};
var x2 = yy;
function aa(e) {
  if (!e || e < 1) throw new Error("BitMatrix size must be defined and greater than 0");
  this.size = e, this.data = new Uint8Array(e * e), this.reservedBit = new Uint8Array(e * e);
}
aa.prototype.set = function (e, t, n, r) {
  const i = e * this.size + t;
  this.data[i] = n, r && (this.reservedBit[i] = !0);
};
aa.prototype.get = function (e, t) {
  return this.data[e * this.size + t];
};
aa.prototype.xor = function (e, t, n) {
  this.data[e * this.size + t] ^= n;
};
aa.prototype.isReserved = function (e, t) {
  return this.reservedBit[e * this.size + t];
};
var g2 = aa,
  vy = {};
(function (e) {
  const t = yt.getSymbolSize;
  e.getRowColCoords = function (r) {
    if (r === 1) return [];
    const i = Math.floor(r / 7) + 2,
      a = t(r),
      o = a === 145 ? 26 : Math.ceil((a - 13) / (2 * i - 2)) * 2,
      c = [a - 7];
    for (let d = 1; d < i - 1; d++) c[d] = c[d - 1] - o;
    return c.push(6), c.reverse();
  }, e.getPositions = function (r) {
    const i = [],
      a = e.getRowColCoords(r),
      o = a.length;
    for (let c = 0; c < o; c++) for (let d = 0; d < o; d++) c === 0 && d === 0 || c === 0 && d === o - 1 || c === o - 1 && d === 0 || i.push([a[c], a[d]]);
    return i;
  };
})(vy);
var jy = {};
const y2 = yt.getSymbolSize,
  bp = 7;
jy.getPositions = function (t) {
  const n = y2(t);
  return [[0, 0], [n - bp, 0], [0, n - bp]];
};
var by = {};
(function (e) {
  e.Patterns = {
    PATTERN000: 0,
    PATTERN001: 1,
    PATTERN010: 2,
    PATTERN011: 3,
    PATTERN100: 4,
    PATTERN101: 5,
    PATTERN110: 6,
    PATTERN111: 7
  };
  const t = {
    N1: 3,
    N2: 3,
    N3: 40,
    N4: 10
  };
  e.isValid = function (i) {
    return i != null && i !== "" && !isNaN(i) && i >= 0 && i <= 7;
  }, e.from = function (i) {
    return e.isValid(i) ? parseInt(i, 10) : void 0;
  }, e.getPenaltyN1 = function (i) {
    const a = i.size;
    let o = 0,
      c = 0,
      d = 0,
      u = null,
      h = null;
    for (let p = 0; p < a; p++) {
      c = d = 0, u = h = null;
      for (let m = 0; m < a; m++) {
        let y = i.get(p, m);
        y === u ? c++ : (c >= 5 && (o += t.N1 + (c - 5)), u = y, c = 1), y = i.get(m, p), y === h ? d++ : (d >= 5 && (o += t.N1 + (d - 5)), h = y, d = 1);
      }
      c >= 5 && (o += t.N1 + (c - 5)), d >= 5 && (o += t.N1 + (d - 5));
    }
    return o;
  }, e.getPenaltyN2 = function (i) {
    const a = i.size;
    let o = 0;
    for (let c = 0; c < a - 1; c++) for (let d = 0; d < a - 1; d++) {
      const u = i.get(c, d) + i.get(c, d + 1) + i.get(c + 1, d) + i.get(c + 1, d + 1);
      (u === 4 || u === 0) && o++;
    }
    return o * t.N2;
  }, e.getPenaltyN3 = function (i) {
    const a = i.size;
    let o = 0,
      c = 0,
      d = 0;
    for (let u = 0; u < a; u++) {
      c = d = 0;
      for (let h = 0; h < a; h++) c = c << 1 & 2047 | i.get(u, h), h >= 10 && (c === 1488 || c === 93) && o++, d = d << 1 & 2047 | i.get(h, u), h >= 10 && (d === 1488 || d === 93) && o++;
    }
    return o * t.N3;
  }, e.getPenaltyN4 = function (i) {
    let a = 0;
    const o = i.data.length;
    for (let d = 0; d < o; d++) a += i.data[d];
    return Math.abs(Math.ceil(a * 100 / o / 5) - 10) * t.N4;
  };
  function n(r, i, a) {
    switch (r) {
      case e.Patterns.PATTERN000:
        return (i + a) % 2 === 0;
      case e.Patterns.PATTERN001:
        return i % 2 === 0;
      case e.Patterns.PATTERN010:
        return a % 3 === 0;
      case e.Patterns.PATTERN011:
        return (i + a) % 3 === 0;
      case e.Patterns.PATTERN100:
        return (Math.floor(i / 2) + Math.floor(a / 3)) % 2 === 0;
      case e.Patterns.PATTERN101:
        return i * a % 2 + i * a % 3 === 0;
      case e.Patterns.PATTERN110:
        return (i * a % 2 + i * a % 3) % 2 === 0;
      case e.Patterns.PATTERN111:
        return (i * a % 3 + (i + a) % 2) % 2 === 0;
      default:
        throw new Error("bad maskPattern:" + r);
    }
  }
  e.applyMask = function (i, a) {
    const o = a.size;
    for (let c = 0; c < o; c++) for (let d = 0; d < o; d++) a.isReserved(d, c) || a.xor(d, c, n(i, d, c));
  }, e.getBestMask = function (i, a) {
    const o = Object.keys(e.Patterns).length;
    let c = 0,
      d = 1 / 0;
    for (let u = 0; u < o; u++) {
      a(u), e.applyMask(u, i);
      const h = e.getPenaltyN1(i) + e.getPenaltyN2(i) + e.getPenaltyN3(i) + e.getPenaltyN4(i);
      e.applyMask(u, i), h < d && (d = h, c = u);
    }
    return c;
  };
})(by);
var Jl = {};
const Ln = Gl,
  Sa = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 1, 2, 2, 4, 1, 2, 4, 4, 2, 4, 4, 4, 2, 4, 6, 5, 2, 4, 6, 6, 2, 5, 8, 8, 4, 5, 8, 8, 4, 5, 8, 11, 4, 8, 10, 11, 4, 9, 12, 16, 4, 9, 16, 16, 6, 10, 12, 18, 6, 10, 17, 16, 6, 11, 16, 19, 6, 13, 18, 21, 7, 14, 21, 25, 8, 16, 20, 25, 8, 17, 23, 25, 9, 17, 23, 34, 9, 18, 25, 30, 10, 20, 27, 32, 12, 21, 29, 35, 12, 23, 34, 37, 12, 25, 34, 40, 13, 26, 35, 42, 14, 28, 38, 45, 15, 29, 40, 48, 16, 31, 43, 51, 17, 33, 45, 54, 18, 35, 48, 57, 19, 37, 51, 60, 19, 38, 53, 63, 20, 40, 56, 66, 21, 43, 59, 70, 22, 45, 62, 74, 24, 47, 65, 77, 25, 49, 68, 81],
  Ea = [7, 10, 13, 17, 10, 16, 22, 28, 15, 26, 36, 44, 20, 36, 52, 64, 26, 48, 72, 88, 36, 64, 96, 112, 40, 72, 108, 130, 48, 88, 132, 156, 60, 110, 160, 192, 72, 130, 192, 224, 80, 150, 224, 264, 96, 176, 260, 308, 104, 198, 288, 352, 120, 216, 320, 384, 132, 240, 360, 432, 144, 280, 408, 480, 168, 308, 448, 532, 180, 338, 504, 588, 196, 364, 546, 650, 224, 416, 600, 700, 224, 442, 644, 750, 252, 476, 690, 816, 270, 504, 750, 900, 300, 560, 810, 960, 312, 588, 870, 1050, 336, 644, 952, 1110, 360, 700, 1020, 1200, 390, 728, 1050, 1260, 420, 784, 1140, 1350, 450, 812, 1200, 1440, 480, 868, 1290, 1530, 510, 924, 1350, 1620, 540, 980, 1440, 1710, 570, 1036, 1530, 1800, 570, 1064, 1590, 1890, 600, 1120, 1680, 1980, 630, 1204, 1770, 2100, 660, 1260, 1860, 2220, 720, 1316, 1950, 2310, 750, 1372, 2040, 2430];
Jl.getBlocksCount = function (t, n) {
  switch (n) {
    case Ln.L:
      return Sa[(t - 1) * 4 + 0];
    case Ln.M:
      return Sa[(t - 1) * 4 + 1];
    case Ln.Q:
      return Sa[(t - 1) * 4 + 2];
    case Ln.H:
      return Sa[(t - 1) * 4 + 3];
    default:
      return;
  }
};
Jl.getTotalCodewordsCount = function (t, n) {
  switch (n) {
    case Ln.L:
      return Ea[(t - 1) * 4 + 0];
    case Ln.M:
      return Ea[(t - 1) * 4 + 1];
    case Ln.Q:
      return Ea[(t - 1) * 4 + 2];
    case Ln.H:
      return Ea[(t - 1) * 4 + 3];
    default:
      return;
  }
};
var wy = {},
  Yl = {};
const gi = new Uint8Array(512),
  kl = new Uint8Array(256);
(function () {
  let t = 1;
  for (let n = 0; n < 255; n++) gi[n] = t, kl[t] = n, t <<= 1, t & 256 && (t ^= 285);
  for (let n = 255; n < 512; n++) gi[n] = gi[n - 255];
})();
Yl.log = function (t) {
  if (t < 1) throw new Error("log(" + t + ")");
  return kl[t];
};
Yl.exp = function (t) {
  return gi[t];
};
Yl.mul = function (t, n) {
  return t === 0 || n === 0 ? 0 : gi[kl[t] + kl[n]];
};
(function (e) {
  const t = Yl;
  e.mul = function (r, i) {
    const a = new Uint8Array(r.length + i.length - 1);
    for (let o = 0; o < r.length; o++) for (let c = 0; c < i.length; c++) a[o + c] ^= t.mul(r[o], i[c]);
    return a;
  }, e.mod = function (r, i) {
    let a = new Uint8Array(r);
    for (; a.length - i.length >= 0;) {
      const o = a[0];
      for (let d = 0; d < i.length; d++) a[d] ^= t.mul(i[d], o);
      let c = 0;
      for (; c < a.length && a[c] === 0;) c++;
      a = a.slice(c);
    }
    return a;
  }, e.generateECPolynomial = function (r) {
    let i = new Uint8Array([1]);
    for (let a = 0; a < r; a++) i = e.mul(i, new Uint8Array([1, t.exp(a)]));
    return i;
  };
})(wy);
const ky = wy;
function _u(e) {
  this.genPoly = void 0, this.degree = e, this.degree && this.initialize(this.degree);
}
_u.prototype.initialize = function (t) {
  this.degree = t, this.genPoly = ky.generateECPolynomial(this.degree);
};
_u.prototype.encode = function (t) {
  if (!this.genPoly) throw new Error("Encoder not initialized");
  const n = new Uint8Array(t.length + this.degree);
  n.set(t);
  const r = ky.mod(n, this.genPoly),
    i = this.degree - r.length;
  if (i > 0) {
    const a = new Uint8Array(this.degree);
    return a.set(r, i), a;
  }
  return r;
};
var v2 = _u,
  Ny = {},
  ss = {},
  Cu = {};
Cu.isValid = function (t) {
  return !isNaN(t) && t >= 1 && t <= 40;
};
var Jt = {};
const _y = "[0-9]+",
  j2 = "[A-Z $%*+\\-./:]+";
let Ui = "(?:[u3000-u303F]|[u3040-u309F]|[u30A0-u30FF]|[uFF00-uFFEF]|[u4E00-u9FAF]|[u2605-u2606]|[u2190-u2195]|u203B|[u2010u2015u2018u2019u2025u2026u201Cu201Du2225u2260]|[u0391-u0451]|[u00A7u00A8u00B1u00B4u00D7u00F7])+";
Ui = Ui.replace(/u/g, "\\u");
const b2 = "(?:(?![A-Z0-9 $%*+\\-./:]|" + Ui + `)(?:.|[\r
]))+`;
Jt.KANJI = new RegExp(Ui, "g");
Jt.BYTE_KANJI = new RegExp("[^A-Z0-9 $%*+\\-./:]+", "g");
Jt.BYTE = new RegExp(b2, "g");
Jt.NUMERIC = new RegExp(_y, "g");
Jt.ALPHANUMERIC = new RegExp(j2, "g");
const w2 = new RegExp("^" + Ui + "$"),
  k2 = new RegExp("^" + _y + "$"),
  N2 = new RegExp("^[A-Z0-9 $%*+\\-./:]+$");
Jt.testKanji = function (t) {
  return w2.test(t);
};
Jt.testNumeric = function (t) {
  return k2.test(t);
};
Jt.testAlphanumeric = function (t) {
  return N2.test(t);
};
(function (e) {
  const t = Cu,
    n = Jt;
  e.NUMERIC = {
    id: "Numeric",
    bit: 1,
    ccBits: [10, 12, 14]
  }, e.ALPHANUMERIC = {
    id: "Alphanumeric",
    bit: 2,
    ccBits: [9, 11, 13]
  }, e.BYTE = {
    id: "Byte",
    bit: 4,
    ccBits: [8, 16, 16]
  }, e.KANJI = {
    id: "Kanji",
    bit: 8,
    ccBits: [8, 10, 12]
  }, e.MIXED = {
    bit: -1
  }, e.getCharCountIndicator = function (a, o) {
    if (!a.ccBits) throw new Error("Invalid mode: " + a);
    if (!t.isValid(o)) throw new Error("Invalid version: " + o);
    return o >= 1 && o < 10 ? a.ccBits[0] : o < 27 ? a.ccBits[1] : a.ccBits[2];
  }, e.getBestModeForData = function (a) {
    return n.testNumeric(a) ? e.NUMERIC : n.testAlphanumeric(a) ? e.ALPHANUMERIC : n.testKanji(a) ? e.KANJI : e.BYTE;
  }, e.toString = function (a) {
    if (a && a.id) return a.id;
    throw new Error("Invalid mode");
  }, e.isValid = function (a) {
    return a && a.bit && a.ccBits;
  };
  function r(i) {
    if (typeof i != "string") throw new Error("Param is not a string");
    switch (i.toLowerCase()) {
      case "numeric":
        return e.NUMERIC;
      case "alphanumeric":
        return e.ALPHANUMERIC;
      case "kanji":
        return e.KANJI;
      case "byte":
        return e.BYTE;
      default:
        throw new Error("Unknown mode: " + i);
    }
  }
  e.from = function (a, o) {
    if (e.isValid(a)) return a;
    try {
      return r(a);
    } catch {
      return o;
    }
  };
})(ss);
(function (e) {
  const t = yt,
    n = Jl,
    r = Gl,
    i = ss,
    a = Cu,
    o = 7973,
    c = t.getBCHDigit(o);
  function d(m, y, j) {
    for (let v = 1; v <= 40; v++) if (y <= e.getCapacity(v, j, m)) return v;
  }
  function u(m, y) {
    return i.getCharCountIndicator(m, y) + 4;
  }
  function h(m, y) {
    let j = 0;
    return m.forEach(function (v) {
      const N = u(v.mode, y);
      j += N + v.getBitsLength();
    }), j;
  }
  function p(m, y) {
    for (let j = 1; j <= 40; j++) if (h(m, j) <= e.getCapacity(j, y, i.MIXED)) return j;
  }
  e.from = function (y, j) {
    return a.isValid(y) ? parseInt(y, 10) : j;
  }, e.getCapacity = function (y, j, v) {
    if (!a.isValid(y)) throw new Error("Invalid QR Code version");
    typeof v > "u" && (v = i.BYTE);
    const N = t.getSymbolTotalCodewords(y),
      x = n.getTotalCodewordsCount(y, j),
      f = (N - x) * 8;
    if (v === i.MIXED) return f;
    const g = f - u(v, y);
    switch (v) {
      case i.NUMERIC:
        return Math.floor(g / 10 * 3);
      case i.ALPHANUMERIC:
        return Math.floor(g / 11 * 2);
      case i.KANJI:
        return Math.floor(g / 13);
      case i.BYTE:
      default:
        return Math.floor(g / 8);
    }
  }, e.getBestVersionForData = function (y, j) {
    let v;
    const N = r.from(j, r.M);
    if (Array.isArray(y)) {
      if (y.length > 1) return p(y, N);
      if (y.length === 0) return 1;
      v = y[0];
    } else v = y;
    return d(v.mode, v.getLength(), N);
  }, e.getEncodedBits = function (y) {
    if (!a.isValid(y) || y < 7) throw new Error("Invalid QR Code version");
    let j = y << 12;
    for (; t.getBCHDigit(j) - c >= 0;) j ^= o << t.getBCHDigit(j) - c;
    return y << 12 | j;
  };
})(Ny);
var Cy = {};
const nd = yt,
  Sy = 1335,
  _2 = 21522,
  wp = nd.getBCHDigit(Sy);
Cy.getEncodedBits = function (t, n) {
  const r = t.bit << 3 | n;
  let i = r << 10;
  for (; nd.getBCHDigit(i) - wp >= 0;) i ^= Sy << nd.getBCHDigit(i) - wp;
  return (r << 10 | i) ^ _2;
};
var Ey = {};
const C2 = ss;
function Rr(e) {
  this.mode = C2.NUMERIC, this.data = e.toString();
}
Rr.getBitsLength = function (t) {
  return 10 * Math.floor(t / 3) + (t % 3 ? t % 3 * 3 + 1 : 0);
};
Rr.prototype.getLength = function () {
  return this.data.length;
};
Rr.prototype.getBitsLength = function () {
  return Rr.getBitsLength(this.data.length);
};
Rr.prototype.write = function (t) {
  let n, r, i;
  for (n = 0; n + 3 <= this.data.length; n += 3) r = this.data.substr(n, 3), i = parseInt(r, 10), t.put(i, 10);
  const a = this.data.length - n;
  a > 0 && (r = this.data.substr(n), i = parseInt(r, 10), t.put(i, a * 3 + 1));
};
var S2 = Rr;
const E2 = ss,
  Lo = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", " ", "$", "%", "*", "+", "-", ".", "/", ":"];
function Mr(e) {
  this.mode = E2.ALPHANUMERIC, this.data = e;
}
Mr.getBitsLength = function (t) {
  return 11 * Math.floor(t / 2) + 6 * (t % 2);
};
Mr.prototype.getLength = function () {
  return this.data.length;
};
Mr.prototype.getBitsLength = function () {
  return Mr.getBitsLength(this.data.length);
};
Mr.prototype.write = function (t) {
  let n;
  for (n = 0; n + 2 <= this.data.length; n += 2) {
    let r = Lo.indexOf(this.data[n]) * 45;
    r += Lo.indexOf(this.data[n + 1]), t.put(r, 11);
  }
  this.data.length % 2 && t.put(Lo.indexOf(this.data[n]), 6);
};
var P2 = Mr;
const R2 = ss;
function Tr(e) {
  this.mode = R2.BYTE, typeof e == "string" ? this.data = new TextEncoder().encode(e) : this.data = new Uint8Array(e);
}
Tr.getBitsLength = function (t) {
  return t * 8;
};
Tr.prototype.getLength = function () {
  return this.data.length;
};
Tr.prototype.getBitsLength = function () {
  return Tr.getBitsLength(this.data.length);
};
Tr.prototype.write = function (e) {
  for (let t = 0, n = this.data.length; t < n; t++) e.put(this.data[t], 8);
};
var M2 = Tr;
const T2 = ss,
  F2 = yt;
function Fr(e) {
  this.mode = T2.KANJI, this.data = e;
}
Fr.getBitsLength = function (t) {
  return t * 13;
};
Fr.prototype.getLength = function () {
  return this.data.length;
};
Fr.prototype.getBitsLength = function () {
  return Fr.getBitsLength(this.data.length);
};
Fr.prototype.write = function (e) {
  let t;
  for (t = 0; t < this.data.length; t++) {
    let n = F2.toSJIS(this.data[t]);
    if (n >= 33088 && n <= 40956) n -= 33088;else if (n >= 57408 && n <= 60351) n -= 49472;else throw new Error("Invalid SJIS character: " + this.data[t] + `
Make sure your charset is UTF-8`);
    n = (n >>> 8 & 255) * 192 + (n & 255), e.put(n, 13);
  }
};
var L2 = Fr,
  Py = {
    exports: {}
  };
(function (e) {
  var t = {
    single_source_shortest_paths: function (n, r, i) {
      var a = {},
        o = {};
      o[r] = 0;
      var c = t.PriorityQueue.make();
      c.push(r, 0);
      for (var d, u, h, p, m, y, j, v, N; !c.empty();) {
        d = c.pop(), u = d.value, p = d.cost, m = n[u] || {};
        for (h in m) m.hasOwnProperty(h) && (y = m[h], j = p + y, v = o[h], N = typeof o[h] > "u", (N || v > j) && (o[h] = j, c.push(h, j), a[h] = u));
      }
      if (typeof i < "u" && typeof o[i] > "u") {
        var x = ["Could not find a path from ", r, " to ", i, "."].join("");
        throw new Error(x);
      }
      return a;
    },
    extract_shortest_path_from_predecessor_list: function (n, r) {
      for (var i = [], a = r; a;) i.push(a), n[a], a = n[a];
      return i.reverse(), i;
    },
    find_path: function (n, r, i) {
      var a = t.single_source_shortest_paths(n, r, i);
      return t.extract_shortest_path_from_predecessor_list(a, i);
    },
    PriorityQueue: {
      make: function (n) {
        var r = t.PriorityQueue,
          i = {},
          a;
        n = n || {};
        for (a in r) r.hasOwnProperty(a) && (i[a] = r[a]);
        return i.queue = [], i.sorter = n.sorter || r.default_sorter, i;
      },
      default_sorter: function (n, r) {
        return n.cost - r.cost;
      },
      push: function (n, r) {
        var i = {
          value: n,
          cost: r
        };
        this.queue.push(i), this.queue.sort(this.sorter);
      },
      pop: function () {
        return this.queue.shift();
      },
      empty: function () {
        return this.queue.length === 0;
      }
    }
  };
  e.exports = t;
})(Py);
var D2 = Py.exports;
(function (e) {
  const t = ss,
    n = S2,
    r = P2,
    i = M2,
    a = L2,
    o = Jt,
    c = yt,
    d = D2;
  function u(x) {
    return unescape(encodeURIComponent(x)).length;
  }
  function h(x, f, g) {
    const b = [];
    let k;
    for (; (k = x.exec(g)) !== null;) b.push({
      data: k[0],
      index: k.index,
      mode: f,
      length: k[0].length
    });
    return b;
  }
  function p(x) {
    const f = h(o.NUMERIC, t.NUMERIC, x),
      g = h(o.ALPHANUMERIC, t.ALPHANUMERIC, x);
    let b, k;
    return c.isKanjiModeEnabled() ? (b = h(o.BYTE, t.BYTE, x), k = h(o.KANJI, t.KANJI, x)) : (b = h(o.BYTE_KANJI, t.BYTE, x), k = []), f.concat(g, b, k).sort(function (S, T) {
      return S.index - T.index;
    }).map(function (S) {
      return {
        data: S.data,
        mode: S.mode,
        length: S.length
      };
    });
  }
  function m(x, f) {
    switch (f) {
      case t.NUMERIC:
        return n.getBitsLength(x);
      case t.ALPHANUMERIC:
        return r.getBitsLength(x);
      case t.KANJI:
        return a.getBitsLength(x);
      case t.BYTE:
        return i.getBitsLength(x);
    }
  }
  function y(x) {
    return x.reduce(function (f, g) {
      const b = f.length - 1 >= 0 ? f[f.length - 1] : null;
      return b && b.mode === g.mode ? (f[f.length - 1].data += g.data, f) : (f.push(g), f);
    }, []);
  }
  function j(x) {
    const f = [];
    for (let g = 0; g < x.length; g++) {
      const b = x[g];
      switch (b.mode) {
        case t.NUMERIC:
          f.push([b, {
            data: b.data,
            mode: t.ALPHANUMERIC,
            length: b.length
          }, {
            data: b.data,
            mode: t.BYTE,
            length: b.length
          }]);
          break;
        case t.ALPHANUMERIC:
          f.push([b, {
            data: b.data,
            mode: t.BYTE,
            length: b.length
          }]);
          break;
        case t.KANJI:
          f.push([b, {
            data: b.data,
            mode: t.BYTE,
            length: u(b.data)
          }]);
          break;
        case t.BYTE:
          f.push([{
            data: b.data,
            mode: t.BYTE,
            length: u(b.data)
          }]);
      }
    }
    return f;
  }
  function v(x, f) {
    const g = {},
      b = {
        start: {}
      };
    let k = ["start"];
    for (let _ = 0; _ < x.length; _++) {
      const S = x[_],
        T = [];
      for (let R = 0; R < S.length; R++) {
        const F = S[R],
          X = "" + _ + R;
        T.push(X), g[X] = {
          node: F,
          lastCount: 0
        }, b[X] = {};
        for (let te = 0; te < k.length; te++) {
          const L = k[te];
          g[L] && g[L].node.mode === F.mode ? (b[L][X] = m(g[L].lastCount + F.length, F.mode) - m(g[L].lastCount, F.mode), g[L].lastCount += F.length) : (g[L] && (g[L].lastCount = F.length), b[L][X] = m(F.length, F.mode) + 4 + t.getCharCountIndicator(F.mode, f));
        }
      }
      k = T;
    }
    for (let _ = 0; _ < k.length; _++) b[k[_]].end = 0;
    return {
      map: b,
      table: g
    };
  }
  function N(x, f) {
    let g;
    const b = t.getBestModeForData(x);
    if (g = t.from(f, b), g !== t.BYTE && g.bit < b.bit) throw new Error('"' + x + '" cannot be encoded with mode ' + t.toString(g) + `.
 Suggested mode is: ` + t.toString(b));
    switch (g === t.KANJI && !c.isKanjiModeEnabled() && (g = t.BYTE), g) {
      case t.NUMERIC:
        return new n(x);
      case t.ALPHANUMERIC:
        return new r(x);
      case t.KANJI:
        return new a(x);
      case t.BYTE:
        return new i(x);
    }
  }
  e.fromArray = function (f) {
    return f.reduce(function (g, b) {
      return typeof b == "string" ? g.push(N(b, null)) : b.data && g.push(N(b.data, b.mode)), g;
    }, []);
  }, e.fromString = function (f, g) {
    const b = p(f, c.isKanjiModeEnabled()),
      k = j(b),
      _ = v(k, g),
      S = d.find_path(_.map, "start", "end"),
      T = [];
    for (let R = 1; R < S.length - 1; R++) T.push(_.table[S[R]].node);
    return e.fromArray(y(T));
  }, e.rawSplit = function (f) {
    return e.fromArray(p(f, c.isKanjiModeEnabled()));
  };
})(Ey);
const Zl = yt,
  Do = Gl,
  z2 = x2,
  I2 = g2,
  $2 = vy,
  A2 = jy,
  sd = by,
  rd = Jl,
  O2 = v2,
  Nl = Ny,
  q2 = Cy,
  B2 = ss,
  zo = Ey;
function U2(e, t) {
  const n = e.size,
    r = A2.getPositions(t);
  for (let i = 0; i < r.length; i++) {
    const a = r[i][0],
      o = r[i][1];
    for (let c = -1; c <= 7; c++) if (!(a + c <= -1 || n <= a + c)) for (let d = -1; d <= 7; d++) o + d <= -1 || n <= o + d || (c >= 0 && c <= 6 && (d === 0 || d === 6) || d >= 0 && d <= 6 && (c === 0 || c === 6) || c >= 2 && c <= 4 && d >= 2 && d <= 4 ? e.set(a + c, o + d, !0, !0) : e.set(a + c, o + d, !1, !0));
  }
}
function Q2(e) {
  const t = e.size;
  for (let n = 8; n < t - 8; n++) {
    const r = n % 2 === 0;
    e.set(n, 6, r, !0), e.set(6, n, r, !0);
  }
}
function K2(e, t) {
  const n = $2.getPositions(t);
  for (let r = 0; r < n.length; r++) {
    const i = n[r][0],
      a = n[r][1];
    for (let o = -2; o <= 2; o++) for (let c = -2; c <= 2; c++) o === -2 || o === 2 || c === -2 || c === 2 || o === 0 && c === 0 ? e.set(i + o, a + c, !0, !0) : e.set(i + o, a + c, !1, !0);
  }
}
function V2(e, t) {
  const n = e.size,
    r = Nl.getEncodedBits(t);
  let i, a, o;
  for (let c = 0; c < 18; c++) i = Math.floor(c / 3), a = c % 3 + n - 8 - 3, o = (r >> c & 1) === 1, e.set(i, a, o, !0), e.set(a, i, o, !0);
}
function Io(e, t, n) {
  const r = e.size,
    i = q2.getEncodedBits(t, n);
  let a, o;
  for (a = 0; a < 15; a++) o = (i >> a & 1) === 1, a < 6 ? e.set(a, 8, o, !0) : a < 8 ? e.set(a + 1, 8, o, !0) : e.set(r - 15 + a, 8, o, !0), a < 8 ? e.set(8, r - a - 1, o, !0) : a < 9 ? e.set(8, 15 - a - 1 + 1, o, !0) : e.set(8, 15 - a - 1, o, !0);
  e.set(r - 8, 8, 1, !0);
}
function W2(e, t) {
  const n = e.size;
  let r = -1,
    i = n - 1,
    a = 7,
    o = 0;
  for (let c = n - 1; c > 0; c -= 2) for (c === 6 && c--;;) {
    for (let d = 0; d < 2; d++) if (!e.isReserved(i, c - d)) {
      let u = !1;
      o < t.length && (u = (t[o] >>> a & 1) === 1), e.set(i, c - d, u), a--, a === -1 && (o++, a = 7);
    }
    if (i += r, i < 0 || n <= i) {
      i -= r, r = -r;
      break;
    }
  }
}
function H2(e, t, n) {
  const r = new z2();
  n.forEach(function (d) {
    r.put(d.mode.bit, 4), r.put(d.getLength(), B2.getCharCountIndicator(d.mode, e)), d.write(r);
  });
  const i = Zl.getSymbolTotalCodewords(e),
    a = rd.getTotalCodewordsCount(e, t),
    o = (i - a) * 8;
  for (r.getLengthInBits() + 4 <= o && r.put(0, 4); r.getLengthInBits() % 8 !== 0;) r.putBit(0);
  const c = (o - r.getLengthInBits()) / 8;
  for (let d = 0; d < c; d++) r.put(d % 2 ? 17 : 236, 8);
  return G2(r, e, t);
}
function G2(e, t, n) {
  const r = Zl.getSymbolTotalCodewords(t),
    i = rd.getTotalCodewordsCount(t, n),
    a = r - i,
    o = rd.getBlocksCount(t, n),
    c = r % o,
    d = o - c,
    u = Math.floor(r / o),
    h = Math.floor(a / o),
    p = h + 1,
    m = u - h,
    y = new O2(m);
  let j = 0;
  const v = new Array(o),
    N = new Array(o);
  let x = 0;
  const f = new Uint8Array(e.buffer);
  for (let S = 0; S < o; S++) {
    const T = S < d ? h : p;
    v[S] = f.slice(j, j + T), N[S] = y.encode(v[S]), j += T, x = Math.max(x, T);
  }
  const g = new Uint8Array(r);
  let b = 0,
    k,
    _;
  for (k = 0; k < x; k++) for (_ = 0; _ < o; _++) k < v[_].length && (g[b++] = v[_][k]);
  for (k = 0; k < m; k++) for (_ = 0; _ < o; _++) g[b++] = N[_][k];
  return g;
}
function J2(e, t, n, r) {
  let i;
  if (Array.isArray(e)) i = zo.fromArray(e);else if (typeof e == "string") {
    let u = t;
    if (!u) {
      const h = zo.rawSplit(e);
      u = Nl.getBestVersionForData(h, n);
    }
    i = zo.fromString(e, u || 40);
  } else throw new Error("Invalid data");
  const a = Nl.getBestVersionForData(i, n);
  if (!a) throw new Error("The amount of data is too big to be stored in a QR Code");
  if (!t) t = a;else if (t < a) throw new Error(`
The chosen QR Code version cannot contain this amount of data.
Minimum version required to store current data is: ` + a + `.
`);
  const o = H2(t, n, i),
    c = Zl.getSymbolSize(t),
    d = new I2(c);
  return U2(d, t), Q2(d), K2(d, t), Io(d, n, 0), t >= 7 && V2(d, t), W2(d, o), isNaN(r) && (r = sd.getBestMask(d, Io.bind(null, d, n))), sd.applyMask(r, d), Io(d, n, r), {
    modules: d,
    version: t,
    errorCorrectionLevel: n,
    maskPattern: r,
    segments: i
  };
}
gy.create = function (t, n) {
  if (typeof t > "u" || t === "") throw new Error("No input text");
  let r = Do.M,
    i,
    a;
  return typeof n < "u" && (r = Do.from(n.errorCorrectionLevel, Do.M), i = Nl.from(n.version), a = sd.from(n.maskPattern), n.toSJISFunc && Zl.setToSJISFunction(n.toSJISFunc)), J2(t, i, r, a);
};
var Ry = {},
  Su = {};
(function (e) {
  function t(n) {
    if (typeof n == "number" && (n = n.toString()), typeof n != "string") throw new Error("Color should be defined as hex string");
    let r = n.slice().replace("#", "").split("");
    if (r.length < 3 || r.length === 5 || r.length > 8) throw new Error("Invalid hex color: " + n);
    (r.length === 3 || r.length === 4) && (r = Array.prototype.concat.apply([], r.map(function (a) {
      return [a, a];
    }))), r.length === 6 && r.push("F", "F");
    const i = parseInt(r.join(""), 16);
    return {
      r: i >> 24 & 255,
      g: i >> 16 & 255,
      b: i >> 8 & 255,
      a: i & 255,
      hex: "#" + r.slice(0, 6).join("")
    };
  }
  e.getOptions = function (r) {
    r || (r = {}), r.color || (r.color = {});
    const i = typeof r.margin > "u" || r.margin === null || r.margin < 0 ? 4 : r.margin,
      a = r.width && r.width >= 21 ? r.width : void 0,
      o = r.scale || 4;
    return {
      width: a,
      scale: a ? 4 : o,
      margin: i,
      color: {
        dark: t(r.color.dark || "#000000ff"),
        light: t(r.color.light || "#ffffffff")
      },
      type: r.type,
      rendererOpts: r.rendererOpts || {}
    };
  }, e.getScale = function (r, i) {
    return i.width && i.width >= r + i.margin * 2 ? i.width / (r + i.margin * 2) : i.scale;
  }, e.getImageWidth = function (r, i) {
    const a = e.getScale(r, i);
    return Math.floor((r + i.margin * 2) * a);
  }, e.qrToImageData = function (r, i, a) {
    const o = i.modules.size,
      c = i.modules.data,
      d = e.getScale(o, a),
      u = Math.floor((o + a.margin * 2) * d),
      h = a.margin * d,
      p = [a.color.light, a.color.dark];
    for (let m = 0; m < u; m++) for (let y = 0; y < u; y++) {
      let j = (m * u + y) * 4,
        v = a.color.light;
      if (m >= h && y >= h && m < u - h && y < u - h) {
        const N = Math.floor((m - h) / d),
          x = Math.floor((y - h) / d);
        v = p[c[N * o + x] ? 1 : 0];
      }
      r[j++] = v.r, r[j++] = v.g, r[j++] = v.b, r[j] = v.a;
    }
  };
})(Su);
(function (e) {
  const t = Su;
  function n(i, a, o) {
    i.clearRect(0, 0, a.width, a.height), a.style || (a.style = {}), a.height = o, a.width = o, a.style.height = o + "px", a.style.width = o + "px";
  }
  function r() {
    try {
      return document.createElement("canvas");
    } catch {
      throw new Error("You need to specify a canvas element");
    }
  }
  e.render = function (a, o, c) {
    let d = c,
      u = o;
    typeof d > "u" && (!o || !o.getContext) && (d = o, o = void 0), o || (u = r()), d = t.getOptions(d);
    const h = t.getImageWidth(a.modules.size, d),
      p = u.getContext("2d"),
      m = p.createImageData(h, h);
    return t.qrToImageData(m.data, a, d), n(p, u, h), p.putImageData(m, 0, 0), u;
  }, e.renderToDataURL = function (a, o, c) {
    let d = c;
    typeof d > "u" && (!o || !o.getContext) && (d = o, o = void 0), d || (d = {});
    const u = e.render(a, o, d),
      h = d.type || "image/png",
      p = d.rendererOpts || {};
    return u.toDataURL(h, p.quality);
  };
})(Ry);
var My = {};
const Y2 = Su;
function kp(e, t) {
  const n = e.a / 255,
    r = t + '="' + e.hex + '"';
  return n < 1 ? r + " " + t + '-opacity="' + n.toFixed(2).slice(1) + '"' : r;
}
function $o(e, t, n) {
  let r = e + t;
  return typeof n < "u" && (r += " " + n), r;
}
function Z2(e, t, n) {
  let r = "",
    i = 0,
    a = !1,
    o = 0;
  for (let c = 0; c < e.length; c++) {
    const d = Math.floor(c % t),
      u = Math.floor(c / t);
    !d && !a && (a = !0), e[c] ? (o++, c > 0 && d > 0 && e[c - 1] || (r += a ? $o("M", d + n, .5 + u + n) : $o("m", i, 0), i = 0, a = !1), d + 1 < t && e[c + 1] || (r += $o("h", o), o = 0)) : i++;
  }
  return r;
}
My.render = function (t, n, r) {
  const i = Y2.getOptions(n),
    a = t.modules.size,
    o = t.modules.data,
    c = a + i.margin * 2,
    d = i.color.light.a ? "<path " + kp(i.color.light, "fill") + ' d="M0 0h' + c + "v" + c + 'H0z"/>' : "",
    u = "<path " + kp(i.color.dark, "stroke") + ' d="' + Z2(o, a, i.margin) + '"/>',
    h = 'viewBox="0 0 ' + c + " " + c + '"',
    m = '<svg xmlns="http://www.w3.org/2000/svg" ' + (i.width ? 'width="' + i.width + '" height="' + i.width + '" ' : "") + h + ' shape-rendering="crispEdges">' + d + u + `</svg>
`;
  return typeof r == "function" && r(null, m), m;
};
const X2 = f2,
  id = gy,
  Ty = Ry,
  ew = My;
function Eu(e, t, n, r, i) {
  const a = [].slice.call(arguments, 1),
    o = a.length,
    c = typeof a[o - 1] == "function";
  if (!c && !X2()) throw new Error("Callback required as last argument");
  if (c) {
    if (o < 2) throw new Error("Too few arguments provided");
    o === 2 ? (i = n, n = t, t = r = void 0) : o === 3 && (t.getContext && typeof i > "u" ? (i = r, r = void 0) : (i = r, r = n, n = t, t = void 0));
  } else {
    if (o < 1) throw new Error("Too few arguments provided");
    return o === 1 ? (n = t, t = r = void 0) : o === 2 && !t.getContext && (r = n, n = t, t = void 0), new Promise(function (d, u) {
      try {
        const h = id.create(n, r);
        d(e(h, t, r));
      } catch (h) {
        u(h);
      }
    });
  }
  try {
    const d = id.create(n, r);
    i(null, e(d, t, r));
  } catch (d) {
    i(d);
  }
}
Br.create = id.create;
Br.toCanvas = Eu.bind(null, Ty.render);
Br.toDataURL = Eu.bind(null, Ty.renderToDataURL);
Br.toString = Eu.bind(null, function (e, t, n) {
  return ew.render(e, n);
});
const Fy = "autocare.invoice.layout",
  tw = () => {
    try {
      const e = localStorage.getItem(Fy);
      return e === "detailed" || e === "summary" ? e : null;
    } catch {
      return null;
    }
  },
  nw = e => {
    try {
      localStorage.setItem(Fy, e);
    } catch {}
  },
  jt = (e, t) => `${Number(e).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })} ${t}`;
function sw({
  kind: e
}) {
  return s.jsxs("svg", {
    viewBox: "0 0 120 150",
    className: "h-36 w-28",
    "aria-hidden": !0,
    children: [s.jsx("rect", {
      x: "6",
      y: "4",
      width: "108",
      height: "142",
      rx: "8",
      fill: "#fff",
      stroke: "#94a3b8",
      strokeWidth: "3"
    }), s.jsx("rect", {
      x: "16",
      y: "14",
      width: "44",
      height: "8",
      rx: "3",
      fill: "#14306f"
    }), s.jsx("rect", {
      x: "86",
      y: "14",
      width: "18",
      height: "18",
      rx: "3",
      fill: "#94a3b8"
    }), e === "detailed" ? s.jsxs("g", {
      children: [s.jsx("rect", {
        x: "16",
        y: "40",
        width: "88",
        height: "10",
        rx: "2",
        fill: "#14306f"
      }), [56, 70, 84, 98].map(t => s.jsxs("g", {
        children: [s.jsx("rect", {
          x: "16",
          y: t,
          width: "44",
          height: "6",
          rx: "2",
          fill: "#cbd5e1"
        }), s.jsx("rect", {
          x: "68",
          y: t,
          width: "12",
          height: "6",
          rx: "2",
          fill: "#cbd5e1"
        }), s.jsx("rect", {
          x: "86",
          y: t,
          width: "18",
          height: "6",
          rx: "2",
          fill: "#94a3b8"
        })]
      }, t)), s.jsx("rect", {
        x: "62",
        y: "114",
        width: "42",
        height: "8",
        rx: "2",
        fill: "#dbeafe"
      }), s.jsx("rect", {
        x: "62",
        y: "126",
        width: "42",
        height: "9",
        rx: "2",
        fill: "#14306f"
      })]
    }) : s.jsxs("g", {
      children: [s.jsx("rect", {
        x: "16",
        y: "46",
        width: "88",
        height: "14",
        rx: "3",
        fill: "#e3ecff"
      }), s.jsx("rect", {
        x: "16",
        y: "64",
        width: "88",
        height: "14",
        rx: "3",
        fill: "#e3ecff"
      }), s.jsx("rect", {
        x: "16",
        y: "82",
        width: "88",
        height: "14",
        rx: "3",
        fill: "#e3ecff"
      }), s.jsx("rect", {
        x: "62",
        y: "106",
        width: "42",
        height: "9",
        rx: "2",
        fill: "#dbeafe"
      }), s.jsx("rect", {
        x: "62",
        y: "120",
        width: "42",
        height: "12",
        rx: "2",
        fill: "#14306f"
      })]
    })]
  });
}
function Np({
  kind: e,
  last: t,
  onPick: n
}) {
  const r = l(e === "detailed" ? "فاتورة تفصيلية" : "فاتورة مختصرة"),
    i = l(e === "detailed" ? "كل قطعة وكل أجر بسعره" : "المجاميع فقط، بدون أسعار القطع");
  return s.jsxs("button", {
    type: "button",
    onClick: () => n(e),
    className: "relative flex min-h-[260px] flex-1 flex-col items-center justify-center gap-3 rounded-3xl border-4 border-slate-200 bg-white p-5 text-center shadow-card transition hover:-translate-y-1 hover:border-brand active:scale-95",
    children: [t && s.jsx("span", {
      className: "absolute end-3 top-3 rounded-full bg-ok-soft px-3 py-1 text-sm font-bold text-ok",
      children: l("آخر اختيار")
    }), s.jsx(sw, {
      kind: e
    }), s.jsx("span", {
      className: "text-2xl font-extrabold",
      children: r
    }), s.jsx("span", {
      className: "text-base font-semibold text-slate-600",
      children: i
    })]
  });
}
function rw({
  doc: e
}) {
  var p;
  const t = e.labels,
    n = e.invoice.currency,
    r = e.totals,
    [i, a] = w.useState("");
  w.useEffect(() => {
    e.qr ? Br.toDataURL(e.qr, {
      margin: 0,
      width: 120
    }).then(a).catch(() => a("")) : a("");
  }, [e.qr]);
  const o = W({
      queryKey: ["logo"],
      enabled: e.workshop.has_logo,
      queryFn: () => M.get("/api/attachments?owner_type=workshop&owner_id=logo")
    }),
    c = (p = o.data) != null && p.length ? o.data[o.data.length - 1].url : null,
    d = e.invoice.status === "draft" ? t.draft : e.invoice.status === "cancelled" ? t.cancelled : "",
    u = [[t.subtotal, jt(r.subtotal, n), !1]];
  Number(r.discount) && u.push([t.discount, `-${jt(r.discount, n)}`, !1]), (Number(r.tax_amount) || Number(r.tax_rate)) && u.push([`${t.tax} (${Number(r.tax_rate)}%)`, jt(r.tax_amount, n), !1]), u.push([t.grand_total, jt(r.total, n), !0]), Number(r.credit_total) && u.push([t.credit, `-${jt(r.credit_total, n)}`, !1]), u.push([t.paid, jt(r.paid, n), !1]), Number(r.refunded) && u.push([t.refunded, jt(r.refunded, n), !1]), u.push([t.outstanding, jt(r.outstanding, n), !0]);
  const h = [["part", t.parts], ["labor", t.labor], ["other", t.other]];
  return s.jsxs("article", {
    dir: e.rtl ? "rtl" : "ltr",
    lang: e.lang,
    className: "invoice-sheet mx-auto w-full max-w-[794px] space-y-4 bg-white p-6 text-[15px] shadow-card sm:p-10 print:max-w-none print:p-0 print:shadow-none",
    children: [s.jsxs("header", {
      className: "flex items-start justify-between gap-4 border-b-2 border-brand-dark pb-3",
      children: [s.jsxs("div", {
        children: [s.jsx("p", {
          className: "text-2xl font-extrabold text-brand-dark",
          children: e.workshop.name
        }), s.jsx("p", {
          className: "text-sm text-slate-600",
          children: [e.workshop.address, e.workshop.phone, e.workshop.email].filter(Boolean).join(" · ")
        }), e.workshop.tax_number && s.jsxs("p", {
          className: "text-sm text-slate-600",
          children: [t.tax_no, ": ", e.workshop.tax_number]
        })]
      }), c && s.jsx("img", {
        src: c,
        alt: "",
        className: "h-16 w-16 object-contain"
      })]
    }), s.jsxs("div", {
      className: "flex items-start justify-between gap-4",
      children: [s.jsxs("div", {
        children: [s.jsxs("h2", {
          className: "text-xl font-extrabold",
          children: [t.title, " ", s.jsx("span", {
            dir: "ltr",
            children: e.invoice.number
          })]
        }), s.jsx("p", {
          className: "text-sm text-slate-500",
          children: e.mode === "detailed" ? t.detailed_note : t.summary_note
        }), d && s.jsx("p", {
          className: "text-lg font-extrabold text-bad",
          children: d
        }), s.jsxs("p", {
          children: [t.date, ": ", s.jsx("span", {
            dir: "ltr",
            children: e.invoice.date ?? "—"
          })]
        }), s.jsxs("p", {
          children: [t.job, ": ", e.invoice.job_no]
        })]
      }), i && s.jsx("img", {
        src: i,
        alt: "QR",
        className: "h-24 w-24"
      })]
    }), s.jsxs("div", {
      className: "grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 sm:grid-cols-2",
      children: [s.jsxs("div", {
        children: [s.jsx("p", {
          className: "text-xs font-bold text-brand",
          children: t.customer
        }), s.jsx("p", {
          className: "font-bold",
          children: e.customer.name
        }), s.jsxs("p", {
          className: "text-sm",
          children: [t.mobile, ": ", s.jsx("span", {
            dir: "ltr",
            children: e.customer.mobile
          })]
        })]
      }), s.jsxs("div", {
        children: [s.jsx("p", {
          className: "text-xs font-bold text-brand",
          children: t.vehicle
        }), s.jsxs("p", {
          className: "font-bold",
          children: [e.vehicle.make, " ", e.vehicle.model]
        }), s.jsxs("p", {
          className: "text-sm",
          children: [t.plate, ": ", s.jsx("span", {
            dir: "ltr",
            children: e.vehicle.plate ?? "—"
          })]
        }), e.vehicle.vin && s.jsxs("p", {
          className: "text-sm",
          children: [t.vin, ": ", s.jsx("span", {
            dir: "ltr",
            children: e.vehicle.vin
          })]
        }), e.vehicle.mileage != null && s.jsxs("p", {
          className: "text-sm",
          children: [t.mileage, ": ", e.vehicle.mileage.toLocaleString("en-US"), " ", t.km]
        }), e.visit.completed_at && s.jsxs("p", {
          className: "text-sm",
          children: [t.completed, ": ", s.jsx("span", {
            dir: "ltr",
            children: e.visit.completed_at
          })]
        }), e.visit.delivered_at && s.jsxs("p", {
          className: "text-sm",
          children: [t.delivered, ": ", s.jsx("span", {
            dir: "ltr",
            children: e.visit.delivered_at
          })]
        })]
      })]
    }), e.mode === "detailed" ? s.jsx("div", {
      className: "overflow-x-auto print:overflow-visible",
      children: s.jsxs("table", {
        className: "w-full border-collapse text-sm",
        children: [s.jsx("thead", {
          children: s.jsx("tr", {
            className: "bg-brand-dark text-white",
            children: [t.desc, t.part_no, t.qty, t.unit, t.total].map(m => s.jsx("th", {
              className: "p-2 text-center !bg-brand-dark !text-white",
              children: m
            }, m))
          })
        }), s.jsx("tbody", {
          children: h.map(([m, y]) => {
            const j = (e.lines ?? []).filter(v => v.kind === m);
            return j.length ? [s.jsx("tr", {
              children: s.jsx("td", {
                colSpan: 5,
                className: "bg-brand-soft p-2 font-bold text-brand-dark",
                children: y
              })
            }, `h${m}`), ...j.map((v, N) => s.jsxs("tr", {
              className: "border-b border-slate-200",
              children: [s.jsxs("td", {
                className: "p-2",
                children: [v.description, m === "labor" && v.hours ? ` (${Number(v.hours)} ${t.hours})` : ""]
              }), s.jsx("td", {
                className: "p-2 text-center",
                dir: "ltr",
                children: v.part_number ?? ""
              }), s.jsx("td", {
                className: "p-2 text-center",
                dir: "ltr",
                children: Number(v.quantity)
              }), s.jsx("td", {
                className: "p-2 text-center",
                dir: "ltr",
                children: jt(v.unit_price, n)
              }), s.jsx("td", {
                className: "p-2 text-center font-bold",
                dir: "ltr",
                children: jt(v.amount, n)
              })]
            }, `${m}${N}`))] : null;
          })
        })]
      })
    }) : s.jsx("table", {
      className: "w-full border-collapse",
      children: s.jsx("tbody", {
        children: [[t.parts, e.groups.parts], [t.labor, e.groups.labor], [t.other, e.groups.other]].map(([m, y]) => s.jsxs("tr", {
          className: "border border-slate-200",
          children: [s.jsx("td", {
            className: "p-3",
            children: m
          }), s.jsx("td", {
            className: "p-3 text-end font-bold",
            dir: "ltr",
            children: jt(y, n)
          })]
        }, m))
      })
    }), s.jsx("table", {
      className: "ms-auto w-full max-w-sm border-collapse",
      children: s.jsx("tbody", {
        children: u.map(([m, y, j]) => s.jsxs("tr", {
          className: `border-b border-slate-200 ${j ? "bg-brand-soft font-extrabold" : ""}`,
          children: [s.jsx("td", {
            className: "p-2",
            children: m
          }), s.jsx("td", {
            className: "p-2 text-end",
            dir: "ltr",
            children: y
          })]
        }, m))
      })
    }), e.payments.length > 0 && s.jsxs("div", {
      children: [s.jsx("p", {
        className: "font-bold text-brand",
        children: t.payments
      }), s.jsx("ul", {
        className: "max-w-sm text-sm",
        children: e.payments.map((m, y) => s.jsxs("li", {
          className: "flex justify-between border-b border-slate-100 py-1",
          children: [s.jsx("span", {
            dir: "ltr",
            children: m.date
          }), s.jsx("span", {
            children: m.method
          }), s.jsx("span", {
            dir: "ltr",
            children: jt(m.amount, n)
          })]
        }, y))
      })]
    }), s.jsx("p", {
      className: "pt-4 text-center text-sm text-slate-500",
      children: t.thanks
    })]
  });
}
function iw({
  invoiceId: e,
  onClose: t
}) {
  const n = tw(),
    [r, i] = w.useState(null),
    [a, o] = w.useState(Et),
    c = W({
      queryKey: ["invoice-doc", e, r, a],
      enabled: !!r,
      queryFn: () => M.get(`/api/invoices/${e}/document?mode=${r}&lang=${a}`)
    }),
    d = p => {
      nw(p), i(p);
    };
  w.useEffect(() => {
    document.body.classList.add("print-invoice");
    const p = m => m.key === "Escape" && t();
    return window.addEventListener("keydown", p), () => {
      document.body.classList.remove("print-invoice"), window.removeEventListener("keydown", p);
    };
  }, [t]);
  const u = p => `/api/invoices/${e}/pdf?mode=${r}&lang=${a}${p ? "&download=true" : ""}`,
    h = s.jsx("div", {
      role: "dialog",
      "aria-modal": "true",
      "aria-label": l("اختر شكل الفاتورة"),
      className: "invoice-dialog fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 p-3 sm:p-6",
      children: s.jsxs("div", {
        className: "mx-auto max-w-4xl space-y-4 rounded-3xl bg-surface p-4 shadow-2xl sm:p-6 print:max-w-none print:bg-white print:p-0 print:shadow-none",
        children: [s.jsxs("div", {
          className: "no-print flex items-center justify-between gap-3",
          children: [s.jsx("h2", {
            className: "text-2xl font-extrabold",
            children: l(r ? "معاينة الفاتورة" : "اختر شكل الفاتورة")
          }), s.jsx("button", {
            type: "button",
            onClick: t,
            "aria-label": l("إغلاق"),
            className: "flex h-12 w-12 items-center justify-center rounded-xl bg-white shadow",
            children: s.jsx(ia, {
              size: 24
            })
          })]
        }), r ? s.jsxs(s.Fragment, {
          children: [s.jsxs("div", {
            className: "no-print flex flex-wrap items-center gap-2",
            children: [s.jsx(P, {
              kind: "secondary",
              icon: pb,
              onClick: () => i(null),
              children: l("رجوع")
            }), ["detailed", "summary"].map(p => s.jsxs("button", {
              type: "button",
              "aria-pressed": r === p,
              onClick: () => d(p),
              className: `inline-flex min-h-[56px] items-center gap-2 rounded-2xl border-2 px-4 text-lg font-bold ${r === p ? "border-brand bg-brand text-white" : "border-slate-200 bg-white"}`,
              children: [s.jsx($i, {
                size: 22
              }), l(p === "detailed" ? "فاتورة تفصيلية" : "فاتورة مختصرة")]
            }, p)), s.jsx("div", {
              className: "ms-auto flex gap-2",
              role: "group",
              "aria-label": l("لغة الفاتورة"),
              children: ["ar", "en"].map(p => s.jsx("button", {
                type: "button",
                "aria-pressed": a === p,
                onClick: () => o(p),
                className: `min-h-[56px] rounded-2xl border-2 px-4 text-lg font-bold ${a === p ? "border-brand bg-brand-soft text-brand" : "border-slate-200 bg-white"}`,
                children: p === "ar" ? "العربية" : "English"
              }, p))
            })]
          }), c.isLoading ? s.jsx(ie, {}) : c.error ? s.jsx($, {
            message: c.error.message
          }) : c.data && s.jsx(rw, {
            doc: c.data
          }), s.jsxs("div", {
            className: "no-print sticky bottom-0 flex flex-wrap gap-3 rounded-2xl bg-white/90 p-3 shadow backdrop-blur",
            children: [s.jsx(P, {
              icon: fn,
              onClick: () => window.print(),
              children: l("طباعة الفاتورة")
            }), s.jsxs("a", {
              href: u(!0),
              className: "inline-flex min-h-[56px] items-center gap-2 rounded-2xl border-2 border-slate-200 bg-white px-5 text-lg font-bold shadow-sm hover:border-brand/40",
              children: [s.jsx(xu, {
                size: 24
              }), l("تصدير PDF")]
            }), s.jsxs("a", {
              href: u(!1),
              target: "_blank",
              rel: "noreferrer",
              className: "inline-flex min-h-[56px] items-center gap-2 rounded-2xl border-2 border-slate-200 bg-white px-5 text-lg font-bold shadow-sm hover:border-brand/40",
              children: [s.jsx($i, {
                size: 24
              }), l("فتح PDF")]
            })]
          })]
        }) : s.jsxs("div", {
          className: "no-print flex flex-col gap-4 sm:flex-row",
          children: [s.jsx(Np, {
            kind: "detailed",
            last: n === "detailed",
            onPick: d
          }), s.jsx(Np, {
            kind: "summary",
            last: n === "summary",
            onPick: d
          })]
        })]
      })
    });
  return yx.createPortal(h, document.body);
}
const _p = {
  labor: l("أجور"),
  part: l("قطع غيار"),
  other: l("أخرى")
};
// Recovered route component for /invoices/:id; original filename/name unknown.
function aw() {
  var ue, Yt, vt, mn, At, rs, Mu, Tu, Fu, Lu, Du;
  const {
      id: e = ""
    } = Ds(),
    {
      can: t
    } = ce(),
    n = de(),
    r = es(),
    [i, a] = w.useState(!1),
    o = zs(),
    c = Object.fromEntries((((ue = o.data) == null ? void 0 : ue.finance.payment_methods) ?? []).map(K => [K.key, J(K.label)])),
    d = W({
      queryKey: ["invoice", e],
      queryFn: () => M.get(`/api/invoices/${e}`)
    }),
    u = () => {
      n.invalidateQueries({
        queryKey: ["invoice", e]
      }), n.invalidateQueries({
        queryKey: ["invoices"]
      });
    },
    h = w.useRef(os()),
    [p, m] = w.useState({
      amount: "",
      method: "cash",
      reference: ""
    }),
    [y, j] = w.useState({
      kind: "other",
      description: "",
      unit_price: ""
    }),
    [v, N] = w.useState({
      discount: "",
      tax_rate: ""
    }),
    [x, f] = w.useState({
      amount: "",
      reason: ""
    }),
    [g, b] = w.useState(null),
    [k, _] = w.useState(null),
    [S, T] = w.useState(""),
    R = V({
      mutationFn: () => M.post(`/api/invoices/${e}/payments`, {
        amount: p.amount,
        method: p.method,
        reference: p.reference || null
      }, {
        "Idempotency-Key": h.current
      }),
      onSuccess: () => {
        h.current = os(), m({
          amount: "",
          method: "cash",
          reference: ""
        }), u();
      }
    }),
    F = V({
      mutationFn: () => M.post(`/api/invoices/${e}/items`, {
        ...y,
        unit_price: y.unit_price || "0"
      }),
      onSuccess: () => {
        j({
          kind: "other",
          description: "",
          unit_price: ""
        }), u();
      }
    }),
    X = V({
      mutationFn: K => M.del(`/api/invoices/${e}/items/${K}`),
      onSuccess: u
    }),
    te = V({
      mutationFn: () => M.patch(`/api/invoices/${e}`, {
        ...(v.discount !== "" ? {
          discount: v.discount
        } : {}),
        ...(v.tax_rate !== "" ? {
          tax_rate: v.tax_rate
        } : {})
      }),
      onSuccess: u
    }),
    L = V({
      mutationFn: () => M.post(`/api/invoices/${e}/issue`),
      onSuccess: u
    }),
    I = V({
      mutationFn: () => M.del(`/api/invoices/${e}`),
      onSuccess: () => {
        n.invalidateQueries({
          queryKey: ["invoices"]
        }), r("/invoices");
      }
    }),
    Te = V({
      mutationFn: () => M.post(`/api/invoices/${e}/cancel`, {
        reason: S
      }),
      onSuccess: () => {
        T(""), u();
      }
    }),
    st = V({
      mutationFn: () => M.post(`/api/invoices/${e}/credit-notes`, x),
      onSuccess: () => {
        f({
          amount: "",
          reason: ""
        }), u();
      }
    }),
    ut = V({
      mutationFn: () => M.post(`/api/payments/${g.id}/refunds`, {
        amount: g.amount,
        reason: g.reason
      }),
      onSuccess: () => {
        b(null), u();
      }
    }),
    O = V({
      mutationFn: () => M.post(`/api/credit-notes/${k.id}/cancel`, {
        reason: k.reason
      }),
      onSuccess: () => {
        _(null), u();
      }
    });
  if (d.isLoading) return s.jsx(ie, {});
  if (d.error || !d.data) return s.jsx($, {
    message: (Yt = d.error) == null ? void 0 : Yt.message
  });
  const D = d.data,
    G = D.status === "draft",
    U = D.status === "issued";
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("div", {
      className: "no-print flex flex-wrap gap-3",
      children: [s.jsx(P, {
        icon: fn,
        kind: "secondary",
        onClick: () => a(!0),
        children: l("طباعة / حفظ PDF")
      }), s.jsxs(re, {
        to: `/jobs/${D.visit_id}${U ? "#job-delivery" : ""}`,
        className: `inline-flex min-h-[56px] items-center gap-2 rounded-2xl border-2 px-6 text-lg font-bold ${U ? "border-brand bg-brand text-white hover:bg-brand-dark" : "border-slate-300 bg-white"}`,
        children: [U && s.jsx(ed, {
          size: 22,
          "aria-hidden": !0
        }), l(U ? "العودة لأمر الشغل — تسليم العربية" : "أمر الصيانة #"), !U && D.job_no]
      })]
    }), i && s.jsx(iw, {
      invoiceId: D.id,
      onClose: () => a(!1)
    }), s.jsx(qr, {}), s.jsxs(B, {
      children: [s.jsxs("div", {
        className: "flex flex-wrap items-center justify-between gap-3",
        children: [s.jsxs("h1", {
          className: "text-3xl font-extrabold",
          children: [l("فاتورة"), " ", D.number]
        }), s.jsx("div", {
          className: "flex gap-2",
          children: G ? s.jsx(Xe, {
            status: "draft"
          }) : D.status === "cancelled" ? s.jsx(Xe, {
            status: "void"
          }) : s.jsx(Xe, {
            status: D.payment_status
          })
        })]
      }), s.jsxs("p", {
        className: "mt-1 text-lg",
        children: [D.customer.name, " — ", s.jsx("span", {
          dir: "ltr",
          children: D.customer.mobile
        }), " · ", D.vehicle.make, " ", D.vehicle.model, " ", s.jsx("span", {
          dir: "ltr",
          children: D.vehicle.plate
        })]
      }), D.invoice_date && s.jsxs("p", {
        className: "text-slate-600",
        children: [l("تاريخ الفاتورة:"), " ", $e(D.invoice_date)]
      }), D.cancel_reason && s.jsxs("p", {
        className: "font-bold text-bad",
        children: [l("سبب الإلغاء:"), " ", D.cancel_reason]
      }), s.jsx("div", {
        className: "overflow-x-auto print:overflow-visible",
        children: s.jsxs("table", {
          className: "mt-4 w-full text-lg",
          children: [s.jsx("thead", {
            children: s.jsxs("tr", {
              className: "border-b-2 text-slate-500",
              children: [s.jsx("th", {
                className: "p-2 text-start",
                children: l("البند")
              }), s.jsx("th", {
                className: "p-2 text-start",
                children: l("النوع")
              }), s.jsx("th", {
                className: "p-2 text-start",
                children: l("الكمية")
              }), s.jsx("th", {
                className: "p-2 text-start",
                children: l("السعر")
              }), s.jsx("th", {
                className: "p-2 text-start",
                children: l("المبلغ")
              }), s.jsx("th", {
                className: "no-print"
              })]
            })
          }), s.jsx("tbody", {
            children: D.items.map(K => s.jsxs("tr", {
              className: "border-b",
              children: [s.jsx("td", {
                className: "p-2 font-semibold",
                children: J(K.description)
              }), s.jsx("td", {
                className: "p-2",
                children: _p[K.kind]
              }), s.jsx("td", {
                className: "p-2",
                children: K.quantity
              }), s.jsx("td", {
                className: "p-2",
                children: K.unit_price
              }), s.jsx("td", {
                className: "p-2 font-bold",
                children: K.amount
              }), s.jsx("td", {
                className: "no-print p-2",
                children: G && s.jsx("button", {
                  "aria-label": l("حذف البند"),
                  onClick: () => X.mutate(K.id),
                  className: "text-bad",
                  children: "✖"
                })
              })]
            }, K.id))
          })]
        })
      }), s.jsxs("dl", {
        className: "mt-4 ms-auto max-w-xs space-y-1 text-lg",
        children: [s.jsxs("div", {
          className: "flex justify-between",
          children: [s.jsx("dt", {
            children: l("الإجمالي")
          }), s.jsx("dd", {
            children: D.subtotal
          })]
        }), Number(D.discount) > 0 && s.jsxs("div", {
          className: "flex justify-between",
          children: [s.jsx("dt", {
            children: l("الخصم")
          }), s.jsxs("dd", {
            children: ["- ", D.discount]
          })]
        }), Number(D.tax_rate) > 0 && s.jsxs("div", {
          className: "flex justify-between",
          children: [s.jsxs("dt", {
            children: [l("الضريبة ("), D.tax_rate, "%)"]
          }), s.jsx("dd", {
            children: D.tax_amount
          })]
        }), s.jsxs("div", {
          className: "flex justify-between border-t-2 pt-1 text-2xl font-extrabold",
          children: [s.jsx("dt", {
            children: l("الصافي")
          }), s.jsxs("dd", {
            children: [D.total, " ", D.currency]
          })]
        }), Number(D.credit_total) > 0 && s.jsxs("div", {
          className: "flex justify-between",
          children: [s.jsx("dt", {
            children: l("إشعارات دائنة")
          }), s.jsxs("dd", {
            children: ["- ", D.credit_total]
          })]
        }), U && s.jsxs(s.Fragment, {
          children: [s.jsxs("div", {
            className: "flex justify-between text-ok",
            children: [s.jsx("dt", {
              children: l("المدفوع")
            }), s.jsx("dd", {
              children: D.net_paid
            })]
          }), s.jsxs("div", {
            className: "flex justify-between text-xl font-extrabold",
            children: [s.jsx("dt", {
              children: l("المتبقي")
            }), s.jsx("dd", {
              children: D.outstanding
            })]
          })]
        })]
      })]
    }), G && t("billing.write") && s.jsxs(B, {
      title: l("تعديل المسودة"),
      children: [s.jsxs("div", {
        className: "grid gap-3 sm:grid-cols-4",
        children: [s.jsx(E, {
          label: l("النوع"),
          children: s.jsx("select", {
            value: y.kind,
            onChange: K => j({
              ...y,
              kind: K.target.value
            }),
            children: Object.entries(_p).map(([K, rt]) => s.jsx("option", {
              value: K,
              children: rt
            }, K))
          })
        }), s.jsx("div", {
          className: "sm:col-span-2",
          children: s.jsx(E, {
            label: l("الوصف"),
            children: s.jsx("input", {
              value: y.description,
              onChange: K => j({
                ...y,
                description: K.target.value
              })
            })
          })
        }), s.jsx(E, {
          label: l("السعر"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            value: y.unit_price,
            onChange: K => j({
              ...y,
              unit_price: K.target.value
            }),
            dir: "ltr"
          })
        })]
      }), s.jsxs("div", {
        className: "mt-3",
        children: [s.jsx($, {
          message: ((vt = F.error) == null ? void 0 : vt.message) ?? ((mn = X.error) == null ? void 0 : mn.message)
        }), s.jsx(P, {
          icon: ts,
          disabled: y.description.length < 2 || F.isPending,
          onClick: () => F.mutate(),
          children: l("إضافة بند")
        })]
      }), s.jsxs("div", {
        className: "mt-4 grid gap-3 sm:grid-cols-3",
        children: [s.jsx(E, {
          label: l("الخصم (مبلغ)"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            placeholder: D.discount,
            value: v.discount,
            onChange: K => N({
              ...v,
              discount: K.target.value
            }),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("نسبة الضريبة %"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            max: "100",
            placeholder: D.tax_rate,
            value: v.tax_rate,
            onChange: K => N({
              ...v,
              tax_rate: K.target.value
            }),
            dir: "ltr"
          })
        }), s.jsx("div", {
          className: "flex items-end",
          children: s.jsx(P, {
            kind: "secondary",
            disabled: te.isPending || v.discount === "" && v.tax_rate === "",
            onClick: () => te.mutate(),
            children: l("حفظ الخصم والضريبة")
          })
        })]
      }), s.jsxs("div", {
        className: "mt-4 space-y-2",
        children: [s.jsx($, {
          message: ((At = te.error) == null ? void 0 : At.message) ?? ((rs = L.error) == null ? void 0 : rs.message) ?? ((Mu = I.error) == null ? void 0 : Mu.message)
        }), s.jsxs("div", {
          className: "flex flex-wrap gap-3",
          children: [s.jsx(P, {
            icon: wb,
            disabled: L.isPending,
            onClick: () => confirm(l("إصدار الفاتورة؟ بعد الإصدار لا يمكن تعديلها.")) && L.mutate(),
            children: l("إصدار الفاتورة")
          }), s.jsx(P, {
            kind: "danger",
            icon: Or,
            disabled: I.isPending,
            onClick: () => confirm(l("حذف الفاتورة المسودة؟ لا يمكن التراجع.")) && I.mutate(),
            children: l("حذف المسودة")
          })]
        })]
      })]
    }), U && t("billing.write") && Number(D.outstanding) > 0 && s.jsxs(B, {
      title: l("تسجيل دفعة"),
      children: [s.jsxs("div", {
        className: "grid gap-3 sm:grid-cols-3",
        children: [s.jsx(E, {
          label: l("المبلغ"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            value: p.amount,
            onChange: K => m({
              ...p,
              amount: K.target.value
            }),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("طريقة الدفع"),
          children: s.jsx("select", {
            value: p.method,
            onChange: K => m({
              ...p,
              method: K.target.value
            }),
            children: Object.entries(c).map(([K, rt]) => s.jsx("option", {
              value: K,
              children: rt
            }, K))
          })
        }), s.jsx(E, {
          label: l("رقم مرجعي (اختياري)"),
          children: s.jsx("input", {
            value: p.reference,
            onChange: K => m({
              ...p,
              reference: K.target.value
            }),
            dir: "ltr"
          })
        })]
      }), s.jsxs("div", {
        className: "mt-3 flex flex-wrap items-center gap-3",
        children: [s.jsx(P, {
          icon: ju,
          disabled: R.isPending || !(Number(p.amount) > 0),
          onClick: () => R.mutate(),
          children: l("تسجيل الدفعة")
        }), s.jsxs(P, {
          kind: "secondary",
          onClick: () => m({
            ...p,
            amount: D.outstanding
          }),
          children: [l("المتبقي كله ("), D.outstanding, ")"]
        })]
      }), s.jsx("div", {
        className: "mt-2",
        children: s.jsx($, {
          message: (Tu = R.error) == null ? void 0 : Tu.message
        })
      })]
    }), D.payments.length > 0 && s.jsxs(B, {
      title: l("الدفعات"),
      children: [s.jsx("ul", {
        className: "space-y-2",
        children: D.payments.map(K => s.jsxs("li", {
          className: "rounded-xl bg-slate-50 p-3",
          children: [s.jsxs("div", {
            className: "flex flex-wrap items-center justify-between gap-2",
            children: [s.jsxs("span", {
              className: "text-lg font-bold",
              children: [K.amount, " · ", c[K.method] ?? K.method, K.kind === "deposit" && l(" (عربون)"), " ", s.jsx("span", {
                className: "text-sm font-normal text-slate-500",
                children: new Date(K.paid_at).toLocaleString($t)
              })]
            }), t("billing.refund") && Number(K.amount) > Number(K.refunded) && s.jsx(P, {
              kind: "secondary",
              icon: ed,
              onClick: () => b({
                id: K.id,
                amount: "",
                reason: ""
              }),
              children: l("استرداد")
            })]
          }), K.refunds.map(rt => s.jsxs("p", {
            className: "text-wait",
            children: [l("↩ مسترد"), " ", rt.amount, " — ", rt.reason]
          }, rt.id)), (g == null ? void 0 : g.id) === K.id && s.jsxs("div", {
            className: "mt-2 grid gap-2 sm:grid-cols-3",
            children: [s.jsx(E, {
              label: l("المبلغ"),
              children: s.jsx("input", {
                type: "number",
                step: "0.01",
                min: "0",
                value: g.amount,
                onChange: rt => b({
                  ...g,
                  amount: rt.target.value
                }),
                dir: "ltr"
              })
            }), s.jsx(E, {
              label: l("السبب"),
              children: s.jsx("input", {
                value: g.reason,
                onChange: rt => b({
                  ...g,
                  reason: rt.target.value
                })
              })
            }), s.jsx("div", {
              className: "flex items-end",
              children: s.jsx(P, {
                disabled: !(Number(g.amount) > 0) || g.reason.length < 3 || ut.isPending,
                onClick: () => ut.mutate(),
                children: l("تأكيد الاسترداد")
              })
            })]
          })]
        }, K.id))
      }), s.jsx($, {
        message: (Fu = ut.error) == null ? void 0 : Fu.message
      })]
    }), D.credit_notes.length > 0 && s.jsx(B, {
      title: l("إشعارات دائنة"),
      children: s.jsx("ul", {
        className: "space-y-1",
        children: D.credit_notes.map(K => {
          var rt;
          return s.jsxs("li", {
            className: "rounded-xl bg-slate-50 p-3 text-lg",
            children: [s.jsxs("div", {
              className: "flex flex-wrap items-center justify-between gap-3",
              children: [s.jsxs("span", {
                children: [s.jsx("b", {
                  children: K.number
                }), " — ", K.amount, " — ", K.reason, " ", K.cancelled && s.jsxs("b", {
                  className: "text-slate-500",
                  children: ["(", l("ملغى بقيد عكسي"), ")"]
                }), K.is_reversal && s.jsxs("b", {
                  className: "text-slate-500",
                  children: [" (", l("قيد عكس إشعار دائن"), ")"]
                })]
              }), (U || D.status === "cancelled") && t("billing.refund") && !K.cancelled && !K.is_reversal && Number(K.amount) > 0 && s.jsx(P, {
                kind: "secondary",
                onClick: () => {
                  O.reset(), _({
                    id: K.id,
                    reason: ""
                  });
                },
                children: l("إلغاء إشعار الدائن")
              })]
            }), (k == null ? void 0 : k.id) === K.id && s.jsxs("div", {
              className: "mt-3 space-y-3",
              children: [s.jsx(E, {
                label: l("سبب إلغاء إشعار الدائن"),
                children: s.jsx("input", {
                  value: k.reason,
                  onChange: $y => _({
                    ...k,
                    reason: $y.target.value
                  })
                })
              }), s.jsx($, {
                message: (rt = O.error) == null ? void 0 : rt.message
              }), s.jsx(P, {
                disabled: O.isPending || k.reason.trim().length < 3,
                onClick: () => O.mutate(),
                children: l("تأكيد إلغاء إشعار الدائن")
              })]
            })]
          }, K.id);
        })
      })
    }), U && t("billing.refund") && s.jsxs(B, {
      title: l("تصحيح الفاتورة"),
      children: [s.jsxs("div", {
        className: "grid gap-3 sm:grid-cols-3",
        children: [s.jsx(E, {
          label: l("مبلغ الإشعار الدائن"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            value: x.amount,
            onChange: K => f({
              ...x,
              amount: K.target.value
            }),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("السبب"),
          children: s.jsx("input", {
            value: x.reason,
            onChange: K => f({
              ...x,
              reason: K.target.value
            })
          })
        }), s.jsx("div", {
          className: "flex items-end",
          children: s.jsx(P, {
            kind: "secondary",
            disabled: !(Number(x.amount) > 0) || x.reason.length < 3 || st.isPending,
            onClick: () => st.mutate(),
            children: l("إصدار إشعار دائن")
          })
        })]
      }), s.jsx($, {
        message: (Lu = st.error) == null ? void 0 : Lu.message
      }), s.jsxs("div", {
        className: "mt-4 grid gap-3 sm:grid-cols-3",
        children: [s.jsx("div", {
          className: "sm:col-span-2",
          children: s.jsx(E, {
            label: l("سبب إلغاء الفاتورة"),
            children: s.jsx("input", {
              value: S,
              onChange: K => T(K.target.value)
            })
          })
        }), s.jsx("div", {
          className: "flex items-end",
          children: s.jsx(P, {
            kind: "danger",
            icon: mi,
            disabled: S.length < 3 || Te.isPending,
            onClick: () => confirm(l("إلغاء الفاتورة نهائياً؟")) && Te.mutate(),
            children: l("إلغاء الفاتورة")
          })
        })]
      }), s.jsx($, {
        message: (Du = Te.error) == null ? void 0 : Du.message
      })]
    })]
  });
}
const lw = [["", l("الكل")], ["unpaid", l("غير مدفوعة")], ["partial", l("مدفوعة جزئياً")], ["paid", l("مدفوعة")], ["overpaid", l("مدفوع زيادة")]];
// Recovered route component for /invoices; original filename/name unknown.
function ow() {
  var u, h;
  const [e, t] = w.useState(""),
    {
      can: n
    } = ce(),
    r = de(),
    i = V({
      mutationFn: p => M.del(`/api/invoices/${p}`),
      onSuccess: () => r.invalidateQueries({
        queryKey: ["invoices"]
      })
    }),
    [a, o] = w.useState(0),
    c = 50,
    d = W({
      queryKey: ["invoices", e, a],
      queryFn: () => M.get(`/api/invoices${Re({
        payment_status: e,
        status: e ? "issued" : "",
        offset: a,
        limit: c + 1
      })}`)
    });
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(Oi, {
        size: 36
      }), l("الفواتير")]
    }), s.jsx("div", {
      className: "flex flex-wrap gap-2",
      children: lw.map(([p, m]) => s.jsx("button", {
        onClick: () => {
          t(p), o(0);
        },
        className: `min-h-[48px] rounded-xl px-4 font-bold ${e === p ? "bg-brand text-white" : "bg-white"}`,
        children: m
      }, p))
    }), d.isLoading ? s.jsx(ie, {}) : d.error ? s.jsx($, {
      message: d.error.message
    }) : (u = d.data) != null && u.length ? s.jsxs("div", {
      className: "space-y-3",
      children: [s.jsx($, {
        message: (h = i.error) == null ? void 0 : h.message
      }), d.data.slice(0, c).map(p => s.jsxs("div", {
        className: "flex items-stretch gap-2",
        children: [s.jsxs(re, {
          to: `/invoices/${p.id}`,
          className: "flex flex-1 flex-wrap items-center justify-between gap-3 rounded-2xl bg-white p-4 shadow hover:shadow-lg",
          children: [s.jsxs("div", {
            children: [s.jsx("p", {
              className: "text-xl font-extrabold",
              children: p.number
            }), s.jsxs("p", {
              className: "text-slate-600",
              children: [p.customer.name, " · ", s.jsx("span", {
                dir: "ltr",
                children: p.vehicle.plate
              })]
            })]
          }), s.jsx(Xe, {
            status: p.status === "issued" ? p.payment_status : p.status === "cancelled" ? "void" : "draft"
          }), s.jsxs("div", {
            className: "text-end",
            children: [s.jsx("p", {
              className: "text-xl font-extrabold",
              children: p.total
            }), p.status === "issued" && Number(p.outstanding) !== 0 && s.jsxs("p", {
              className: "text-bad",
              children: [l("المتبقي"), " ", p.outstanding]
            })]
          })]
        }), p.status === "draft" && n("billing.write") && s.jsx("button", {
          type: "button",
          "aria-label": l("حذف المسودة"),
          disabled: i.isPending,
          onClick: () => confirm(l("حذف الفاتورة المسودة؟ لا يمكن التراجع.")) && i.mutate(p.id),
          className: "flex w-14 items-center justify-center rounded-2xl bg-bad-soft text-bad shadow hover:brightness-95",
          children: s.jsx(Or, {
            size: 24
          })
        })]
      }, p.id))]
    }) : s.jsx(Ie, {
      icon: Oi,
      text: l("مفيش فواتير")
    }), s.jsxs("div", {
      className: "flex items-center justify-between gap-3",
      children: [s.jsx(P, {
        kind: "secondary",
        disabled: a === 0 || d.isFetching,
        onClick: () => o(Math.max(0, a - c)),
        children: l("السابق")
      }), s.jsx("span", {
        children: Math.floor(a / c) + 1
      }), s.jsx(P, {
        kind: "secondary",
        disabled: d.isFetching || !d.data || d.data.length <= c,
        onClick: () => o(a + c),
        children: l("التالي")
      })]
    })]
  });
}
function cw() {
  const {
      user: e,
      can: t
    } = ce(),
    n = W({
      queryKey: ["board"],
      enabled: t("visits.read"),
      queryFn: () => M.get("/api/board"),
      refetchInterval: 3e4
    }),
    r = n.data ?? [],
    i = r.filter(c => c.status === "ready").length,
    a = r.filter(c => c.status.startsWith("waiting")).length,
    o = [{
      icon: ns,
      label: l("في الورشة الآن"),
      value: r.length,
      cls: "bg-brand-soft text-brand",
      to: "/board"
    }, {
      icon: Le,
      label: l("في الانتظار"),
      value: a,
      cls: "bg-wait-soft text-wait",
      to: "/board?group=waiting"
    }, {
      icon: Ke,
      label: l("جاهزة للتسليم"),
      value: i,
      cls: "bg-ok-soft text-ok",
      to: "/board?group=ready"
    }];
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      children: [l("أهلاً"), " ", e == null ? void 0 : e.full_name, " 👋"]
    }), t("visits.read") && s.jsx("div", {
      className: "grid grid-cols-3 gap-3",
      "aria-label": l("في الورشة الآن"),
      children: o.map(({
        icon: c,
        label: d,
        value: u,
        cls: h,
        to: p
      }) => s.jsxs(re, {
        to: p,
        className: "group relative flex flex-col items-center gap-1 rounded-2xl border border-slate-200 bg-white p-3 text-center shadow-card transition hover:-translate-y-0.5 hover:border-brand/40 hover:shadow-lift active:scale-95 sm:flex-row sm:gap-3 sm:text-start",
        children: [s.jsx("span", {
          className: `flex h-12 w-12 items-center justify-center rounded-xl ${h}`,
          children: s.jsx(c, {
            size: 26,
            "aria-hidden": !0
          })
        }), s.jsxs("span", {
          children: [s.jsx("b", {
            className: "block text-3xl font-extrabold leading-none",
            children: n.isLoading ? "…" : u
          }), s.jsx("span", {
            className: "text-sm font-semibold text-slate-600",
            children: d
          })]
        }), s.jsx(Ii, {
          size: 20,
          "aria-hidden": !0,
          className: "absolute end-3 top-3 hidden text-slate-300 transition group-hover:text-brand rtl:rotate-180 sm:block"
        })]
      }, d))
    }), s.jsx(xy, {}), s.jsxs("div", {
      className: "grid grid-cols-1 gap-4 sm:grid-cols-3",
      children: [t("visits.write") && s.jsx(Mo, {
        to: "/reception",
        icon: mu,
        label: l("استقبال عربية"),
        tone: "ok"
      }), t("visits.read") && s.jsx(Mo, {
        to: "/board",
        icon: Vl,
        label: l("متابعة التصليح"),
        tone: "wait"
      }), t("vehicles.read") && s.jsx(Mo, {
        to: "/search",
        icon: Wn,
        label: l("بحث عن عربية")
      })]
    }), s.jsx("h2", {
      className: "pt-2 text-xl font-extrabold text-slate-700",
      children: l("كل الأقسام")
    }), s.jsxs("div", {
      className: "grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3",
      children: [t("vehicles.write") && s.jsx(We, {
        to: "/vehicles?new=1",
        icon: Bx,
        label: l("تسجيل عربية جديدة"),
        tone: "ok"
      }), t("vehicles.read") && s.jsx(We, {
        to: "/vehicles",
        icon: un,
        label: l("العربيات")
      }), t("customers.write") && s.jsx(We, {
        to: "/customers?new=1",
        icon: vu,
        label: l("عميل جديد"),
        tone: "ok"
      }), t("customers.read") && s.jsx(We, {
        to: "/customers",
        icon: Ms,
        label: l("العملاء")
      }), t("visits.read") && s.jsx(We, {
        to: "/suppliers",
        icon: Wl,
        label: l("قطع الغيار")
      }), t("visits.read") && s.jsx(We, {
        to: "/reminders",
        icon: Qn,
        label: l("تذكيرات الصيانة"),
        tone: "wait"
      }), t("billing.read") && s.jsx(We, {
        to: "/invoices",
        icon: Oi,
        label: l("الفواتير"),
        tone: "ok"
      }), t("expenses.read") && s.jsx(We, {
        to: "/expenses",
        icon: yl,
        label: l("المصروفات"),
        tone: "wait"
      }), t("reports.financial") && s.jsx(We, {
        to: "/finance",
        icon: pu,
        label: l("الحسابات")
      }), t("visits.read") && s.jsx(We, {
        to: "/reports",
        icon: Kl,
        label: l("التقارير")
      }), t("technicians.manage") && s.jsx(We, {
        to: "/technicians",
        icon: wl,
        label: l("الفنيين"),
        tone: "idle"
      }), t("users.manage") && s.jsx(We, {
        to: "/users",
        icon: sy,
        label: l("المستخدمين"),
        tone: "idle"
      }), t("settings.manage") && s.jsx(We, {
        to: "/settings",
        icon: ra,
        label: l("الإعدادات"),
        tone: "idle"
      }), t("audit.read") && s.jsx(We, {
        to: "/audit",
        icon: xi,
        label: l("سجل الورشة"),
        tone: "idle"
      }), t("backup.manage") && s.jsx(We, {
        to: "/backup",
        icon: bl,
        label: l("النسخ الاحتياطي"),
        tone: "idle"
      })]
    })]
  });
}
async function dw(e) {
  if (!e.type.startsWith("image/") || e.type === "image/gif" || e.size < 6e5) return e;
  try {
    const t = await createImageBitmap(e),
      n = Math.min(1, 1600 / Math.max(t.width, t.height)),
      r = document.createElement("canvas");
    r.width = Math.round(t.width * n), r.height = Math.round(t.height * n), r.getContext("2d").drawImage(t, 0, 0, r.width, r.height);
    const i = await new Promise(a => r.toBlob(a, "image/jpeg", .85));
    return i && i.size < e.size ? new File([i], e.name.replace(/\.\w+$/, "") + ".jpg", {
      type: "image/jpeg"
    }) : e;
  } catch {
    return e;
  }
}
async function Pu(e, t, n, r = "photo", i) {
  const a = await dw(n),
    o = new FormData();
  o.append("owner_type", e), o.append("owner_id", t), o.append("kind", r), i && o.append("point", i), o.append("file", a);
  const c = (await M.get("/api/auth/me")).csrf_token,
    d = await fetch("/api/attachments", {
      method: "POST",
      body: o,
      credentials: "same-origin",
      headers: {
        "X-CSRF-Token": c
      }
    }),
    u = await d.json().catch(() => ({}));
  if (!d.ok) throw new Sr(d.status, u.error ?? "error", u.message ?? l("فشل رفع الملف"));
  return u;
}
function Ru({
  ownerType: e,
  ownerId: t,
  title: n = l("الصور والمستندات"),
  canWrite: r
}) {
  var v, N, x, f;
  const {
      can: i
    } = ce(),
    a = de(),
    o = w.useRef(null),
    c = w.useRef(null),
    [d, u] = w.useState(null),
    h = ["attachments", e, t],
    p = W({
      queryKey: h,
      queryFn: () => M.get(`/api/attachments?owner_type=${e}&owner_id=${t}`)
    }),
    m = V({
      mutationFn: async g => {
        for (const b of Array.from(g.files)) await Pu(e, t, b, g.kind);
      },
      onSuccess: () => a.invalidateQueries({
        queryKey: h
      })
    }),
    y = V({
      mutationFn: g => {
        const b = prompt(l("سبب حذف الملف؟"));
        if (!b || b.trim().length < 3) throw new Error("cancel");
        return M.post(`/api/attachments/${g.id}/remove`, {
          reason: b.trim()
        });
      },
      onSuccess: () => a.invalidateQueries({
        queryKey: h
      })
    }),
    j = r ?? i(e === "vehicle" ? "vehicles.write" : "visits.write");
  return s.jsxs(B, {
    title: `${n} (${((v = p.data) == null ? void 0 : v.length) ?? 0})`,
    children: [s.jsxs("div", {
      className: "flex flex-wrap gap-3",
      children: [(N = p.data) == null ? void 0 : N.map(g => s.jsxs("div", {
        className: "relative",
        children: [g.mime.startsWith("image/") ? s.jsx("button", {
          onClick: () => u(g),
          "aria-label": g.name,
          children: s.jsx("img", {
            src: g.url,
            alt: g.point ?? g.name,
            className: "h-28 w-28 rounded-2xl border-2 border-slate-200 object-cover"
          })
        }) : s.jsxs("a", {
          href: g.url,
          target: "_blank",
          rel: "noreferrer",
          className: "flex h-28 w-28 flex-col items-center justify-center gap-1 rounded-2xl border-2 border-slate-200 bg-slate-50 p-1 text-center text-xs font-bold",
          children: [s.jsx($i, {
            size: 32
          }), g.name]
        }), g.point && s.jsx("span", {
          className: "absolute bottom-1 start-1 rounded bg-black/60 px-1 text-xs text-white",
          children: g.point
        }), j && s.jsx("button", {
          "aria-label": l("حذف"),
          onClick: () => y.mutate(g),
          className: "absolute -end-2 -top-2 rounded-full bg-white p-1 text-bad shadow",
          children: s.jsx(Or, {
            size: 16
          })
        })]
      }, g.id)), !((x = p.data) != null && x.length) && s.jsx("p", {
        className: "text-slate-500",
        children: l("لا توجد ملفات")
      })]
    }), j && s.jsxs("div", {
      className: "mt-3 flex flex-wrap gap-3",
      children: [s.jsx("input", {
        ref: o,
        type: "file",
        accept: "image/*",
        capture: "environment",
        multiple: !0,
        hidden: !0,
        onChange: g => g.target.files && m.mutate({
          files: g.target.files,
          kind: "photo"
        })
      }), s.jsx("input", {
        ref: c,
        type: "file",
        accept: "application/pdf,image/*",
        hidden: !0,
        onChange: g => g.target.files && m.mutate({
          files: g.target.files,
          kind: "document"
        })
      }), s.jsxs("button", {
        type: "button",
        onClick: () => {
          var g;
          return (g = o.current) == null ? void 0 : g.click();
        },
        disabled: m.isPending,
        className: "inline-flex min-h-[56px] items-center gap-2 rounded-2xl bg-brand px-6 text-xl font-bold text-white disabled:opacity-50",
        children: [s.jsx(xb, {
          size: 24
        }), m.isPending ? l("جاري الرفع…") : l("تصوير / إضافة صورة")]
      }), s.jsxs("button", {
        type: "button",
        onClick: () => {
          var g;
          return (g = c.current) == null ? void 0 : g.click();
        },
        disabled: m.isPending,
        className: "inline-flex min-h-[56px] items-center gap-2 rounded-2xl border-2 border-slate-300 bg-white px-6 text-xl font-bold disabled:opacity-50",
        children: [s.jsx($i, {
          size: 24
        }), l("إضافة مستند (PDF)")]
      })]
    }), s.jsx("div", {
      className: "mt-2",
      children: s.jsx($, {
        message: ((f = m.error) == null ? void 0 : f.message) ?? (y.error && y.error.message !== "cancel" ? y.error.message : void 0)
      })
    }), d && s.jsx("div", {
      role: "dialog",
      "aria-label": l("عرض الصورة"),
      onClick: () => u(null),
      className: "fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4",
      children: s.jsx("img", {
        src: d.url,
        alt: d.name,
        className: "max-h-full max-w-full rounded-2xl"
      })
    })]
  });
}
function Ly(e, t, n) {
  var o;
  const r = {
    received: {
      target: "job-technicians",
      action: l("تعيين الفني ومراجعة الشكوى"),
      owner: l("موظف استقبال")
    },
    inspection_pending: {
      target: "job-inspections",
      action: l("تسجيل نتائج الفحص عند الحاجة"),
      owner: l("الفني المسؤول")
    },
    under_inspection: {
      target: "job-inspections",
      action: l("تسجيل نتائج الفحص عند الحاجة"),
      owner: l("الفني المسؤول")
    },
    waiting_quotation: {
      target: "job-quotes",
      action: l("مراجعة عرض السعر وإرساله للعميل"),
      owner: l("موظف استقبال")
    },
    waiting_approval: {
      target: "job-quotes",
      action: l("تسجيل قرار العميل على عرض السعر"),
      owner: l("موظف استقبال")
    },
    waiting_parts: {
      target: "job-parts",
      action: l("متابعة القطع المطلوبة وتسجيل وصولها"),
      owner: l("مسؤول قطع الغيار")
    },
    in_progress: {
      target: "job-operations",
      action: l("تحديث تقدم أعمال الإصلاح"),
      owner: l("الفني المسؤول")
    },
    quality_check: {
      target: "job-quality",
      action: l("مراجعة قائمة الجودة واعتماد النتيجة"),
      owner: l("مسؤول الجودة")
    },
    ready: {
      target: "job-delivery",
      action: l("مراجعة متطلبات التسليم والفاتورة والرصيد"),
      owner: l("الاستقبال والحسابات")
    },
    delivered: {
      target: "job-history",
      action: l("مراجعة سجل الأمر المكتمل"),
      owner: l("موظف استقبال")
    },
    cancelled: {
      target: "job-history",
      action: l("مراجعة سبب الإلغاء وسجل الأمر"),
      owner: l("مدير الورشة")
    }
  };
  if (["received", "inspection_pending", "under_inspection"].includes(e.status) && (o = e.operations) != null && o.some(c => c.status === "pending" || c.status === "in_progress")) return r.in_progress;
  const i = n == null ? void 0 : n.blockers.some(({
    code: c
  }) => ["no_invoice", "draft_invoice", "unbilled_items", "unpaid"].includes(c));
  return e.status === "ready" && t("billing.read") && (i || !t("delivery.write")) ? {
    target: "job-invoices",
    action: l("مراجعة الفاتورة والرصيد المتبقي"),
    owner: l("الحسابات")
  } : r[e.status] ?? r.received;
}
function Cp({
  job: e,
  can: t,
  readiness: n,
  compact: r = !1
}) {
  const i = Ly(e, t, n),
    a = {
      "job-technicians": "visits.write",
      "job-inspections": "visits.write",
      "job-quotes": "visits.read",
      "job-parts": "visits.read",
      "job-operations": "visits.read",
      "job-invoices": "billing.read",
      "job-history": "visits.read",
      "job-quality": "qc.write",
      "job-delivery": "delivery.write"
    },
    o = e.operations.filter(d => d.status !== "cancelled"),
    c = o.filter(d => d.status === "done").length;
  return r ? s.jsxs("div", {
    className: "flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-2 pb-2 text-sm",
    children: [s.jsx(Pr, {
      status: e.status
    }), s.jsx("span", {
      className: "hidden min-w-0 flex-1 truncate text-slate-600 sm:block",
      children: i.action
    }), t(a[i.target]) && s.jsxs("a", {
      href: `#${i.target}`,
      className: "inline-flex min-h-[40px] items-center gap-1 rounded-lg px-3 font-bold text-brand hover:bg-brand-soft",
      children: [l("انتقل للخطوة"), s.jsx(cp, {
        size: 16
      })]
    })]
  }) : s.jsxs(B, {
    title: l("ملخص رحلة العربية"),
    children: [s.jsxs("div", {
      className: "flex flex-wrap items-center justify-between gap-3",
      children: [s.jsx(Pr, {
        status: e.status
      }), s.jsxs("a", {
        href: "#job-history",
        className: "inline-flex min-h-[44px] items-center gap-2 font-bold text-brand underline",
        children: [s.jsx(fu, {
          size: 18
        }), l("سجل الحالات")]
      })]
    }), s.jsxs("div", {
      className: "mt-4 grid gap-4 lg:grid-cols-[1.5fr_1fr]",
      children: [s.jsxs("div", {
        className: "rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50 to-indigo-50 p-5",
        children: [s.jsx("p", {
          className: "text-sm font-bold text-brand",
          children: l("الخطوة التالية")
        }), s.jsx("h3", {
          className: "mt-1 text-xl font-extrabold",
          children: i.action
        }), s.jsxs("p", {
          className: "mt-2 text-sm text-slate-600",
          children: [l("المسؤول عن الخطوة:"), " ", i.owner]
        }), t(a[i.target]) ? s.jsxs("a", {
          href: `#${i.target}`,
          className: "mt-3 inline-flex min-h-[48px] items-center gap-2 rounded-xl bg-brand px-5 py-2 font-bold text-white shadow-sm transition-colors hover:bg-brand-dark",
          children: [s.jsx(cp, {
            size: 18
          }), l("انتقل للخطوة")]
        }) : s.jsx("p", {
          className: "mt-3 text-sm text-slate-600",
          children: l("تابع هذه الخطوة مع المسؤول الموضح.")
        })]
      }), s.jsxs("div", {
        className: "rounded-2xl border border-slate-200 bg-slate-50/70 p-5",
        children: [s.jsxs("p", {
          className: "flex items-center gap-2 font-bold",
          children: [s.jsx(Ms, {
            size: 18
          }), l("الفنيون المعيّنون")]
        }), s.jsx("p", {
          className: "mt-1 break-words text-sm text-slate-600",
          children: e.technicians.length ? e.technicians.map(d => d.name).join("، ") : l("لم يتم تعيين فني بعد")
        }), o.length > 0 && s.jsxs("div", {
          className: "mt-4",
          children: [s.jsx("p", {
            className: "text-sm font-bold",
            children: Z("أعمال مكتملة: {0} من {1}", c, o.length)
          }), s.jsx("progress", {
            "aria-label": l("تقدم أعمال الإصلاح"),
            value: c,
            max: o.length,
            className: "mt-2 h-2 w-full accent-blue-600"
          })]
        }), s.jsx("p", {
          className: "mt-3 text-xs text-slate-500",
          children: l("اكتمال الأعمال لا يغني عن اعتماد الجودة وتأكيد التسليم.")
        })]
      })]
    })]
  });
}
function uw({
  sections: e,
  children: t,
  initial: n,
  summary: r
}) {
  var v, N;
  const i = e.some(x => x.id === n) ? n : (v = e[0]) == null ? void 0 : v.id,
    [a, o] = w.useState(() => window.location.hash.slice(1) || i),
    c = x => e.find(f => {
      var g;
      return f.id === x || ((g = f.anchors) == null ? void 0 : g.includes(x));
    }),
    d = ((N = c(a)) == null ? void 0 : N.id) ?? i,
    u = e.findIndex(x => x.id === d),
    h = e[u - 1],
    p = e[u + 1],
    m = w.useRef(null);
  w.useEffect(() => {
    const x = () => o(window.location.hash.slice(1) || i);
    return window.addEventListener("hashchange", x), window.addEventListener("popstate", x), () => {
      window.removeEventListener("hashchange", x), window.removeEventListener("popstate", x);
    };
  }, [i]), w.useEffect(() => {
    if (a === d || !c(a)) return;
    const x = requestAnimationFrame(() => {
      var f, g;
      return (g = (f = document.getElementById(a)) == null ? void 0 : f.scrollIntoView) == null ? void 0 : g.call(f, {
        block: "start"
      });
    });
    return () => cancelAnimationFrame(x);
  }, [a, d]);
  function y(x) {
    c(x) && (window.location.hash !== `#${x}` && window.history.pushState(window.history.state, "", `#${x}`), o(x));
  }
  function j(x) {
    y(x), requestAnimationFrame(() => {
      var b, k, _;
      const f = document.getElementById(x);
      f == null || f.focus({
        preventScroll: !0
      }), (k = f == null ? void 0 : f.scrollIntoView) == null || k.call(f, {
        block: "start",
        behavior: (b = window.matchMedia) != null && b.call(window, "(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
      });
      const g = document.getElementById(`tab-${x}`);
      (_ = g == null ? void 0 : g.scrollIntoView) == null || _.call(g, {
        block: "nearest",
        inline: "nearest"
      });
    });
  }
  return s.jsxs("div", {
    ref: m,
    className: "space-y-5",
    onClickCapture: x => {
      const f = x.target.closest('a[href^="#"]');
      if (!f || x.ctrlKey || x.metaKey || x.shiftKey || x.altKey || x.button !== 0) return;
      const g = f.hash.slice(1);
      c(g) && (x.preventDefault(), y(g), requestAnimationFrame(() => {
        var _, S, T;
        const b = g !== ((_ = c(g)) == null ? void 0 : _.id),
          k = b ? document.getElementById(g) : document.getElementById(`tab-${g}`);
        k == null || k.focus({
          preventScroll: !0
        }), (T = k == null ? void 0 : k.scrollIntoView) == null || T.call(k, {
          block: b ? "start" : "nearest",
          inline: "nearest",
          behavior: (S = window.matchMedia) != null && S.call(window, "(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
        });
      }));
    },
    children: [t, s.jsxs("div", {
      className: "job-tabs no-print rounded-2xl border border-slate-200 bg-white/95 p-2 shadow-card backdrop-blur",
      children: [r, s.jsx("div", {
        role: "tablist",
        "aria-label": l("أقسام أمر الشغل"),
        className: "flex gap-2 overflow-x-auto p-1",
        children: e.map((x, f) => s.jsxs("button", {
          type: "button",
          role: "tab",
          id: `tab-${x.id}`,
          "aria-controls": x.id,
          "aria-selected": d === x.id,
          tabIndex: d === x.id ? 0 : -1,
          onClick: () => y(x.id),
          onKeyDown: g => {
            var _, S;
            let b = f;
            const k = document.documentElement.dir === "rtl";
            if (g.key === "Home") b = 0;else if (g.key === "End") b = e.length - 1;else if (g.key === "ArrowRight") b = (f + (k ? -1 : 1) + e.length) % e.length;else if (g.key === "ArrowLeft") b = (f + (k ? 1 : -1) + e.length) % e.length;else return;
            g.preventDefault(), y(e[b].id), (S = (_ = m.current) == null ? void 0 : _.querySelector(`#tab-${e[b].id}`)) == null || S.focus();
          },
          className: `flex min-h-[48px] shrink-0 items-center gap-2 rounded-xl px-4 text-sm font-bold transition-colors ${d === x.id ? "bg-brand text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"}`,
          children: [x.label, x.count !== void 0 && s.jsx("span", {
            className: `rounded-lg px-2 py-0.5 text-xs ${d === x.id ? "bg-white/20" : "bg-slate-100"}`,
            children: x.count
          })]
        }, x.id))
      })]
    }), e.map(x => s.jsx("div", {
      id: x.id,
      role: "tabpanel",
      "aria-labelledby": `tab-${x.id}`,
      tabIndex: 0,
      hidden: d !== x.id,
      className: "job-tab-panel space-y-5 scroll-mt-64",
      children: x.content
    }, x.id)), s.jsxs("nav", {
      "aria-label": l("التنقل بين أقسام أمر الشغل"),
      className: "no-print flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4",
      children: [s.jsx("div", {
        children: h && s.jsx("button", {
          type: "button",
          onClick: () => j(h.id),
          className: "min-h-[48px] rounded-xl border border-slate-300 px-4 py-2 font-bold text-slate-600 hover:bg-slate-50",
          children: Z("السابق: {0}", h.label)
        })
      }), p && s.jsx("button", {
        type: "button",
        onClick: () => j(p.id),
        className: "min-h-[48px] rounded-xl bg-brand px-4 py-2 font-bold text-white hover:bg-brand-dark",
        children: Z("التالي: {0}", p.label)
      })]
    })]
  });
}
function Sp({
  job: e,
  view: t = "all"
}) {
  var st, ut, O, D, G;
  const {
      can: n
    } = ce(),
    r = de(),
    i = e.status === "delivered",
    a = i || e.status === "cancelled",
    o = W({
      queryKey: ["readiness", e.id, e.status, e.version],
      enabled: !a,
      queryFn: () => M.get(`/api/jobs/${e.id}/delivery-readiness`)
    }),
    c = () => {
      r.invalidateQueries({
        queryKey: ["job", e.id]
      }), r.invalidateQueries({
        queryKey: ["readiness", e.id]
      }), r.invalidateQueries({
        queryKey: ["board"]
      }), r.invalidateQueries({
        queryKey: ["job-invoices", e.id]
      });
    },
    [d, u] = w.useState({
      repairs: !1,
      parts: !1,
      road: !1,
      notes: "",
      override: ""
    }),
    [h, p] = w.useState(null),
    [m, y] = w.useState(null),
    [j, v] = w.useState({
      final_mileage: ((st = e.mileage) == null ? void 0 : st.toString()) ?? "",
      final_condition: "",
      ack_name: e.customer.name,
      override_reason: ""
    }),
    N = V({
      mutationFn: U => M.post(`/api/jobs/${e.id}/quality-check`, {
        result: U,
        repairs_verified: d.repairs,
        parts_verified: d.parts,
        road_test_ok: d.road,
        notes: d.notes || null,
        override_reason: d.override || null
      }),
      onSuccess: (U, ue) => {
        y({
          jobId: e.id,
          version: e.version,
          result: ue,
          notes: d.notes.trim()
        }), p(null), u({
          repairs: !1,
          parts: !1,
          road: !1,
          notes: "",
          override: ""
        }), c();
      }
    }),
    x = V({
      mutationFn: () => M.post(`/api/jobs/${e.id}/deliver`, {
        ...j,
        final_mileage: Number(j.final_mileage),
        override_reason: j.override_reason || null,
        final_condition: j.final_condition || null
      }),
      onSuccess: c
    });
  if (i) return s.jsxs(B, {
    title: l("التسليم"),
    children: [s.jsx("p", {
      className: "mb-3 text-xl font-bold text-ok",
      children: l("✔ تم تسليم العربية")
    }), s.jsx(re, {
      to: `/jobs/${e.id}/delivery-report`,
      className: "inline-flex min-h-[56px] items-center rounded-2xl bg-brand px-6 text-xl font-bold text-white",
      children: l("تقرير التسليم")
    })]
  });
  if (a) return null;
  const f = ((ut = o.data) == null ? void 0 : ut.blockers) ?? [],
    g = f.some(U => ["no_invoice", "draft_invoice", "unbilled_items"].includes(U.code)),
    b = f.filter(U => U.code === "operations_unfinished" || U.code === "parts_not_installed"),
    k = [d.repairs, d.parts, d.road].filter(Boolean).length,
    _ = (O = o.data) == null ? void 0 : O.latest_quality_check,
    S = (m == null ? void 0 : m.jobId) === e.id && (m.version === e.version || !o.data && e.status === (m.result === "passed" ? "ready" : "in_progress")) ? m : null,
    T = _ && (_.result === "passed" && e.status === "ready" || _.result === "failed" && e.status === "in_progress") ? _ : null,
    R = h !== e.id ? S ?? T : null,
    F = (R == null ? void 0 : R.result) === "passed",
    X = !o.isFetching && (_ == null ? void 0 : _.result) === (R == null ? void 0 : R.result) ? _ == null ? void 0 : _.checked_at : void 0,
    te = f.filter(U => U.code !== "quality_not_passed" && U.code !== "not_ready"),
    L = !o.data || o.isFetching || o.isError,
    I = N.isPending || L || k !== 3 || b.length > 0 && !(n("jobs.override") && d.override.trim()),
    Te = (U, ue, Yt, vt) => s.jsxs("label", {
      className: `flex cursor-pointer items-start gap-3 rounded-2xl border-2 p-4 transition focus-within:ring-2 focus-within:ring-brand ${d[U] ? "border-ok bg-ok-soft" : "border-slate-200 bg-white hover:border-brand"}`,
      children: [s.jsx("input", {
        type: "checkbox",
        "aria-label": ue,
        disabled: N.isPending,
        className: "!mt-1 !h-6 !w-6 shrink-0 accent-emerald-700",
        checked: d[U],
        onChange: mn => u({
          ...d,
          [U]: mn.target.checked
        })
      }), s.jsxs("span", {
        className: "min-w-0",
        children: [s.jsx("span", {
          className: `mb-1 block text-xs font-bold ${d[U] ? "text-ok" : "text-slate-500"}`,
          children: d[U] ? l("تمت المراجعة") : Z("خطوة {0}", vt)
        }), s.jsx("span", {
          className: "block text-base font-extrabold",
          children: ue
        }), s.jsx("span", {
          className: "mt-1 block text-sm text-slate-600",
          children: Yt
        })]
      })]
    });
  return s.jsxs(s.Fragment, {
    children: [t !== "delivery" && n("qc.write") && s.jsx(B, {
      title: l("فحص الجودة"),
      children: R ? s.jsxs(s.Fragment, {
        children: [s.jsxs("div", {
          className: `rounded-2xl border p-5 ${F ? "border-emerald-200 bg-ok-soft" : "border-red-200 bg-bad-soft"}`,
          children: [s.jsxs("div", {
            className: "flex items-start gap-3",
            children: [F ? s.jsx(rr, {
              className: "shrink-0 text-ok",
              size: 32,
              "aria-hidden": !0
            }) : s.jsx(at, {
              className: "shrink-0 text-bad",
              size: 32,
              "aria-hidden": !0
            }), s.jsxs("div", {
              children: [s.jsx("h3", {
                className: `text-xl font-extrabold ${F ? "text-ok" : "text-bad"}`,
                children: l(F ? "تم اجتياز فحص الجودة" : "لم تجتز العربية فحص الجودة")
              }), s.jsx("p", {
                role: "status",
                className: "mt-1 font-semibold",
                children: l(F ? "تم اعتماد الجودة. العربية جاهزة لخطوة التسليم." : "تم تسجيل الرفض وإعادة العربية للتصليح.")
              }), X && s.jsxs("p", {
                className: "mt-2 text-sm text-slate-600",
                children: [l("وقت تسجيل الفحص:"), " ", s.jsx("time", {
                  dateTime: X,
                  children: new Date(X).toLocaleString($t)
                })]
              })]
            })]
          }), F && s.jsx("ul", {
            className: "mt-4 grid gap-2 sm:grid-cols-3",
            children: [l("تمت مراجعة الأعمال"), l("تمت مراجعة القطع المركّبة"), l("تمت تجربة العربية")].map(U => s.jsxs("li", {
              className: "flex items-center gap-2 rounded-xl bg-white px-3 py-2 text-sm font-bold text-ok",
              children: [s.jsx(Ke, {
                size: 18,
                className: "shrink-0",
                "aria-hidden": !0
              }), U]
            }, U))
          }), R.notes && s.jsxs("div", {
            className: "mt-4 rounded-xl bg-white p-3",
            children: [s.jsx("p", {
              className: "text-sm font-bold",
              children: l(F ? "ملاحظات الفحص" : "سبب إعادة العربية للتصليح")
            }), s.jsx("p", {
              className: "mt-1 whitespace-pre-wrap break-words",
              children: R.notes
            })]
          })]
        }), F ? s.jsxs("div", {
          className: "mt-4 rounded-xl border border-slate-200 p-4",
          children: [s.jsx("h3", {
            className: "font-extrabold",
            children: l("الخطوة التالية: تسليم العربية")
          }), s.jsx("p", {
            className: "mt-1 text-sm text-slate-600",
            children: l("اعتماد الجودة لا يعني تسليم العربية للعميل. التسليم يحتاج تأكيداً منفصلاً.")
          }), o.isError ? s.jsxs("div", {
            className: "mt-3 space-y-2",
            children: [s.jsx($, {
              message: o.error.message
            }), s.jsx(P, {
              kind: "secondary",
              onClick: () => o.refetch(),
              children: l("إعادة المحاولة")
            })]
          }) : L ? s.jsx("p", {
            role: "status",
            className: "mt-3 text-sm text-slate-500",
            children: l("جارٍ تحديث متطلبات التسليم…")
          }) : te.length > 0 ? s.jsxs("div", {
            className: "mt-3",
            children: [s.jsx("p", {
              className: "text-sm font-bold text-amber-900",
              children: l("المتبقي قبل تسليم العربية")
            }), s.jsx("ul", {
              className: "mt-2 space-y-1",
              children: te.map(U => s.jsxs("li", {
                className: "flex items-start gap-2 text-sm text-amber-900",
                children: [s.jsx(at, {
                  size: 17,
                  className: "mt-0.5 shrink-0",
                  "aria-hidden": !0
                }), J(U.message)]
              }, U.code))
            })]
          }) : s.jsx("p", {
            className: "mt-3 font-semibold text-ok",
            children: l("متطلبات التسليم مكتملة. يمكنك تأكيد التسليم من القسم التالي.")
          })]
        }) : s.jsx("p", {
          className: "mt-4 rounded-xl bg-slate-50 p-4 text-slate-700",
          children: l("عالج الملاحظات، ثم سجّل فحص جودة جديداً قبل التسليم.")
        }), !F && s.jsx("div", {
          className: "mt-4",
          children: s.jsx(P, {
            kind: "secondary",
            icon: rr,
            onClick: () => {
              p(e.id), y(null), u({
                repairs: !1,
                parts: !1,
                road: !1,
                notes: "",
                override: ""
              }), N.reset();
            },
            children: l("إجراء فحص جديد")
          })
        })]
      }) : s.jsxs(s.Fragment, {
        children: [h === e.id && s.jsx("p", {
          className: "mb-3 text-sm font-semibold text-brand",
          children: l("فحص جديد — النتيجة السابقة محفوظة")
        }), s.jsxs("div", {
          className: "mb-4 rounded-2xl bg-slate-50 p-4",
          children: [s.jsxs("div", {
            className: "mb-2 flex flex-wrap items-center justify-between gap-2",
            children: [s.jsx("p", {
              className: "text-sm text-slate-600",
              children: l("٣ خطوات سريعة قبل تجهيز العربية للتسليم")
            }), s.jsx("span", {
              className: `text-sm font-extrabold ${k === 3 ? "text-ok" : "text-brand"}`,
              "aria-live": "polite",
              children: Z("تمت مراجعة {0} من 3", k)
            })]
          }), s.jsx("div", {
            role: "progressbar",
            "aria-label": l("تقدم فحص الجودة"),
            "aria-valuemin": 0,
            "aria-valuemax": 3,
            "aria-valuenow": k,
            className: "h-2 overflow-hidden rounded-full bg-slate-200",
            children: s.jsx("div", {
              className: `h-full rounded-full transition-all ${k === 3 ? "bg-ok" : "bg-brand"}`,
              style: {
                width: `${k / 3 * 100}%`
              }
            })
          })]
        }), _ && s.jsxs("div", {
          className: "mb-4 rounded-xl border border-slate-200 px-4 py-3 text-sm",
          children: [s.jsxs("div", {
            className: "flex flex-wrap items-center gap-2",
            children: [s.jsx("span", {
              className: "font-bold",
              children: l("آخر فحص مسجّل")
            }), s.jsxs("span", {
              className: `inline-flex items-center gap-1 font-bold ${_.result === "passed" ? "text-ok" : "text-bad"}`,
              children: [_.result === "passed" ? s.jsx(Ke, {
                size: 16,
                "aria-hidden": !0
              }) : s.jsx(at, {
                size: 16,
                "aria-hidden": !0
              }), _.result === "passed" ? l("اجتاز الفحص") : l("رفض وإعادة للتصليح")]
            }), _.checked_at && s.jsx("time", {
              className: "text-slate-500",
              dateTime: _.checked_at,
              children: new Date(_.checked_at).toLocaleString($t)
            })]
          }), _.notes && s.jsx("p", {
            className: "mt-1 whitespace-pre-wrap break-words text-slate-600",
            children: _.notes
          })]
        }), o.isError ? s.jsxs("div", {
          className: "mb-4 space-y-2",
          children: [s.jsx($, {
            message: o.error.message
          }), s.jsx(P, {
            kind: "secondary",
            disabled: o.isFetching,
            onClick: () => o.refetch(),
            children: l("إعادة المحاولة")
          })]
        }) : L ? s.jsx("p", {
          role: "status",
          className: "mb-4 text-sm text-slate-500",
          children: l("جارٍ التحقق من اكتمال الأعمال والقطع…")
        }) : b.length > 0 ? s.jsxs("div", {
          className: "mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4",
          children: [s.jsx("p", {
            className: "mb-1 font-bold text-amber-900",
            children: l("نواقص قبل اعتماد الجودة")
          }), s.jsx("ul", {
            className: "space-y-1 text-sm text-amber-900",
            children: b.map(U => s.jsxs("li", {
              className: "flex items-start gap-2",
              children: [s.jsx(at, {
                size: 17,
                className: "mt-0.5 shrink-0",
                "aria-hidden": !0
              }), J(U.message)]
            }, U.code))
          })]
        }) : s.jsxs("p", {
          className: "mb-4 flex items-center gap-2 text-sm font-semibold text-slate-600",
          children: [s.jsx(Ke, {
            size: 18,
            "aria-hidden": !0
          }), l("الأعمال والقطع مكتملة وجاهزة للمراجعة")]
        }), s.jsxs("div", {
          className: "grid gap-3 sm:grid-cols-3",
          children: [Te("repairs", l("راجعت كل الأعمال"), l("تأكد أن الإصلاحات المطلوبة اتنفذت بشكل سليم."), 1), Te("parts", l("راجعت القطع المركّبة"), l("راجع تركيب القطع والتثبيت وعدم وجود تسريب."), 2), Te("road", l("جرّبت العربية"), l("تأكد أن الشكوى اتحلت وأن التجربة سليمة."), 3)]
        }), s.jsxs("div", {
          className: "mt-4 grid gap-3 sm:grid-cols-2",
          children: [s.jsx("div", {
            className: b.length > 0 && n("jobs.override") ? "" : "sm:col-span-2",
            children: s.jsx(E, {
              label: l("ملاحظات (مطلوبة عند الرفض)"),
              children: s.jsx("textarea", {
                rows: 2,
                disabled: N.isPending,
                placeholder: l("اكتب الملاحظة أو سبب إعادة العربية للتصليح"),
                value: d.notes,
                onChange: U => u({
                  ...d,
                  notes: U.target.value
                })
              })
            })
          }), b.length > 0 && n("jobs.override") && s.jsx(E, {
            label: l("سبب الاعتماد رغم عدم الاكتمال (مدير)"),
            children: s.jsx("textarea", {
              rows: 2,
              disabled: N.isPending,
              value: d.override,
              onChange: U => u({
                ...d,
                override: U.target.value
              })
            })
          })]
        }), s.jsx("div", {
          className: "mt-3",
          children: s.jsx($, {
            message: (D = N.error) == null ? void 0 : D.message
          })
        }), s.jsxs("div", {
          className: "mt-4 border-t border-slate-200 pt-4",
          children: [s.jsx("p", {
            className: "mb-3 text-sm text-slate-600",
            children: k < 3 ? l("علّم الخطوات الثلاث بعد مراجعتها لتفعيل الاعتماد.") : b.length > 0 ? l("أكمل النواقص أو سجّل سبب الاستثناء بصلاحية المدير.") : l("اعتماد الجودة ينقل العربية لخطوة التسليم؛ لا يسلمها للعميل تلقائياً.")
          }), s.jsxs("div", {
            className: "flex flex-wrap gap-3",
            children: [s.jsx(P, {
              icon: rr,
              disabled: I,
              onClick: () => N.mutate("passed"),
              children: l("اجتاز الفحص")
            }), s.jsx(P, {
              kind: "danger",
              icon: at,
              disabled: N.isPending || !d.notes.trim(),
              onClick: () => N.mutate("failed"),
              children: l("رفض وإعادة للتصليح")
            })]
          })]
        })]
      })
    }), t !== "quality" && n("delivery.write") && s.jsx("div", {
      id: "vehicle-delivery",
      tabIndex: -1,
      className: "scroll-mt-64",
      children: s.jsxs(B, {
        title: l("تسليم العربية"),
        children: [s.jsx("p", {
          className: "mb-3 rounded-xl bg-brand-soft p-3 text-sm font-semibold",
          children: l("يُغلق أمر الشغل بعد فوترة كل الإصلاحات والقطع وتأكيد التسليم.")
        }), g && n("billing.read") && s.jsx("a", {
          href: "#job-invoices",
          className: "mb-3 inline-block font-bold text-brand underline",
          children: l("انتقل للفواتير لاستكمال الفوترة")
        }), o.data && (f.length === 0 ? s.jsxs("p", {
          className: "mb-3 flex items-center gap-2 text-xl font-bold text-ok",
          children: [s.jsx(Ke, {}), l("جاهزة للتسليم")]
        }) : s.jsx("ul", {
          className: "mb-3 space-y-1",
          children: f.map(U => s.jsxs("li", {
            className: "flex items-center gap-2 text-lg font-semibold text-bad",
            children: [s.jsx(at, {
              size: 20
            }), J(U.message)]
          }, U.code))
        })), s.jsxs("div", {
          className: "grid gap-3 sm:grid-cols-2",
          children: [s.jsx(E, {
            label: l("قراءة العداد عند التسليم"),
            children: s.jsx("input", {
              type: "number",
              min: e.mileage ?? 0,
              value: j.final_mileage,
              onChange: U => v({
                ...j,
                final_mileage: U.target.value
              }),
              dir: "ltr"
            })
          }), s.jsx(E, {
            label: l("اسم المستلم (إقرار العميل)"),
            children: s.jsx("input", {
              value: j.ack_name,
              onChange: U => v({
                ...j,
                ack_name: U.target.value
              })
            })
          }), s.jsx("div", {
            className: "sm:col-span-2",
            children: s.jsx(E, {
              label: l("حالة العربية عند التسليم"),
              children: s.jsx("input", {
                value: j.final_condition,
                onChange: U => v({
                  ...j,
                  final_condition: U.target.value
                })
              })
            })
          }), f.length > 0 && !g && n("jobs.override") && s.jsx("div", {
            className: "sm:col-span-2",
            children: s.jsx(E, {
              label: l("سبب التسليم رغم النواقص (استثناء إداري يُسجَّل)"),
              children: s.jsx("input", {
                value: j.override_reason,
                onChange: U => v({
                  ...j,
                  override_reason: U.target.value
                })
              })
            })
          })]
        }), s.jsx("div", {
          className: "mt-3",
          children: s.jsx($, {
            message: (G = x.error) == null ? void 0 : G.message
          })
        }), s.jsx("div", {
          className: "mt-2",
          children: s.jsx(P, {
            icon: Hl,
            disabled: x.isPending || L || g || !j.final_mileage || j.ack_name.length < 2 || f.length > 0 && !(n("jobs.override") && j.override_reason.trim()),
            onClick: () => confirm(l("تأكيد تسليم العربية للعميل؟")) && x.mutate(),
            children: l("تسليم العربية")
          })
        })]
      })
    })]
  });
}
function hw({
  job: e
}) {
  var x, f, g, b, k, _, S, T, R, F, X, te;
  const {
      can: t
    } = ce(),
    n = zs(),
    r = es(),
    i = de(),
    a = w.useRef(os()),
    o = w.useRef(os()),
    [c, d] = w.useState("all"),
    [u, h] = w.useState({
      amount: "",
      method: "cash"
    }),
    p = W({
      queryKey: ["job-invoices", e.id],
      enabled: t("billing.read"),
      queryFn: () => M.get(`/api/jobs/${e.id}/invoices`)
    }),
    m = V({
      mutationFn: L => M.post(`/api/jobs/${e.id}/invoices`, {
        supplemental: L,
        scope: c
      }, {
        "Idempotency-Key": a.current
      }),
      onSuccess: L => {
        a.current = os(), r(`/invoices/${L.id}`);
      }
    }),
    y = V({
      mutationFn: () => M.post(`/api/jobs/${e.id}/deposits`, {
        amount: u.amount,
        method: u.method
      }, {
        "Idempotency-Key": o.current
      }),
      onSuccess: () => {
        o.current = os(), h({
          amount: "",
          method: "cash"
        }), i.invalidateQueries({
          queryKey: ["job-deposits", e.id]
        });
      }
    }),
    j = W({
      queryKey: ["job-deposits", e.id],
      enabled: t("billing.read"),
      queryFn: () => M.get(`/api/jobs/${e.id}/deposits`)
    });
  if (!t("billing.read")) return null;
  const v = e.status === "cancelled" || e.status === "delivered",
    N = (x = p.data) == null ? void 0 : x.find(L => L.status !== "cancelled");
  return s.jsxs(B, {
    title: l("الفواتير والدفع"),
    children: [p.isLoading && s.jsx("div", {
      role: "status",
      "aria-label": l("جارٍ التحميل…"),
      children: s.jsx(ie, {})
    }), p.isError && s.jsxs("div", {
      className: "space-y-2",
      children: [s.jsx($, {
        message: p.error.message
      }), s.jsx(P, {
        kind: "secondary",
        onClick: () => p.refetch(),
        children: l("إعادة المحاولة")
      })]
    }), s.jsx("ul", {
      className: "space-y-2",
      children: (f = p.data) == null ? void 0 : f.map(L => s.jsx("li", {
        children: s.jsxs(re, {
          to: `/invoices/${L.id}`,
          className: "flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-50 p-4 hover:bg-brand-soft",
          children: [s.jsx("span", {
            className: "text-xl font-bold",
            children: L.number
          }), s.jsx(Xe, {
            status: L.status === "issued" ? L.payment_status : L.status === "cancelled" ? "void" : "draft"
          }), s.jsx("span", {
            className: "text-xl font-extrabold",
            children: L.total
          })]
        })
      }, L.id))
    }), p.isSuccess && e.status !== "cancelled" && t("billing.write") && !((g = p.data) != null && g.some(L => L.status === "draft")) && (!v || !N) && s.jsxs("div", {
      className: "mt-4 rounded-2xl border border-blue-100 bg-blue-50 p-4",
      children: [s.jsx(E, {
        label: l("محتوى الفاتورة"),
        children: s.jsxs("select", {
          disabled: m.isPending,
          value: c,
          onChange: L => {
            d(L.target.value), a.current = os(), m.reset();
          },
          children: [s.jsx("option", {
            value: "all",
            children: l("الإصلاحات وقطع الغيار معًا")
          }), s.jsx("option", {
            value: "labor",
            children: l("الإصلاحات فقط")
          }), s.jsx("option", {
            value: "parts",
            children: l("قطع الغيار فقط")
          })]
        })
      }), s.jsx("p", {
        className: "mt-2 text-sm text-slate-600",
        children: l("سيتم إنشاء مسودة للمراجعة بالبَنود المختارة غير المفوترة فقط.")
      })]
    }), p.isSuccess && e.status !== "cancelled" && !N && t("billing.write") && s.jsxs("div", {
      className: "mt-3",
      children: [s.jsx($, {
        message: (b = m.error) == null ? void 0 : b.message
      }), s.jsx(P, {
        icon: Xc,
        disabled: m.isPending,
        onClick: () => m.mutate(!1),
        children: l("إنشاء فاتورة")
      })]
    }), p.isSuccess && !v && t("billing.write") && ((k = p.data) == null ? void 0 : k.some(L => L.status === "issued")) && !((_ = p.data) != null && _.some(L => L.status === "draft")) && s.jsxs("div", {
      className: "mt-4 rounded-xl bg-brand-soft p-4",
      children: [s.jsx("p", {
        className: "mb-3 text-sm",
        children: l("الفاتورة الإضافية تشمل الأعمال والقطع الجديدة غير المفوترة فقط.")
      }), s.jsx($, {
        message: (S = m.error) == null ? void 0 : S.message
      }), s.jsx(P, {
        icon: Xc,
        disabled: m.isPending,
        onClick: () => m.mutate(!0),
        children: l("فاتورة إضافية للأعمال الجديدة")
      })]
    }), p.isSuccess && !v && t("billing.write") && !((T = p.data) != null && T.some(L => L.status === "issued")) && s.jsxs("div", {
      className: "mt-5 rounded-2xl border-2 border-dashed border-slate-300 p-4",
      children: [s.jsxs("p", {
        className: "mb-2 text-lg font-extrabold",
        children: [l("عربون مقدم"), " ", (R = j.data) != null && R.length ? `(${j.data.map(L => L.amount).join(" + ")})` : ""]
      }), s.jsxs("div", {
        className: "grid gap-3 sm:grid-cols-3",
        children: [s.jsx(E, {
          label: l("المبلغ"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            value: u.amount,
            onChange: L => h({
              ...u,
              amount: L.target.value
            }),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("الطريقة"),
          children: s.jsx("select", {
            value: u.method,
            onChange: L => h({
              ...u,
              method: L.target.value
            }),
            children: (((F = n.data) == null ? void 0 : F.finance.payment_methods) ?? []).map(L => s.jsx("option", {
              value: L.key,
              children: J(L.label)
            }, L.key))
          })
        }), s.jsx("div", {
          className: "flex items-end",
          children: s.jsx(P, {
            icon: ju,
            disabled: !(Number(u.amount) > 0) || y.isPending || !j.isSuccess,
            onClick: () => y.mutate(),
            children: l("تسجيل العربون")
          })
        })]
      }), s.jsx($, {
        message: ((X = y.error) == null ? void 0 : X.message) ?? ((te = j.error) == null ? void 0 : te.message)
      }), j.isError && s.jsx(P, {
        kind: "secondary",
        onClick: () => j.refetch(),
        children: l("إعادة المحاولة")
      })]
    })]
  });
}
const Ep = ["requested", "ordered", "purchased", "received", "installed"],
  Dy = {
    ordered: l("تم الطلب"),
    purchased: l("تم الشراء"),
    received: l("وصلت الورشة"),
    installed: l("تم التركيب")
  },
  Pp = {
    part_name: "",
    brand: "",
    part_number: "",
    supplier_id: "",
    supplier_invoice_no: "",
    quantity: "1",
    unit_cost: "",
    unit_price: "",
    warranty_months: "",
    status: "purchased"
  };
function pw({
  p: e,
  job: t,
  techs: n,
  refresh: r
}) {
  var y, j;
  const [i, a] = w.useState(""),
    [o, c] = w.useState(null),
    d = V({
      mutationFn: v => M.post(`/api/parts/${e.id}/status`, {
        status: v,
        technician_id: i ? Number(i) : null
      }),
      onSuccess: r
    }),
    u = V({
      mutationFn: () => M.post(`/api/parts/${e.id}/return`, {
        quantity: o.quantity,
        refund_amount: o.refund_amount || "0",
        reason: o.reason
      }),
      onSuccess: () => {
        c(null), r();
      }
    }),
    h = t.status === "delivered" || t.status === "cancelled",
    p = e.status === "returned" || e.status === "cancelled",
    m = Ep[Ep.indexOf(e.status) + 1];
  return s.jsxs("li", {
    className: "space-y-2 rounded-2xl bg-slate-50 p-4",
    children: [s.jsxs("div", {
      className: "flex flex-wrap items-center justify-between gap-2",
      children: [s.jsxs("p", {
        className: "text-xl font-bold",
        children: [e.part_name, " ", e.brand && s.jsxs("span", {
          className: "text-slate-500",
          children: ["· ", e.brand]
        })]
      }), s.jsx(Xe, {
        status: e.status
      })]
    }), s.jsxs("p", {
      className: "text-slate-600",
      children: [s.jsx("span", {
        dir: "ltr",
        children: e.part_number ?? ""
      }), " ", l("· الكمية"), " ", e.effective_quantity, Number(e.returned_quantity) > 0 && Z(" (رجع {0})", e.returned_quantity), " ", l("· سعر البيع"), " ", s.jsx("b", {
        children: e.total_price
      }), e.total_cost !== void 0 && s.jsxs(s.Fragment, {
        children: [" ", l("· التكلفة"), " ", e.total_cost, " ", l("· الربح"), " ", s.jsx("b", {
          children: e.gross_profit
        })]
      })]
    }), e.installed_at && s.jsxs("p", {
      className: "text-ok font-semibold",
      children: [l("تركيب:"), " ", $e(e.installed_at), e.warranty_expiry && Z(" · الضمان حتى {0}", $e(e.warranty_expiry))]
    }), !h && !p && s.jsxs("div", {
      className: "flex flex-wrap items-center gap-2",
      children: [m === "installed" && s.jsxs("select", {
        "aria-label": l("الفني المركّب"),
        value: i,
        onChange: v => a(v.target.value),
        className: "!w-auto",
        children: [s.jsx("option", {
          value: "",
          children: l("مين ركّبها؟")
        }), n.map(v => s.jsx("option", {
          value: v.id,
          children: v.name
        }, v.id))]
      }), m && s.jsx(P, {
        disabled: d.isPending || m === "installed" && !i,
        onClick: () => d.mutate(m),
        children: Dy[m]
      }), e.status !== "installed" && s.jsx(P, {
        kind: "secondary",
        onClick: () => confirm(l("إلغاء القطعة؟")) && d.mutate("cancelled"),
        children: l("إلغاء")
      }), ["purchased", "received", "installed"].includes(e.status) && s.jsx(P, {
        kind: "secondary",
        icon: ed,
        onClick: () => c({
          quantity: "1",
          refund_amount: "",
          reason: ""
        }),
        children: l("مرتجع")
      })]
    }), o && s.jsxs("div", {
      className: "grid gap-2 rounded-xl border-2 border-dashed border-slate-300 p-3 sm:grid-cols-3",
      children: [s.jsx(E, {
        label: l("الكمية المرتجعة"),
        children: s.jsx("input", {
          type: "number",
          step: "0.01",
          min: "0",
          value: o.quantity,
          onChange: v => c({
            ...o,
            quantity: v.target.value
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("المبلغ المسترد"),
        children: s.jsx("input", {
          type: "number",
          step: "0.01",
          min: "0",
          value: o.refund_amount,
          onChange: v => c({
            ...o,
            refund_amount: v.target.value
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("السبب"),
        children: s.jsx("input", {
          value: o.reason,
          onChange: v => c({
            ...o,
            reason: v.target.value
          })
        })
      }), s.jsx("div", {
        className: "sm:col-span-3",
        children: s.jsx(P, {
          disabled: o.reason.length < 2 || u.isPending,
          onClick: () => u.mutate(),
          children: l("تسجيل المرتجع")
        })
      })]
    }), s.jsx($, {
      message: ((y = d.error) == null ? void 0 : y.message) ?? ((j = u.error) == null ? void 0 : j.message)
    }), s.jsxs("details", {
      className: "no-print",
      children: [s.jsx("summary", {
        className: "cursor-pointer font-bold text-brand",
        children: l("صورة القطعة وفاتورة المورد")
      }), s.jsx(Ru, {
        ownerType: "part",
        ownerId: String(e.id),
        title: l("مرفقات القطعة")
      })]
    })]
  });
}
function fw({
  job: e,
  techs: t
}) {
  var y, j, v, N, x;
  const n = de(),
    [r, i] = w.useState(Pp),
    [a, o] = w.useState(!1),
    c = () => {
      n.invalidateQueries({
        queryKey: ["parts", e.id]
      }), n.invalidateQueries({
        queryKey: ["job", e.id]
      }), n.invalidateQueries({
        queryKey: ["board"]
      });
    },
    d = W({
      queryKey: ["parts", e.id],
      queryFn: () => M.get(`/api/jobs/${e.id}/parts`)
    }),
    u = W({
      queryKey: ["suppliers", !0],
      queryFn: () => M.get("/api/suppliers?active=true")
    }),
    h = V({
      mutationFn: f => M.post(`/api/jobs/${e.id}/parts${f ? "?force=true" : ""}`, {
        part_name: r.part_name,
        brand: r.brand || null,
        part_number: r.part_number || null,
        supplier_id: r.supplier_id ? Number(r.supplier_id) : null,
        supplier_invoice_no: r.supplier_invoice_no || null,
        quantity: r.quantity || "1",
        unit_cost: r.unit_cost || "0",
        unit_price: r.unit_price || "0",
        warranty_months: r.warranty_months ? Number(r.warranty_months) : null,
        status: r.status
      }),
      onSuccess: () => {
        i(Pp), o(!1), c();
      },
      onError: f => o(f instanceof Sr && f.code === "possible_duplicate")
    }),
    p = e.status === "delivered" || e.status === "cancelled",
    m = f => g => i({
      ...r,
      [f]: g.target.value
    });
  return s.jsxs(B, {
    title: Z("قطع الغيار ({0})", ((y = d.data) == null ? void 0 : y.length) ?? 0),
    children: [s.jsx("ul", {
      className: "space-y-3",
      children: (j = d.data) == null ? void 0 : j.map(f => s.jsx(pw, {
        p: f,
        job: e,
        techs: t,
        refresh: c
      }, f.id))
    }), !p && s.jsxs("div", {
      className: "mt-5 space-y-3 rounded-2xl border-2 border-dashed border-slate-300 p-4",
      children: [s.jsx("p", {
        className: "text-lg font-extrabold",
        children: l("تسجيل قطعة غيار")
      }), s.jsxs("div", {
        className: "grid gap-3 sm:grid-cols-2 lg:grid-cols-3",
        children: [s.jsx(E, {
          label: l("اسم القطعة"),
          children: s.jsx("input", {
            value: r.part_name,
            onChange: m("part_name")
          })
        }), s.jsx(E, {
          label: l("الماركة"),
          children: s.jsx("input", {
            value: r.brand,
            onChange: m("brand")
          })
        }), s.jsx(E, {
          label: l("رقم القطعة"),
          children: s.jsx("input", {
            value: r.part_number,
            onChange: m("part_number"),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("المورد"),
          children: s.jsxs("select", {
            value: r.supplier_id,
            onChange: m("supplier_id"),
            children: [s.jsx("option", {
              value: "",
              children: "—"
            }), (v = u.data) == null ? void 0 : v.map(f => s.jsx("option", {
              value: f.id,
              children: f.name
            }, f.id))]
          })
        }), s.jsx(E, {
          label: l("رقم فاتورة المورد"),
          children: s.jsx("input", {
            value: r.supplier_invoice_no,
            onChange: m("supplier_invoice_no"),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("الكمية"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            value: r.quantity,
            onChange: m("quantity"),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("سعر الشراء (للوحدة)"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            value: r.unit_cost,
            onChange: m("unit_cost"),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("سعر البيع (للوحدة)"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            value: r.unit_price,
            onChange: m("unit_price"),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("الضمان (شهور)"),
          children: s.jsx("input", {
            type: "number",
            min: "0",
            value: r.warranty_months,
            onChange: m("warranty_months"),
            dir: "ltr"
          })
        })]
      }), s.jsx(E, {
        label: l("الحالة"),
        children: s.jsx("select", {
          value: r.status,
          onChange: m("status"),
          children: ["requested", "ordered", "purchased", "received"].map(f => s.jsx("option", {
            value: f,
            children: Dy[f] ?? l("مطلوبة")
          }, f))
        })
      }), a ? s.jsxs("div", {
        className: "rounded-xl bg-wait-soft p-3 font-bold text-wait",
        children: ["⚠️ ", (N = h.error) == null ? void 0 : N.message, " ", s.jsx("button", {
          className: "underline",
          onClick: () => h.mutate(!0),
          children: l("سجّلها برضه")
        })]
      }) : s.jsx($, {
        message: (x = h.error) == null ? void 0 : x.message
      }), s.jsx(P, {
        icon: Pb,
        disabled: r.part_name.length < 2 || h.isPending,
        onClick: () => h.mutate(!1),
        children: l("حفظ القطعة")
      })]
    })]
  });
}
function mw({
  job: e
}) {
  var o, c, d;
  const t = de(),
    {
      can: n
    } = ce(),
    r = W({
      queryKey: ["quotes", e.id],
      queryFn: () => M.get(`/api/jobs/${e.id}/quotations`)
    }),
    i = V({
      mutationFn: () => M.post(`/api/jobs/${e.id}/quotations`, {}),
      onSuccess: () => {
        t.invalidateQueries({
          queryKey: ["quotes", e.id]
        }), t.invalidateQueries({
          queryKey: ["job", e.id]
        }), t.invalidateQueries({
          queryKey: ["board"]
        });
      }
    }),
    a = e.status === "delivered" || e.status === "cancelled";
  return s.jsxs(B, {
    title: l("عروض الأسعار"),
    action: n("quotes.write") && !a ? s.jsx(P, {
      icon: Xc,
      disabled: i.isPending || !r.isSuccess,
      onClick: () => i.mutate(),
      children: l("عرض سعر جديد")
    }) : void 0,
    children: [s.jsx($, {
      message: (o = i.error) == null ? void 0 : o.message
    }), r.isLoading && s.jsx("div", {
      role: "status",
      "aria-label": l("جارٍ التحميل…"),
      children: s.jsx(ie, {})
    }), r.isError && s.jsxs("div", {
      className: "space-y-2",
      children: [s.jsx($, {
        message: r.error.message
      }), s.jsx(P, {
        kind: "secondary",
        onClick: () => r.refetch(),
        children: l("إعادة المحاولة")
      })]
    }), r.isSuccess && !((c = r.data) != null && c.length) && s.jsx("p", {
      className: "text-slate-500",
      children: l("لسه مفيش عروض أسعار")
    }), s.jsx("ul", {
      className: "space-y-2",
      children: (d = r.data) == null ? void 0 : d.map(u => s.jsx("li", {
        children: s.jsxs(re, {
          to: `/quotations/${u.id}`,
          className: "flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-50 p-4 hover:bg-brand-soft",
          children: [s.jsxs("span", {
            className: "text-xl font-bold",
            children: [l("عرض #"), u.quote_no]
          }), s.jsx(Xe, {
            status: u.status
          }), s.jsx("span", {
            className: "text-xl font-extrabold",
            children: u.grand_total
          })]
        })
      }, u.id))
    })]
  });
}
const xw = {
  open: l("مفتوحة"),
  approved: l("مقبولة"),
  rejected: l("مرفوضة")
};
function gw({
  w: e,
  refresh: t
}) {
  var u, h;
  const {
      can: n
    } = ce(),
    [r, i] = w.useState({
      description: "",
      mileage: ""
    }),
    [a, o] = w.useState(null),
    c = V({
      mutationFn: () => M.post(`/api/warranties/${e.id}/claims`, {
        description: r.description,
        mileage: r.mileage ? Number(r.mileage) : null
      }),
      onSuccess: () => {
        i({
          description: "",
          mileage: ""
        }), t();
      }
    }),
    d = V({
      mutationFn: () => M.post(`/api/claims/${a.id}/decide`, {
        decision: a.decision,
        resolution: a.resolution
      }),
      onSuccess: () => {
        o(null), t();
      }
    });
  return s.jsxs("div", {
    className: "mt-2 space-y-2",
    children: [e.claims.map(p => s.jsxs("div", {
      className: "rounded-xl bg-white p-3",
      children: [s.jsxs("p", {
        children: [s.jsxs("b", {
          children: [l("مطالبة"), " ", $e(p.claim_date), ":"]
        }), " ", p.description, " — ", s.jsx("span", {
          className: "font-bold",
          children: xw[p.status]
        }), p.resolution && ` (${p.resolution})`]
      }), p.status === "open" && n("warranties.decide") && ((a == null ? void 0 : a.id) === p.id ? s.jsxs("div", {
        className: "mt-2 grid gap-2 sm:grid-cols-3",
        children: [s.jsx(E, {
          label: l("القرار"),
          children: s.jsxs("select", {
            value: a.decision,
            onChange: m => o({
              ...a,
              decision: m.target.value
            }),
            children: [s.jsx("option", {
              value: "approved",
              children: l("قبول")
            }), s.jsx("option", {
              value: "rejected",
              children: l("رفض")
            })]
          })
        }), s.jsx(E, {
          label: l("التفاصيل"),
          children: s.jsx("input", {
            value: a.resolution,
            onChange: m => o({
              ...a,
              resolution: m.target.value
            })
          })
        }), s.jsx("div", {
          className: "flex items-end",
          children: s.jsx(P, {
            disabled: a.resolution.length < 3 || d.isPending,
            onClick: () => d.mutate(),
            children: l("تأكيد")
          })
        })]
      }) : s.jsx("div", {
        className: "mt-2",
        children: s.jsx(P, {
          kind: "secondary",
          onClick: () => o({
            id: p.id,
            decision: "approved",
            resolution: ""
          }),
          children: l("البت في المطالبة")
        })
      }))]
    }, p.id)), e.status === "active" && n("visits.write") && s.jsxs("div", {
      className: "grid gap-2 sm:grid-cols-3",
      children: [s.jsx(E, {
        label: l("وصف المشكلة"),
        children: s.jsx("input", {
          value: r.description,
          onChange: p => i({
            ...r,
            description: p.target.value
          })
        })
      }), s.jsx(E, {
        label: l("العداد الحالي"),
        children: s.jsx("input", {
          type: "number",
          min: 0,
          value: r.mileage,
          onChange: p => i({
            ...r,
            mileage: p.target.value
          }),
          dir: "ltr"
        })
      }), s.jsx("div", {
        className: "flex items-end",
        children: s.jsx(P, {
          kind: "secondary",
          disabled: r.description.length < 3 || c.isPending,
          onClick: () => c.mutate(),
          children: l("تسجيل مطالبة ضمان")
        })
      })]
    }), s.jsx($, {
      message: ((u = c.error) == null ? void 0 : u.message) ?? ((h = d.error) == null ? void 0 : h.message)
    })]
  });
}
function yw({
  job: e
}) {
  var d, u, h, p;
  const {
      can: t
    } = ce(),
    n = de(),
    [r, i] = w.useState({
      description: "",
      months: "3",
      mileage_limit: ""
    }),
    a = W({
      queryKey: ["job-warranties", e.id],
      queryFn: () => M.get(`/api/jobs/${e.id}/warranties`)
    }),
    o = () => n.invalidateQueries({
      queryKey: ["job-warranties", e.id]
    }),
    c = V({
      mutationFn: () => M.post(`/api/jobs/${e.id}/warranties`, {
        kind: "labor",
        description: r.description,
        months: Number(r.months),
        mileage_limit: r.mileage_limit ? Number(r.mileage_limit) : null
      }),
      onSuccess: () => {
        i({
          description: "",
          months: "3",
          mileage_limit: ""
        }), o();
      }
    });
  return !((d = a.data) != null && d.length) && !t("visits.write") ? null : s.jsxs(B, {
    title: Z("الضمان ({0})", ((u = a.data) == null ? void 0 : u.length) ?? 0),
    children: [s.jsx("ul", {
      className: "space-y-3",
      children: (h = a.data) == null ? void 0 : h.map(m => s.jsxs("li", {
        className: "rounded-2xl bg-slate-50 p-4",
        children: [s.jsxs("div", {
          className: "flex flex-wrap items-center justify-between gap-2",
          children: [s.jsx("p", {
            className: "text-xl font-bold",
            children: J(m.description)
          }), s.jsx(Xe, {
            status: m.status
          })]
        }), s.jsxs("p", {
          className: "text-slate-600",
          children: [l("من"), " ", $e(m.start_date), " ", l("حتى"), " ", $e(m.end_date), m.mileage_limit ? Z(" · حد {0} كم", m.mileage_limit) : ""]
        }), s.jsx(gw, {
          w: m,
          refresh: o
        })]
      }, m.id))
    }), t("visits.write") && s.jsxs("div", {
      className: "mt-4 grid gap-3 rounded-2xl border-2 border-dashed border-slate-300 p-4 sm:grid-cols-4",
      children: [s.jsx("div", {
        className: "sm:col-span-2",
        children: s.jsx(E, {
          label: l("ضمان عمالة جديد"),
          children: s.jsx("input", {
            value: r.description,
            onChange: m => i({
              ...r,
              description: m.target.value
            }),
            placeholder: l("مثلاً: ضمان تركيب الفرامل")
          })
        })
      }), s.jsx(E, {
        label: l("المدة (شهور)"),
        children: s.jsx("input", {
          type: "number",
          min: 1,
          value: r.months,
          onChange: m => i({
            ...r,
            months: m.target.value
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("حد المسافة (كم، اختياري)"),
        children: s.jsx("input", {
          type: "number",
          min: 1,
          value: r.mileage_limit,
          onChange: m => i({
            ...r,
            mileage_limit: m.target.value
          }),
          dir: "ltr"
        })
      }), s.jsxs("div", {
        className: "sm:col-span-4",
        children: [s.jsx($, {
          message: (p = c.error) == null ? void 0 : p.message
        }), s.jsx(P, {
          icon: Fb,
          disabled: r.description.length < 2 || c.isPending,
          onClick: () => c.mutate(),
          children: l("إضافة ضمان")
        })]
      })]
    }), s.jsx("span", {
      className: "hidden",
      children: s.jsx(ts, {})
    })]
  });
}
const Pa = {
    good: l("سليم"),
    attention: l("يحتاج انتباه"),
    critical: l("حرج"),
    na: l("لا ينطبق")
  },
  Ao = {
    good: "border-ok bg-ok-soft text-ok",
    attention: "border-wait bg-wait-soft text-wait",
    critical: "border-bad bg-bad-soft text-bad",
    na: "border-idle bg-idle-soft text-idle"
  },
  Rp = {
    good: "✔",
    attention: "⚠",
    critical: "✖",
    na: "—"
  },
  vw = {
    pending: l("في الانتظار"),
    in_progress: l("شغّال"),
    done: l("خلصت"),
    cancelled: l("ملغية")
  };
function jw(e) {
  const t = de();
  return {
    q: W({
      queryKey: ["job", e],
      queryFn: () => M.get(`/api/jobs/${e}`),
      refetchInterval: 3e4
    }),
    refresh: () => {
      t.invalidateQueries({
        queryKey: ["job", e]
      }), t.invalidateQueries({
        queryKey: ["board"]
      });
    }
  };
}
function bw({
  job: e,
  refresh: t
}) {
  var d;
  const {
      can: n
    } = ce(),
    [r, i] = w.useState(""),
    a = V({
      mutationFn: u => M.post(`/api/jobs/${e.id}/status`, {
        status: u,
        reason: r || null,
        expected_version: e.version
      }),
      onSuccess: () => {
        i(""), t();
      }
    }),
    o = e.status === "delivered" || e.status === "cancelled",
    c = u => {
      if (u === "cancelled" && !r.trim()) {
        alert(l("اكتب سبب الإلغاء الأول"));
        return;
      }
      u === "cancelled" && !confirm(l("تأكيد إلغاء أمر الصيانة؟")) || a.mutate(u);
    };
  return o && !n("jobs.override") ? null : s.jsx(B, {
    children: s.jsxs("details", {
      children: [s.jsx("summary", {
        className: "cursor-pointer py-2 font-extrabold text-slate-700",
        children: l("التعديل اليدوي للحالة")
      }), s.jsxs("div", {
        className: "mt-3",
        children: [!o && s.jsx("p", {
          className: "mb-3 text-sm text-slate-600",
          children: l("تتحدث الحالة تلقائياً حسب الفحص وعرض السعر وقطع الغيار والإصلاح. يمكنك تعديلها يدوياً عند الحاجة.")
        }), s.jsx("div", {
          className: "flex flex-wrap gap-2",
          children: (o ? ["in_progress"] : my.filter(u => u !== e.status && u !== "delivered" && u !== "ready")).map(u => s.jsxs("button", {
            onClick: () => c(u),
            disabled: a.isPending || o && !r.trim(),
            className: "inline-flex min-h-[48px] items-center gap-2 rounded-xl border-2 border-slate-300 bg-white px-4 font-bold hover:border-brand disabled:opacity-50",
            children: [(() => {
              const h = Ts[u].icon;
              return s.jsx(h, {
                size: 18
              });
            })(), o ? l("إعادة فتح للإصلاح") : Ts[u].label]
          }, u))
        }), s.jsx("div", {
          className: "mt-3",
          children: s.jsx(E, {
            label: l(o ? "سبب إعادة الفتح (مطلوب، بصلاحية المدير)" : "سبب تغيير الحالة (مطلوب عند الإلغاء)"),
            children: s.jsx("input", {
              value: r,
              onChange: u => i(u.target.value)
            })
          })
        }), s.jsx("div", {
          className: "mt-2",
          children: s.jsx($, {
            message: (d = a.error) == null ? void 0 : d.message
          })
        })]
      })]
    })
  });
}
function ww({
  job: e,
  refresh: t,
  tpl: n,
  techs: r
}) {
  var T, R, F, X, te, L;
  const i = zs(),
    [a, o] = w.useState(""),
    [c, d] = w.useState({
      description: "",
      technician_id: "",
      labor_hours: "",
      labor_rate: ""
    }),
    u = (T = n == null ? void 0 : n.repair_catalog) == null ? void 0 : T.find(I => I.category === a && J(I.name) === c.description && I.active),
    h = e.technicians ?? [],
    p = h.some(I => String(I.id) === c.technician_id) ? c.technician_id : h.length === 1 ? String(h[0].id) : "",
    m = V({
      mutationFn: () => M.post(`/api/jobs/${e.id}/operations`, {
        category: a || null,
        description: c.description,
        technician_id: p ? Number(p) : null,
        labor_hours: c.labor_hours || "0"
      }),
      onSuccess: () => {
        d({
          description: "",
          technician_id: "",
          labor_hours: "",
          labor_rate: ""
        }), t();
      }
    }),
    y = V({
      mutationFn: I => M.patch(`/api/operations/${I.id}`, {
        status: I.status
      }),
      onSuccess: t
    }),
    [j, v] = w.useState(null),
    [N, x] = w.useState({
      description: "",
      technician_id: "",
      labor_hours: "",
      labor_rate: ""
    }),
    f = (R = e.operations.find(I => I.id === j)) == null ? void 0 : R.technician_id,
    g = h.some(I => String(I.id) === N.technician_id) || N.technician_id === String(f) ? N.technician_id : "",
    b = V({
      mutationFn: I => M.patch(`/api/operations/${I}`, {
        description: N.description,
        technician_id: g ? Number(g) : null,
        labor_hours: N.labor_hours || "0",
        labor_rate: N.labor_rate || "0"
      }),
      onSuccess: () => {
        v(null), t();
      }
    }),
    k = I => {
      x({
        description: J(I.description),
        technician_id: I.technician_id ? String(I.technician_id) : "",
        labor_hours: String(I.labor_hours),
        labor_rate: String(I.labor_rate)
      }), b.reset(), v(I.id);
    },
    _ = I => {
      confirm(l("حذف هذه العملية؟ ستظل ظاهرة كملغية في السجل.")) && y.mutate({
        id: I,
        status: "cancelled"
      });
    },
    S = e.status === "delivered" || e.status === "cancelled";
  return s.jsxs(B, {
    title: Z("عمليات الصيانة ({0})", e.operations.length),
    children: [s.jsx($, {
      message: (F = y.error) == null ? void 0 : F.message
    }), s.jsx("ul", {
      className: "space-y-3",
      children: e.operations.map(I => {
        var ut, O;
        const Te = Er(I.category),
          st = (Te == null ? void 0 : Te.icon) ?? ns;
        return s.jsxs("li", {
          className: "flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-50 p-4",
          children: [s.jsxs("div", {
            className: "flex items-center gap-3",
            children: [s.jsx(st, {
              size: 32,
              className: "text-brand"
            }), s.jsxs("div", {
              children: [s.jsx("p", {
                className: `text-xl font-bold ${I.status === "cancelled" ? "text-slate-400 line-through" : ""}`,
                children: J(I.description)
              }), s.jsxs("p", {
                className: "text-slate-600",
                children: [vw[I.status], " · ", I.labor_hours, " ", l("ساعة ×"), " ", I.labor_rate, " = ", s.jsx("b", {
                  children: I.labor_amount
                })]
              })]
            })]
          }), !S && j !== I.id && s.jsxs("div", {
            className: "flex flex-wrap gap-2",
            children: [I.status === "pending" && s.jsx(P, {
              onClick: () => y.mutate({
                id: I.id,
                status: "in_progress"
              }),
              children: l("ابدأ")
            }), I.status !== "done" && I.status !== "cancelled" && s.jsx(P, {
              kind: "secondary",
              icon: Ke,
              onClick: () => y.mutate({
                id: I.id,
                status: "done"
              }),
              children: l("خلصت")
            }), I.status !== "cancelled" && s.jsx(P, {
              kind: "secondary",
              icon: Mg,
              onClick: () => k(I),
              children: l("تعديل")
            }), I.status !== "cancelled" && s.jsx(P, {
              kind: "secondary",
              icon: Or,
              onClick: () => _(I.id),
              children: l("حذف")
            }), I.status === "cancelled" && s.jsx(P, {
              kind: "secondary",
              icon: yu,
              onClick: () => y.mutate({
                id: I.id,
                status: "pending"
              }),
              children: l("استرجاع")
            })]
          }), j === I.id && s.jsxs("div", {
            className: "basis-full space-y-3 rounded-2xl border-2 border-brand/30 bg-white p-4",
            children: [s.jsx(E, {
              label: l("الوصف"),
              children: s.jsx("input", {
                value: N.description,
                onChange: D => x({
                  ...N,
                  description: D.target.value
                })
              })
            }), s.jsxs("div", {
              className: "grid gap-3 sm:grid-cols-3",
              children: [s.jsx(E, {
                label: l("الفني"),
                children: s.jsxs("select", {
                  value: g,
                  onChange: D => x({
                    ...N,
                    technician_id: D.target.value
                  }),
                  children: [s.jsx("option", {
                    value: "",
                    children: "—"
                  }), f && !h.some(D => D.id === f) && s.jsxs("option", {
                    value: f,
                    disabled: !0,
                    children: [((ut = r.find(D => D.id === f)) == null ? void 0 : ut.name) ?? `${l("الفني")} #${f}`, " — ", l("التعيين السابق")]
                  }), h.map(D => s.jsx("option", {
                    value: D.id,
                    children: D.name
                  }, D.id))]
                })
              }), s.jsx(E, {
                label: l("ساعات العمل"),
                children: s.jsx("input", {
                  type: "number",
                  step: "0.25",
                  min: 0,
                  value: N.labor_hours,
                  onChange: D => x({
                    ...N,
                    labor_hours: D.target.value
                  }),
                  dir: "ltr"
                })
              }), s.jsx(E, {
                label: l("سعر الساعة"),
                children: s.jsx("input", {
                  type: "number",
                  step: "0.01",
                  min: 0,
                  value: N.labor_rate,
                  onChange: D => x({
                    ...N,
                    labor_rate: D.target.value
                  }),
                  dir: "ltr"
                })
              })]
            }), s.jsx($, {
              message: (O = b.error) == null ? void 0 : O.message
            }), s.jsxs("div", {
              className: "flex flex-wrap gap-2",
              children: [s.jsx(P, {
                icon: et,
                disabled: N.description.length < 2 || b.isPending,
                onClick: () => b.mutate(I.id),
                children: l("حفظ")
              }), s.jsx(P, {
                kind: "secondary",
                icon: ia,
                onClick: () => v(null),
                children: l("إلغاء")
              })]
            })]
          })]
        }, I.id);
      })
    }), s.jsxs("p", {
      className: "mt-3 text-2xl font-extrabold",
      children: [l("إجمالي الأجور:"), " ", (e.operations.filter(I => I.status !== "cancelled").reduce((I, Te) => I + Math.round(Number(Te.labor_amount) * 100), 0) / 100).toFixed(2)]
    }), !S && s.jsxs("div", {
      className: "mt-5 space-y-3 rounded-2xl border-2 border-dashed border-slate-300 p-4",
      children: [s.jsx("p", {
        className: "text-lg font-extrabold",
        children: l("إضافة عملية")
      }), s.jsx("div", {
        className: "grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-7",
        children: Hn.map(({
          key: I,
          label: Te,
          icon: st
        }) => s.jsxs("button", {
          type: "button",
          "aria-pressed": a === I,
          onClick: () => o(a === I ? "" : I),
          className: `flex min-h-[72px] flex-col items-center justify-center gap-1 rounded-xl border-4 p-1 text-sm font-bold ${a === I ? "border-brand bg-brand-soft text-brand" : "border-slate-200 bg-white"}`,
          children: [s.jsx(st, {
            size: 26
          }), Te]
        }, I))
      }), a && s.jsx("div", {
        className: "flex flex-wrap gap-2",
        children: ((n == null ? void 0 : n.repairs[a]) ?? []).map(I => s.jsx("button", {
          type: "button",
          onClick: () => d({
            ...c,
            description: J(I)
          }),
          className: "min-h-[44px] rounded-xl bg-brand-soft px-3 font-semibold text-brand",
          children: J(I)
        }, I))
      }), (u == null ? void 0 : u.initial_price) != null && s.jsxs("p", {
        className: "rounded-xl bg-brand-soft p-3 text-sm font-semibold",
        children: [Z("تقدير مبدئي للمراجعة: {0} {1}", u.initial_price, ((X = i.data) == null ? void 0 : X.finance.currency) ?? ""), s.jsx("span", {
          className: "mt-1 block text-xs font-normal",
          children: l("لا يُضاف هذا التقدير إلى الفاتورة تلقائيًا.")
        })]
      }), s.jsx(E, {
        label: l("الوصف"),
        children: s.jsx("input", {
          value: c.description,
          onChange: I => d({
            ...c,
            description: I.target.value
          })
        })
      }), s.jsxs("div", {
        className: "grid gap-3 sm:grid-cols-3",
        children: [s.jsxs("div", {
          children: [s.jsx(E, {
            label: l("الفني"),
            children: s.jsxs("select", {
              disabled: !h.length,
              value: p,
              onChange: I => d({
                ...c,
                technician_id: I.target.value
              }),
              children: [s.jsx("option", {
                value: "",
                children: "—"
              }), h.map(I => s.jsx("option", {
                value: I.id,
                children: I.name
              }, I.id))]
            })
          }), !h.length && s.jsx("a", {
            href: "#job-technicians",
            className: "mt-1 block text-sm font-semibold text-brand underline",
            children: l("أضف فنيًا لأمر الشغل من قسم الفنيين أولًا")
          })]
        }), s.jsx(E, {
          label: l("ساعات العمل"),
          children: s.jsx("input", {
            type: "number",
            step: "0.25",
            min: 0,
            value: c.labor_hours,
            onChange: I => d({
              ...c,
              labor_hours: I.target.value
            }),
            dir: "ltr"
          })
        }), s.jsxs("div", {
          children: [s.jsx(E, {
            label: l("سعر الساعة"),
            children: s.jsx("input", {
              type: "number",
              readOnly: !0,
              value: ((te = i.data) == null ? void 0 : te.finance.default_labor_rate) ?? "",
              dir: "ltr",
              className: "!bg-slate-50"
            })
          }), s.jsx("p", {
            className: "mt-1 text-xs text-slate-500",
            children: l("السعر من إعدادات الورشة")
          }), s.jsx("a", {
            href: "/settings",
            className: "mt-1 inline-block text-xs font-semibold text-brand underline",
            children: l("تعديل سعر الساعة في الإعدادات")
          })]
        })]
      }), s.jsx($, {
        message: (L = m.error) == null ? void 0 : L.message
      }), s.jsx(P, {
        icon: ts,
        disabled: c.description.length < 2 || m.isPending,
        onClick: () => m.mutate(),
        children: l("إضافة")
      })]
    })]
  });
}
function kw({
  job: e,
  refresh: t,
  tpl: n
}) {
  var u;
  const [r, i] = w.useState(""),
    [a, o] = w.useState({}),
    c = V({
      mutationFn: () => M.post(`/api/jobs/${e.id}/inspections`, {
        category: r,
        items: Object.entries(a).map(([h, p]) => ({
          name: h,
          status: p
        }))
      }),
      onSuccess: () => {
        i(""), o({}), t();
      }
    }),
    d = e.status === "delivered" || e.status === "cancelled";
  return s.jsxs(B, {
    title: Z("الفحص ({0})", e.inspections.length),
    children: [e.inspections.map(h => {
      var p;
      return s.jsxs("div", {
        className: "mb-4",
        children: [s.jsx("p", {
          className: "mb-1 text-lg font-extrabold",
          children: ((p = Er(h.category)) == null ? void 0 : p.label) ?? h.category
        }), s.jsx("ul", {
          className: "grid gap-2 sm:grid-cols-2",
          children: h.items.map(m => s.jsxs("li", {
            className: `rounded-xl border-2 px-3 py-2 font-bold ${Ao[m.status]}`,
            children: [Rp[m.status], " ", m.name, " — ", Pa[m.status]]
          }, J(m.name)))
        })]
      }, h.id);
    }), !d && s.jsxs("div", {
      className: "space-y-3",
      children: [s.jsx(E, {
        label: l("فحص جديد"),
        children: s.jsxs("select", {
          value: r,
          onChange: h => {
            i(h.target.value), o({});
          },
          children: [s.jsx("option", {
            value: "",
            children: l("اختار نوع الفحص")
          }), Object.keys((n == null ? void 0 : n.inspections) ?? {}).map(h => {
            var p;
            return s.jsx("option", {
              value: h,
              children: ((p = Er(h)) == null ? void 0 : p.label) ?? {
                fluids: l("السوائل"),
                lights: l("الإضاءة"),
                safety: l("معدات الأمان")
              }[h] ?? h
            }, h);
          })]
        })
      }), r && s.jsxs("div", {
        className: "flex flex-wrap items-center justify-between gap-2",
        children: [s.jsx("div", {
          className: "flex gap-3 text-sm font-bold",
          "aria-hidden": !0,
          children: ["good", "attention", "critical"].map(h => s.jsxs("span", {
            className: "inline-flex items-center gap-1",
            children: [s.jsx("span", {
              className: `h-4 w-4 rounded-full border-2 ${Ao[h]}`
            }), Pa[h]]
          }, h))
        }), s.jsx(P, {
          kind: "secondary",
          icon: jl,
          onClick: () => o(Object.fromEntries(((n == null ? void 0 : n.inspections[r]) ?? []).map(h => [h, a[h] ?? "good"]))),
          children: l("الكل سليم")
        })]
      }), r && ((n == null ? void 0 : n.inspections[r]) ?? []).map(h => s.jsxs("div", {
        className: "flex flex-wrap items-center justify-between gap-2 rounded-xl bg-slate-50 p-3",
        children: [s.jsx("span", {
          className: "text-lg font-bold",
          children: h
        }), s.jsx("div", {
          className: "flex flex-wrap gap-2",
          children: Object.keys(Pa).map(p => s.jsxs("button", {
            type: "button",
            "aria-pressed": a[h] === p,
            onClick: () => o({
              ...a,
              [h]: p
            }),
            className: `min-h-[44px] rounded-xl border-2 px-3 font-bold ${a[h] === p ? Ao[p] : "border-slate-200 bg-white"}`,
            children: [Rp[p], " ", Pa[p]]
          }, p))
        })]
      }, h)), s.jsx($, {
        message: (u = c.error) == null ? void 0 : u.message
      }), r && s.jsx(P, {
        icon: jl,
        disabled: !Object.keys(a).length || c.isPending,
        onClick: () => c.mutate(),
        children: l("حفظ الفحص")
      })]
    })]
  });
}
function Nw({
  job: e,
  refresh: t,
  techs: n
}) {
  var d, u;
  const [r, i] = w.useState(""),
    a = V({
      mutationFn: () => M.post(`/api/jobs/${e.id}/assign`, {
        technician_id: Number(r)
      }),
      onSuccess: () => {
        i(""), t();
      }
    }),
    o = V({
      mutationFn: h => M.post(`/api/jobs/${e.id}/unassign`, {
        technician_id: h
      }),
      onSuccess: t
    }),
    c = e.status === "delivered" || e.status === "cancelled";
  return s.jsxs(B, {
    title: l("الفنيين"),
    children: [s.jsxs("div", {
      className: "flex flex-wrap gap-2",
      children: [e.technicians.map(h => s.jsxs("span", {
        className: "inline-flex items-center gap-2 rounded-full bg-brand-soft px-4 py-2 font-bold text-brand",
        children: [h.name, !c && s.jsx("button", {
          "aria-label": l("إزالة"),
          onClick: () => o.mutate(h.id),
          children: "✖"
        })]
      }, h.id)), !e.technicians.length && s.jsx("span", {
        className: "text-slate-500",
        children: l("لم يُحدد فني")
      })]
    }), !c && s.jsxs("div", {
      className: "mt-3 flex gap-2",
      children: [s.jsxs("select", {
        value: r,
        onChange: h => i(h.target.value),
        "aria-label": l("اختار فني"),
        children: [s.jsx("option", {
          value: "",
          children: l("إضافة فني…")
        }), n.filter(h => !e.technicians.some(p => p.id === h.id)).map(h => s.jsx("option", {
          value: h.id,
          children: h.name
        }, h.id))]
      }), s.jsx(P, {
        disabled: !r,
        onClick: () => a.mutate(),
        children: l("إضافة")
      })]
    }), s.jsx("div", {
      className: "mt-2",
      children: s.jsx($, {
        message: ((d = a.error) == null ? void 0 : d.message) ?? ((u = o.error) == null ? void 0 : u.message)
      })
    })]
  });
}
// Recovered route component for /jobs/:id; original filename/name unknown.
function _w() {
  const {
    id: e = ""
  } = Ds();
  return s.jsx(Cw, {
    id: e
  }, e);
}
function Cw({
  id: e
}) {
  var h, p, m, y;
  const {
      can: t
    } = ce(),
    {
      q: n,
      refresh: r
    } = jw(e),
    i = W({
      queryKey: ["templates"],
      queryFn: () => M.get("/api/templates")
    }),
    a = W({
      queryKey: ["techs", !0],
      queryFn: () => M.get("/api/technicians?active=true")
    }),
    o = W({
      queryKey: ["readiness", e, (h = n.data) == null ? void 0 : h.status, (p = n.data) == null ? void 0 : p.version],
      enabled: ((m = n.data) == null ? void 0 : m.status) === "ready" && t("billing.read"),
      queryFn: () => M.get(`/api/jobs/${e}/delivery-readiness`)
    }),
    [c, d] = w.useState(!1);
  if (w.useEffect(() => {
    n.data && !o.isLoading && d(!0);
  }, [n.data, o.isLoading]), n.isLoading || !c && o.isLoading) return s.jsx(ie, {});
  if (n.error || !n.data) return s.jsx($, {
    message: ((y = n.error) == null ? void 0 : y.message) ?? l("غير موجود")
  });
  const u = n.data;
  return s.jsxs(s.Fragment, {
    children: [s.jsxs(B, {
      action: s.jsx("div", {
        className: "no-print flex gap-2",
        children: s.jsxs(re, {
          to: `/jobs/${u.id}/receipt`,
          className: "inline-flex min-h-[56px] items-center gap-2 rounded-2xl border-2 border-slate-300 bg-white px-5 text-lg font-bold",
          children: [s.jsx(fn, {
            size: 22
          }), l("إيصال الاستلام")]
        })
      }),
      children: [s.jsxs("p", {
        className: "text-slate-500",
        children: [l("أمر صيانة #"), u.visit_no, " · ", $e(u.arrival_at)]
      }), s.jsx(re, {
        to: `/vehicles/${u.vehicle.id}`,
        className: "text-4xl font-extrabold hover:text-brand",
        dir: "ltr",
        children: u.vehicle.plate ?? "—"
      }), s.jsxs("p", {
        className: "text-2xl font-bold",
        children: [u.vehicle.make, " ", u.vehicle.model, " — ", u.customer.name, " ", s.jsx("span", {
          dir: "ltr",
          className: "text-lg text-slate-500",
          children: u.customer.mobile
        })]
      }), u.complaint && s.jsxs("p", {
        className: "mt-2 text-lg",
        children: [s.jsx("b", {
          children: l("الشكوى:")
        }), " ", u.complaint]
      })]
    }), s.jsx(uw, {
      initial: Ly(u, t, o.data).target,
      summary: s.jsx(Cp, {
        job: u,
        can: t,
        readiness: o.data,
        compact: !0
      }),
      sections: [...(t("visits.write") ? [{
        id: "job-technicians",
        label: l("الفنيين"),
        count: u.technicians.length,
        content: s.jsxs(s.Fragment, {
          children: [s.jsx(Nw, {
            job: u,
            refresh: r,
            techs: a.data ?? []
          }), s.jsx(bw, {
            job: u,
            refresh: r
          })]
        })
      }] : []), {
        id: "job-inspections",
        label: l("الفحص (اختياري)"),
        count: u.inspections.length,
        content: s.jsx(kw, {
          job: u,
          refresh: r,
          tpl: i.data
        })
      }, {
        id: "job-parts",
        label: l("قطع الغيار"),
        content: s.jsx(fw, {
          job: u,
          techs: a.data ?? []
        })
      }, {
        id: "job-quotes",
        label: l("عروض الأسعار"),
        content: s.jsx(mw, {
          job: u
        })
      }, {
        id: "job-operations",
        label: l("الإصلاح"),
        count: u.operations.filter(j => j.status !== "cancelled").length,
        content: s.jsx(ww, {
          job: u,
          refresh: r,
          tpl: i.data,
          techs: a.data ?? []
        })
      }, ...(u.status !== "cancelled" && u.status !== "delivered" && t("qc.write") ? [{
        id: "job-quality",
        label: l("فحص الجودة"),
        content: s.jsx(Sp, {
          job: u,
          view: "quality"
        })
      }] : []), ...(t("billing.read") ? [{
        id: "job-invoices",
        label: l("الفواتير والدفع"),
        content: s.jsx(hw, {
          job: u
        })
      }] : []), ...(u.status !== "cancelled" && (t("delivery.write") || u.status === "delivered") ? [{
        id: "job-delivery",
        anchors: ["vehicle-delivery"],
        label: l("تسليم العربية"),
        content: s.jsx(Sp, {
          job: u,
          view: "delivery"
        })
      }] : []), {
        id: "job-attachments",
        label: l("المرفقات"),
        content: s.jsx(Ru, {
          ownerType: "visit",
          ownerId: u.id
        })
      }, {
        id: "job-warranty",
        label: l("الضمان"),
        content: s.jsx(yw, {
          job: u
        })
      }, {
        id: "job-history",
        label: l("سجل الحالات"),
        count: u.status_history.length,
        content: s.jsx(B, {
          title: l("سجل الحالات"),
          children: s.jsx("ol", {
            className: "space-y-2",
            children: [...u.status_history].reverse().map((j, v) => s.jsxs("li", {
              className: "flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 p-3",
              children: [s.jsx(Pr, {
                status: j.to
              }), s.jsx("span", {
                className: "text-slate-600",
                children: new Date(j.at).toLocaleString($t)
              }), s.jsx("span", {
                className: "font-semibold",
                children: j.by
              }), j.reason && s.jsxs("span", {
                className: "text-slate-700",
                children: ["— ", J(j.reason)]
              })]
            }, v))
          })
        })
      }],
      children: s.jsx(Cp, {
        job: u,
        can: t,
        readiness: o.data
      })
    }, u.id)]
  });
}
function ad({
  className: e = ""
}) {
  const t = Et === "ar" ? "en" : "ar";
  return s.jsxs("button", {
    type: "button",
    onClick: () => qb(t),
    lang: t,
    "aria-label": t === "en" ? "Switch to English" : "التبديل إلى العربية",
    className: `inline-flex min-h-[48px] items-center gap-2 rounded-xl bg-white/10 px-4 text-lg font-bold ${e}`,
    children: [s.jsx(Cb, {
      size: 22,
      "aria-hidden": !0
    }), t === "en" ? "English" : "العربية"]
  });
}
const Sw = [l("الورشة"), l("حساب المدير"), l("الحسابات"), l("النسخ الاحتياطي")];
function Ew() {
  const {
      setup: e
    } = ce(),
    [t, n] = w.useState(0),
    [r, i] = w.useState({
      name: "",
      phone: "",
      address: ""
    }),
    [a, o] = w.useState({
      username: "",
      full_name: "",
      password: "",
      again: ""
    }),
    [c, d] = w.useState({
      currency: "QAR",
      tax: "0"
    }),
    [u, h] = w.useState(""),
    [p, m] = w.useState(""),
    [y, j] = w.useState(!1),
    v = [r.name.trim().length >= 2, a.username.length >= 3 && a.full_name.length >= 2 && a.password.length >= 8 && a.password === a.again, /^[A-Za-z]{3}$/.test(c.currency), !0][t],
    N = async () => {
      m(""), j(!0);
      try {
        await e(a.username, a.full_name, a.password, {
          workshop: {
            name: r.name,
            phone: r.phone,
            address: r.address
          },
          currency: c.currency.toUpperCase(),
          default_tax_rate: Number(c.tax) || 0,
          backup_dir: u.trim() || null,
          language: Et
        });
      } catch (f) {
        m(f.message);
      } finally {
        j(!1);
      }
    },
    x = f => {
      f.preventDefault(), t < 3 ? v && n(t + 1) : N();
    };
  return s.jsxs("form", {
    onSubmit: x,
    className: "w-full max-w-lg space-y-5 rounded-3xl bg-white p-8 shadow-xl",
    children: [s.jsxs("div", {
      className: "flex flex-col items-center gap-2 text-brand",
      children: [s.jsx(un, {
        size: 72
      }), s.jsx("h1", {
        className: "text-3xl font-extrabold",
        children: l("أهلاً بك في أوتو كير برو")
      }), s.jsx("p", {
        className: "text-lg font-semibold text-slate-600",
        children: l("إعداد النظام لأول مرة")
      })]
    }), s.jsx("ol", {
      className: "flex gap-1",
      "aria-label": l("خطوات الإعداد"),
      children: Sw.map((f, g) => s.jsxs("li", {
        "aria-current": g === t,
        className: `flex-1 rounded-lg p-1 text-center text-xs font-bold sm:text-sm ${g < t ? "bg-ok-soft text-ok" : g === t ? "bg-brand text-white" : "bg-slate-200 text-slate-600"}`,
        children: [g < t ? "✔ " : "", f]
      }, f))
    }), t === 0 && s.jsxs("div", {
      className: "space-y-4",
      children: [s.jsx(E, {
        label: l("اسم الورشة"),
        children: s.jsx("input", {
          value: r.name,
          onChange: f => i({
            ...r,
            name: f.target.value
          }),
          autoFocus: !0
        })
      }), s.jsx(E, {
        label: l("رقم التليفون"),
        children: s.jsx("input", {
          value: r.phone,
          onChange: f => i({
            ...r,
            phone: f.target.value
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("العنوان"),
        children: s.jsx("input", {
          value: r.address,
          onChange: f => i({
            ...r,
            address: f.target.value
          })
        })
      })]
    }), t === 1 && s.jsxs("div", {
      className: "space-y-4",
      children: [s.jsx(E, {
        label: l("اسم المستخدم (إنجليزي)"),
        children: s.jsx("input", {
          value: a.username,
          onChange: f => o({
            ...a,
            username: f.target.value
          }),
          dir: "ltr",
          autoComplete: "username"
        })
      }), s.jsx(E, {
        label: l("الاسم بالكامل"),
        children: s.jsx("input", {
          value: a.full_name,
          onChange: f => o({
            ...a,
            full_name: f.target.value
          })
        })
      }), s.jsx(E, {
        label: l("كلمة المرور (٨ حروف أو أرقام على الأقل)"),
        children: s.jsx("input", {
          type: "password",
          value: a.password,
          onChange: f => o({
            ...a,
            password: f.target.value
          }),
          dir: "ltr",
          autoComplete: "new-password"
        })
      }), s.jsx(E, {
        label: l("أعد كتابة كلمة المرور"),
        error: a.again && a.again !== a.password ? l("غير متطابقة") : void 0,
        children: s.jsx("input", {
          type: "password",
          value: a.again,
          onChange: f => o({
            ...a,
            again: f.target.value
          }),
          dir: "ltr",
          autoComplete: "new-password"
        })
      })]
    }), t === 2 && s.jsxs("div", {
      className: "space-y-4",
      children: [s.jsx(E, {
        label: l("العملة (٣ حروف مثل QAR)"),
        children: s.jsx("input", {
          value: c.currency,
          onChange: f => d({
            ...c,
            currency: f.target.value.toUpperCase()
          }),
          dir: "ltr",
          maxLength: 3
        })
      }), s.jsx(E, {
        label: l("نسبة الضريبة % (اتركها ٠ لو لا توجد ضريبة)"),
        children: s.jsx("input", {
          type: "number",
          min: 0,
          max: 100,
          step: "0.01",
          value: c.tax,
          onChange: f => d({
            ...c,
            tax: f.target.value
          }),
          dir: "ltr"
        })
      })]
    }), t === 3 && s.jsxs("div", {
      className: "space-y-4",
      children: [s.jsx(E, {
        label: l("مكان حفظ النسخ الاحتياطية — يُفضّل فلاشة أو قرص خارجي (اختياري الآن)"),
        children: s.jsx("input", {
          value: u,
          onChange: f => h(f.target.value),
          dir: "ltr",
          placeholder: "D:\\Backups"
        })
      }), s.jsx("p", {
        className: "rounded-2xl bg-slate-50 p-3 text-slate-600",
        children: l("للتشغيل على أكتر من جهاز في الورشة (شبكة محلية) راجع دليل التثبيت. اللغة العربية والواجهة جاهزة، ويمكن تعديل كل ده لاحقاً من الإعدادات.")
      })]
    }), s.jsx($, {
      message: p
    }), s.jsxs("div", {
      className: "flex justify-between gap-3",
      children: [s.jsx(P, {
        kind: "secondary",
        icon: qi ? Ii : vl,
        disabled: t === 0,
        onClick: () => n(t - 1),
        children: l("السابق")
      }), t < 3 ? s.jsx(P, {
        type: "submit",
        icon: qi ? vl : Ii,
        disabled: !v,
        children: l("التالي")
      }) : s.jsx(P, {
        type: "submit",
        icon: Wx,
        disabled: y,
        children: l("إنهاء وبدء")
      })]
    })]
  });
}
// Recovered route component for /login; original filename/name unknown.
function Pw() {
  const {
      user: e,
      loading: t,
      setupNeeded: n,
      login: r
    } = ce(),
    [i, a] = w.useState(""),
    [o, c] = w.useState(""),
    [d, u] = w.useState(""),
    [h, p] = w.useState(!1);
  if (t) return s.jsx(ie, {});
  if (e) return s.jsx(hu, {
    to: "/",
    replace: !0
  });
  if (n) return s.jsxs("div", {
    className: "flex min-h-screen items-center justify-center p-4",
    children: [s.jsx("div", {
      className: "absolute end-4 top-4 text-brand",
      children: s.jsx(ad, {
        className: "!bg-brand/10"
      })
    }), s.jsx(Ew, {})]
  });
  const m = async y => {
    y.preventDefault(), u(""), p(!0);
    try {
      await r(i, o);
    } catch (j) {
      u(j.message);
    } finally {
      p(!1);
    }
  };
  return s.jsxs("div", {
    className: "flex min-h-screen items-center justify-center p-4",
    children: [s.jsx("div", {
      className: "absolute end-4 top-4 text-brand",
      children: s.jsx(ad, {
        className: "!bg-brand/10"
      })
    }), s.jsxs("form", {
      onSubmit: m,
      className: "w-full max-w-md space-y-5 rounded-3xl bg-white p-8 shadow-xl",
      children: [s.jsxs("div", {
        className: "flex flex-col items-center gap-2 text-brand",
        children: [s.jsx(un, {
          size: 72
        }), s.jsx("h1", {
          className: "text-3xl font-extrabold",
          children: l("أوتو كير برو")
        }), s.jsx("p", {
          className: "text-lg font-semibold text-slate-600",
          children: l("تسجيل الدخول")
        })]
      }), s.jsx(E, {
        label: l("اسم المستخدم"),
        children: s.jsx("input", {
          value: i,
          onChange: y => a(y.target.value),
          autoComplete: "username",
          required: !0,
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("كلمة المرور"),
        children: s.jsx("input", {
          type: "password",
          value: o,
          onChange: y => c(y.target.value),
          autoComplete: "current-password",
          required: !0,
          dir: "ltr"
        })
      }), s.jsx($, {
        message: d
      }), s.jsx(P, {
        type: "submit",
        icon: Sb,
        disabled: h,
        children: l("دخول")
      })]
    })]
  });
}
const Xl = {
    dent: {
      label: l("طعجة"),
      color: "#ea580c"
    },
    scratch: {
      label: l("خدش"),
      color: "#ca8a04"
    },
    rust: {
      label: l("صدأ"),
      color: "#92400e"
    },
    crack: {
      label: l("شرخ"),
      color: "#7c3aed"
    },
    broken: {
      label: l("كسر"),
      color: "#dc2626"
    },
    other: {
      label: l("أخرى"),
      color: "#475569"
    }
  },
  Mp = {
    tire_pressure: {
      label: l("ضغط الكفرات"),
      icon: "◎"
    },
    traction: {
      label: l("الثبات"),
      icon: "⚠"
    },
    abs: {
      label: "ABS",
      icon: "ⓐ"
    },
    check_engine: {
      label: l("لمبة المحرك"),
      icon: "⚙"
    },
    airbag: {
      label: l("الوسادة الهوائية"),
      icon: "☺"
    },
    oil_pressure: {
      label: l("ضغط الزيت"),
      icon: "🛢"
    },
    battery: {
      label: l("البطارية"),
      icon: "🔋"
    },
    brake: {
      label: l("الفرامل"),
      icon: "⊙"
    },
    temperature: {
      label: l("حرارة المحرك"),
      icon: "🌡"
    }
  },
  Rw = [{
    key: "front_bumper",
    d: "M66 30 Q110 6 154 30 L158 46 Q110 26 62 46 Z"
  }, {
    key: "headlights",
    d: "M62 54 Q70 44 90 46 L87 62 Q72 62 64 70 Z M158 54 Q150 44 130 46 L133 62 Q148 62 156 70 Z"
  }, {
    key: "windshield",
    d: "M76 112 Q110 98 144 112 L138 152 Q110 142 82 152 Z"
  }, {
    key: "left_side",
    d: "M54 160 Q50 190 50 232 Q50 290 56 336 L72 336 Q70 290 70 232 Q70 190 72 160 Z"
  }, {
    key: "right_side",
    d: "M166 160 Q170 190 170 232 Q170 290 164 336 L148 336 Q150 290 150 232 Q150 190 148 160 Z"
  }, {
    key: "taillights",
    d: "M64 372 Q74 380 90 378 L88 394 Q72 396 66 388 Z M156 372 Q146 380 130 378 L132 394 Q148 396 154 388 Z"
  }, {
    key: "rear_bumper",
    d: "M64 398 Q110 420 156 398 L152 414 Q110 434 68 414 Z"
  }, {
    key: "tires",
    d: "M38 74 h15 v50 q0 5 -5 5 h-5 q-5 0 -5 -5 Z M167 74 h15 v50 q0 5 -5 5 h-5 q-5 0 -5 -5 Z M38 286 h15 v52 q0 5 -5 5 h-5 q-5 0 -5 -5 Z M167 286 h15 v52 q0 5 -5 5 h-5 q-5 0 -5 -5 Z"
  }];
function zy({
  condition: e,
  selected: t,
  onSelect: n
}) {
  return s.jsxs("svg", {
    viewBox: "0 0 242 387",
    role: "group",
    "aria-label": l("رسم العربية"),
    className: "mx-auto w-full max-w-[280px] drop-shadow-md",
    children: [s.jsxs("defs", {
      children: [s.jsxs("linearGradient", {
        id: "car-body",
        x1: "0",
        x2: "1",
        children: [s.jsx("stop", {
          offset: "0",
          stopColor: "#94a3b8"
        }), s.jsx("stop", {
          offset: ".35",
          stopColor: "#e2e8f0"
        }), s.jsx("stop", {
          offset: ".65",
          stopColor: "#f8fafc"
        }), s.jsx("stop", {
          offset: "1",
          stopColor: "#94a3b8"
        })]
      }), s.jsxs("linearGradient", {
        id: "car-glass",
        x1: "0",
        y1: "0",
        x2: "0",
        y2: "1",
        children: [s.jsx("stop", {
          offset: "0",
          stopColor: "#7dd3fc"
        }), s.jsx("stop", {
          offset: "1",
          stopColor: "#1e3a8a"
        })]
      }), s.jsxs("linearGradient", {
        id: "car-roof",
        x1: "0",
        x2: "1",
        children: [s.jsx("stop", {
          offset: "0",
          stopColor: "#cbd5e1"
        }), s.jsx("stop", {
          offset: ".5",
          stopColor: "#f1f5f9"
        }), s.jsx("stop", {
          offset: "1",
          stopColor: "#cbd5e1"
        })]
      }), s.jsxs("radialGradient", {
        id: "car-shadow",
        children: [s.jsx("stop", {
          offset: "0",
          stopColor: "#0f172a",
          stopOpacity: ".28"
        }), s.jsx("stop", {
          offset: "1",
          stopColor: "#0f172a",
          stopOpacity: "0"
        })]
      })]
    }), s.jsxs("g", {
      transform: "scale(1.1 .88)",
      children: [s.jsx("ellipse", {
        cx: "110",
        cy: "228",
        rx: "92",
        ry: "210",
        fill: "url(#car-shadow)"
      }), s.jsxs("g", {
        fill: "#1e293b",
        children: [s.jsx("rect", {
          x: "38",
          y: "74",
          width: "15",
          height: "55",
          rx: "6"
        }), s.jsx("rect", {
          x: "167",
          y: "74",
          width: "15",
          height: "55",
          rx: "6"
        }), s.jsx("rect", {
          x: "38",
          y: "286",
          width: "15",
          height: "57",
          rx: "6"
        }), s.jsx("rect", {
          x: "167",
          y: "286",
          width: "15",
          height: "57",
          rx: "6"
        })]
      }), s.jsx("path", {
        d: "M62 128 Q46 124 44 134 Q48 142 62 140 Z M158 128 Q174 124 176 134 Q172 142 158 140 Z",
        fill: "#94a3b8",
        stroke: "#64748b",
        strokeWidth: "1.5"
      }), s.jsx("path", {
        d: "M110 12 C146 12 164 30 168 58 C172 92 174 128 174 168 L175 238 C175 290 174 336 168 372 C163 402 144 424 110 426 C76 424 57 402 52 372 C46 336 45 290 45 238 L46 168 C46 128 48 92 52 58 C56 30 74 12 110 12 Z",
        fill: "url(#car-body)",
        stroke: "#475569",
        strokeWidth: "2.5",
        strokeLinejoin: "round"
      }), s.jsx("path", {
        d: "M72 70 Q110 58 148 70 M70 96 Q110 86 150 96",
        fill: "none",
        stroke: "#94a3b8",
        strokeWidth: "1.5",
        opacity: ".8"
      }), s.jsx("path", {
        d: "M76 346 Q110 354 144 346 M80 364 Q110 370 140 364",
        fill: "none",
        stroke: "#94a3b8",
        strokeWidth: "1.5",
        opacity: ".8"
      }), s.jsx("path", {
        d: "M76 112 Q110 98 144 112 L138 152 Q110 142 82 152 Z",
        fill: "url(#car-glass)",
        stroke: "#334155",
        strokeWidth: "2"
      }), s.jsx("path", {
        d: "M80 296 Q110 288 140 296 L146 330 Q110 342 74 330 Z",
        fill: "url(#car-glass)",
        stroke: "#334155",
        strokeWidth: "2"
      }), s.jsx("path", {
        d: "M82 154 Q110 146 138 154 L140 292 Q110 286 80 292 Z",
        fill: "url(#car-roof)",
        stroke: "#94a3b8",
        strokeWidth: "2"
      }), s.jsx("path", {
        d: "M92 170 Q110 166 128 170 M92 276 Q110 272 128 276",
        fill: "none",
        stroke: "#cbd5e1",
        strokeWidth: "2",
        strokeLinecap: "round"
      }), s.jsx("path", {
        d: "M74 156 L74 292 M146 156 L146 292 M74 222 L146 222",
        fill: "none",
        stroke: "#94a3b8",
        strokeWidth: "1.2",
        opacity: ".7"
      }), s.jsx("path", {
        d: "M68 190 h5 M68 252 h5 M147 190 h5 M147 252 h5",
        stroke: "#64748b",
        strokeWidth: "3",
        strokeLinecap: "round"
      }), s.jsx("path", {
        d: "M62 54 Q70 44 90 46 L87 62 Q72 62 64 70 Z M158 54 Q150 44 130 46 L133 62 Q148 62 156 70 Z",
        fill: "#fef9c3",
        stroke: "#a16207",
        strokeWidth: "1.5"
      }), s.jsx("path", {
        d: "M64 372 Q74 380 90 378 L88 394 Q72 396 66 388 Z M156 372 Q146 380 130 378 L132 394 Q148 396 154 388 Z",
        fill: "#fca5a5",
        stroke: "#991b1b",
        strokeWidth: "1.5"
      }), Rw.map(r => {
        var d;
        const i = e[r.key],
          a = (i == null ? void 0 : i.state) === "damaged",
          o = a || (i == null ? void 0 : i.state) === "ok",
          c = a ? ((d = Xl[(i == null ? void 0 : i.kind) ?? "other"]) == null ? void 0 : d.color) ?? "#dc2626" : (i == null ? void 0 : i.state) === "ok" ? "#16a34a" : "#2563eb";
        return s.jsx("path", {
          d: r.d,
          role: "button",
          tabIndex: 0,
          "aria-label": r.key,
          "aria-pressed": t === r.key,
          onClick: () => n(r.key),
          onKeyDown: u => (u.key === "Enter" || u.key === " ") && n(r.key),
          fill: c,
          style: o ? {
            fillOpacity: a ? .72 : .45
          } : void 0,
          className: `cursor-pointer outline-none transition ${o ? "" : "[fill-opacity:0] hover:![fill-opacity:.35] focus-visible:![fill-opacity:.35]"}`,
          stroke: t === r.key ? "#0f172a" : a ? c : "transparent",
          strokeWidth: t === r.key ? 3 : 1.5,
          strokeDasharray: t === r.key ? "5 3" : void 0
        }, r.key);
      })]
    })]
  });
}
function Iy({
  value: e,
  onChange: t
}) {
  const n = i => t == null ? void 0 : t(e.includes(i) ? e.filter(a => a !== i) : [...e, i]),
    r = t ? Object.keys(Mp) : e;
  return s.jsx("div", {
    className: "flex flex-wrap gap-2",
    children: r.map(i => {
      const a = e.includes(i),
        o = Mp[i] ?? {
          label: i,
          icon: "•"
        };
      return s.jsxs("button", {
        type: "button",
        disabled: !t,
        "aria-pressed": a,
        onClick: () => n(i),
        className: `flex min-h-[64px] min-w-[84px] flex-col items-center justify-center rounded-2xl border-4 px-2 text-sm font-bold ${a ? "border-bad bg-bad-soft text-bad" : "border-slate-200 bg-white text-slate-500"}`,
        children: [s.jsx("span", {
          className: "text-2xl",
          "aria-hidden": !0,
          children: o.icon
        }), o.label]
      }, i);
    })
  });
}
function Mw({
  points: e
}) {
  if (e.length < 2) return s.jsx("p", {
    className: "text-sm text-slate-500",
    children: l("لا توجد بيانات كافية للرسم")
  });
  const t = e.map(h => h.x),
    n = e.map(h => h.y),
    [r, i, a, o] = [Math.min(...t), Math.max(...t), Math.min(...n), Math.max(...n)],
    c = h => 6 + (h - r) / (i - r || 1) * 228,
    d = h => 54 - (h - a) / (o - a || 1) * 48,
    u = e.map(h => `${c(h.x).toFixed(1)},${d(h.y).toFixed(1)}`).join(" ");
  return s.jsxs("svg", {
    viewBox: "0 0 240 60",
    role: "img",
    "aria-label": l("تطور قراءة العداد"),
    className: "w-full",
    style: {
      direction: "ltr"
    },
    children: [s.jsx("polyline", {
      points: u,
      fill: "none",
      stroke: "#2563eb",
      strokeWidth: "2.5",
      strokeLinejoin: "round"
    }), e.map((h, p) => s.jsx("circle", {
      cx: c(h.x),
      cy: d(h.y),
      r: "3.5",
      fill: "#2563eb"
    }, p))]
  });
}
function Tw({
  score: e,
  level: t
}) {
  const n = t === "good" ? "#16a34a" : t === "fair" ? "#ca8a04" : "#dc2626";
  return s.jsx("div", {
    role: "meter",
    "aria-valuemin": 0,
    "aria-valuemax": 100,
    "aria-valuenow": e,
    "aria-label": l("صحة العربية"),
    className: "h-4 w-full overflow-hidden rounded-full bg-slate-200",
    children: s.jsx("div", {
      className: "h-full rounded-full",
      style: {
        width: `${e}%`,
        background: n
      }
    })
  });
}
const Qa = "autocare.reception.draft",
  Fw = [l("العميل"), l("العربية"), l("حالة العربية"), l("الشكوى"), l("تأكيد")],
  ii = {
    front_bumper: l("الصدام الأمامي"),
    rear_bumper: l("الصدام الخلفي"),
    left_side: l("الجنب الشمال"),
    right_side: l("الجنب اليمين"),
    windshield: l("الزجاج الأمامي"),
    headlights: l("الفوانيس الأمامية"),
    taillights: l("الفوانيس الخلفية"),
    tires: l("الكفرات"),
    interior: l("الداخلية"),
    dashboard: l("التابلوه"),
    scratches_dents: l("خدوش وطعجات")
  },
  ld = {
    empty: l("فاضي"),
    quarter: l("ربع"),
    half: l("نص"),
    three_quarters: l("تلات أرباع"),
    full: l("فل")
  },
  od = {
    step: 0,
    mileage: "",
    fuel: "half",
    condition: {},
    lights: [],
    categories: [],
    complaintText: "",
    belongings: "",
    technicianId: "",
    notes: ""
  };
function Lw() {
  try {
    return {
      ...od,
      ...JSON.parse(localStorage.getItem(Qa) ?? "{}")
    };
  } catch {
    return od;
  }
}
function Zr({
  on: e,
  onClick: t,
  children: n
}) {
  return s.jsxs("button", {
    type: "button",
    onClick: t,
    "aria-pressed": e,
    className: `min-h-[56px] rounded-2xl border-4 px-4 text-lg font-bold ${e ? "border-brand bg-brand-soft text-brand" : "border-slate-200 bg-white"}`,
    children: [e && "✔ ", n]
  });
}
function Dw({
  d: e,
  set: t
}) {
  var h, p;
  const [n, r] = w.useState(""),
    [i, a] = w.useState(!1),
    [o, c] = w.useState({
      full_name: "",
      mobile: ""
    }),
    d = W({
      queryKey: ["rc-cust", n],
      enabled: n.length >= 2,
      queryFn: () => M.get(`/api/customers${Re({
        q: n,
        limit: 6
      })}`)
    }),
    u = V({
      mutationFn: m => M.post(`/api/customers${m ? "?force=true" : ""}`, o),
      onSuccess: m => t({
        customer: m,
        vehicle: void 0
      })
    });
  return e.customer ? s.jsxs("div", {
    className: "flex items-center justify-between rounded-2xl bg-ok-soft p-5 text-xl font-bold text-ok",
    children: ["✔ ", e.customer.full_name, " ", s.jsx("span", {
      dir: "ltr",
      children: e.customer.mobile
    }), s.jsx("button", {
      className: "underline",
      onClick: () => t({
        customer: void 0,
        vehicle: void 0
      }),
      children: l("تغيير")
    })]
  }) : s.jsxs("div", {
    className: "space-y-4",
    children: [s.jsx(E, {
      label: l("ابحث عن العميل بالاسم أو الموبايل"),
      children: s.jsx("input", {
        value: n,
        onChange: m => r(m.target.value)
      })
    }), (h = d.data) == null ? void 0 : h.items.map(m => s.jsxs("button", {
      type: "button",
      onClick: () => t({
        customer: m,
        vehicle: void 0
      }),
      className: "block w-full rounded-2xl bg-slate-100 p-4 text-start text-xl font-bold hover:bg-brand-soft",
      children: [m.full_name, " — ", s.jsx("span", {
        dir: "ltr",
        children: m.mobile
      })]
    }, m.id)), !i && s.jsx(P, {
      kind: "secondary",
      onClick: () => a(!0),
      children: l("عميل جديد")
    }), i && s.jsxs("div", {
      className: "grid gap-3 rounded-2xl bg-slate-50 p-4 sm:grid-cols-2",
      children: [s.jsx(E, {
        label: l("الاسم"),
        children: s.jsx("input", {
          value: o.full_name,
          onChange: m => c({
            ...o,
            full_name: m.target.value
          })
        })
      }), s.jsx(E, {
        label: l("الموبايل"),
        children: s.jsx("input", {
          value: o.mobile,
          onChange: m => c({
            ...o,
            mobile: m.target.value
          }),
          dir: "ltr"
        })
      }), s.jsxs("div", {
        className: "sm:col-span-2 space-y-2",
        children: [u.error && u.error.code === "possible_duplicate" ? s.jsxs("div", {
          className: "rounded-xl bg-wait-soft p-3 font-bold text-wait",
          children: [l("فيه عميل مشابه بالفعل — ابحث عنه فوق، أو"), " ", s.jsx("button", {
            className: "underline",
            onClick: () => u.mutate(!0),
            children: l("احفظ كعميل جديد")
          })]
        }) : s.jsx($, {
          message: (p = u.error) == null ? void 0 : p.message
        }), s.jsx(P, {
          onClick: () => u.mutate(!1),
          disabled: o.full_name.length < 2 || o.mobile.length < 5 || u.isPending,
          children: l("حفظ العميل")
        })]
      })]
    })]
  });
}
function zw({
  d: e,
  set: t
}) {
  var d, u, h;
  const [n, r] = w.useState(!1),
    [i, a] = w.useState({
      make: "",
      model: "",
      plate: "",
      model_year: ""
    }),
    o = W({
      queryKey: ["rc-veh", (d = e.customer) == null ? void 0 : d.id],
      queryFn: () => M.get(`/api/vehicles${Re({
        customer_id: e.customer.id
      })}`)
    }),
    c = V({
      mutationFn: () => M.post("/api/vehicles", {
        customer_id: e.customer.id,
        make: i.make,
        model: i.model,
        plate: i.plate || null,
        model_year: i.model_year ? Number(i.model_year) : null
      }),
      onSuccess: p => {
        var m;
        t({
          vehicle: p,
          mileage: ((m = p.current_mileage) == null ? void 0 : m.toString()) ?? e.mileage
        }), o.refetch(), r(!1);
      }
    });
  return e.vehicle ? s.jsxs("div", {
    className: "flex items-center justify-between rounded-2xl bg-ok-soft p-5 text-xl font-bold text-ok",
    children: ["✔ ", s.jsx("span", {
      dir: "ltr",
      children: e.vehicle.plate ?? l("بدون لوحة")
    }), " ", e.vehicle.make, " ", e.vehicle.model, s.jsx("button", {
      className: "underline",
      onClick: () => t({
        vehicle: void 0
      }),
      children: l("تغيير")
    })]
  }) : s.jsxs("div", {
    className: "space-y-4",
    children: [s.jsx("div", {
      className: "grid gap-3 sm:grid-cols-2",
      children: (u = o.data) == null ? void 0 : u.items.map(p => s.jsxs("button", {
        type: "button",
        onClick: () => {
          var m;
          return t({
            vehicle: p,
            mileage: ((m = p.current_mileage) == null ? void 0 : m.toString()) ?? ""
          });
        },
        className: "rounded-2xl border-4 border-slate-200 bg-white p-4 text-start hover:border-brand",
        children: [s.jsx("p", {
          className: "text-2xl font-extrabold",
          dir: "ltr",
          children: p.plate ?? l("بدون لوحة")
        }), s.jsxs("p", {
          className: "text-lg font-semibold",
          children: [p.make, " ", p.model, " ", p.model_year ?? ""]
        })]
      }, p.id))
    }), !n && s.jsx(P, {
      kind: "secondary",
      onClick: () => r(!0),
      children: l("عربية جديدة")
    }), n && s.jsxs("div", {
      className: "grid gap-3 rounded-2xl bg-slate-50 p-4 sm:grid-cols-2",
      children: [s.jsx(E, {
        label: l("الماركة"),
        children: s.jsx("input", {
          value: i.make,
          onChange: p => a({
            ...i,
            make: p.target.value
          })
        })
      }), s.jsx(E, {
        label: l("الموديل"),
        children: s.jsx("input", {
          value: i.model,
          onChange: p => a({
            ...i,
            model: p.target.value
          })
        })
      }), s.jsx(E, {
        label: l("رقم اللوحة"),
        children: s.jsx("input", {
          value: i.plate,
          onChange: p => a({
            ...i,
            plate: p.target.value
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("سنة الصنع"),
        children: s.jsx("input", {
          value: i.model_year,
          onChange: p => a({
            ...i,
            model_year: p.target.value
          }),
          type: "number",
          dir: "ltr"
        })
      }), s.jsxs("div", {
        className: "sm:col-span-2 space-y-2",
        children: [s.jsx($, {
          message: (h = c.error) == null ? void 0 : h.message
        }), s.jsx(P, {
          onClick: () => c.mutate(),
          disabled: !i.make || !i.model || c.isPending,
          children: l("حفظ العربية")
        })]
      })]
    })]
  });
}
function Iw({
  d: e,
  set: t,
  tpl: n,
  shots: r,
  setShots: i
}) {
  var h;
  const [a, o] = w.useState(),
    c = (p, m) => t({
      condition: {
        ...e.condition,
        [p]: {
          ...e.condition[p],
          state: m
        }
      }
    }),
    d = (p, m) => t({
      condition: {
        ...e.condition,
        [p]: {
          ...e.condition[p],
          state: "damaged",
          kind: m
        }
      }
    }),
    u = () => t({
      condition: Object.fromEntries(((n == null ? void 0 : n.condition_points) ?? Object.keys(ii)).map(p => {
        var m;
        return [p, ((m = e.condition[p]) == null ? void 0 : m.state) === "damaged" ? e.condition[p] : {
          state: "ok"
        }];
      }))
    });
  return s.jsxs("div", {
    className: "space-y-5",
    children: [s.jsxs("div", {
      className: "grid gap-4 sm:grid-cols-2",
      children: [s.jsx(E, {
        label: l("قراءة العداد (كم)"),
        children: s.jsx("input", {
          type: "number",
          min: 0,
          value: e.mileage,
          onChange: p => t({
            mileage: p.target.value
          }),
          dir: "ltr",
          inputMode: "numeric"
        })
      }), s.jsxs("div", {
        children: [s.jsx("span", {
          className: "mb-1 block text-base font-semibold",
          children: l("مستوى البنزين")
        }), s.jsx("div", {
          className: "flex flex-wrap gap-2",
          children: ((n == null ? void 0 : n.fuel_levels) ?? Object.keys(ld)).map(p => s.jsx(Zr, {
            on: e.fuel === p,
            onClick: () => t({
              fuel: p
            }),
            children: ld[p]
          }, p))
        })]
      })]
    }), s.jsxs("div", {
      children: [s.jsxs("div", {
        className: "mb-2 flex flex-wrap items-center justify-between gap-2",
        children: [s.jsx("p", {
          className: "text-xl font-extrabold",
          children: l("حالة العربية من برة")
        }), s.jsx(P, {
          kind: "secondary",
          onClick: u,
          children: l("الكل سليم")
        })]
      }), s.jsxs("div", {
        className: "mb-4 rounded-2xl bg-slate-50 p-3",
        children: [s.jsx("p", {
          className: "mb-2 text-center text-sm font-semibold text-slate-600",
          children: l("اضغط على مكان العيب في الرسم")
        }), s.jsx(zy, {
          condition: e.condition,
          selected: a,
          onSelect: p => {
            o(p), e.condition[p] || c(p, "ok");
          }
        }), a && s.jsxs("div", {
          className: "mt-3 space-y-2 text-center",
          children: [s.jsx("p", {
            className: "text-lg font-bold",
            children: ii[a] ?? a
          }), s.jsxs("div", {
            className: "flex flex-wrap justify-center gap-2",
            children: [s.jsx(Zr, {
              on: ((h = e.condition[a]) == null ? void 0 : h.state) === "ok",
              onClick: () => c(a, "ok"),
              children: l("سليم")
            }), Object.entries(Xl).map(([p, m]) => {
              var y, j;
              return s.jsx(Zr, {
                on: ((y = e.condition[a]) == null ? void 0 : y.state) === "damaged" && ((j = e.condition[a]) == null ? void 0 : j.kind) === p,
                onClick: () => d(a, p),
                children: m.label
              }, p);
            })]
          })]
        })]
      }), s.jsx("div", {
        className: "space-y-2",
        children: ((n == null ? void 0 : n.condition_points) ?? Object.keys(ii)).map(p => {
          var m, y, j, v, N;
          return s.jsxs("div", {
            className: "flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-slate-50 p-3",
            children: [s.jsx("span", {
              className: "text-lg font-bold",
              children: ii[p] ?? p
            }), s.jsxs("div", {
              className: "flex gap-2",
              children: [s.jsx(Zr, {
                on: ((m = e.condition[p]) == null ? void 0 : m.state) === "ok",
                onClick: () => c(p, "ok"),
                children: l("سليم")
              }), s.jsx(Zr, {
                on: ((y = e.condition[p]) == null ? void 0 : y.state) === "damaged",
                onClick: () => c(p, "damaged"),
                children: l("فيه عيب")
              })]
            }), s.jsxs("label", {
              className: "inline-flex min-h-[48px] cursor-pointer items-center gap-1 rounded-xl border-2 border-slate-300 bg-white px-3 font-bold",
              children: ["📷 ", (j = r[p]) != null && j.length ? `(${r[p].length})` : l("صورة"), s.jsx("input", {
                type: "file",
                accept: "image/*",
                capture: "environment",
                multiple: !0,
                hidden: !0,
                onChange: x => x.target.files && i({
                  ...r,
                  [p]: [...(r[p] ?? []), ...Array.from(x.target.files)]
                })
              })]
            }), ((v = e.condition[p]) == null ? void 0 : v.state) === "damaged" && s.jsx("input", {
              className: "basis-full",
              placeholder: l("وصف العيب"),
              value: ((N = e.condition[p]) == null ? void 0 : N.note) ?? "",
              onChange: x => t({
                condition: {
                  ...e.condition,
                  [p]: {
                    state: "damaged",
                    note: x.target.value
                  }
                }
              })
            })]
          }, p);
        })
      })]
    }), s.jsxs("div", {
      children: [s.jsx("p", {
        className: "mb-2 text-xl font-extrabold",
        children: l("لمبات التابلوه المضيئة")
      }), s.jsx(Iy, {
        value: e.lights,
        onChange: p => t({
          lights: p
        })
      })]
    })]
  });
}
function $w({
  d: e,
  set: t,
  techs: n
}) {
  const r = i => t({
    categories: e.categories.includes(i) ? e.categories.filter(a => a !== i) : [...e.categories, i]
  });
  return s.jsxs("div", {
    className: "space-y-5",
    children: [s.jsx("p", {
      className: "text-xl font-extrabold",
      children: l("إيه المشكلة؟ (اختار واحد أو أكتر)")
    }), s.jsx("div", {
      className: "grid grid-cols-3 gap-3 sm:grid-cols-5 lg:grid-cols-7",
      children: Hn.map(({
        key: i,
        label: a,
        icon: o
      }) => s.jsxs("button", {
        type: "button",
        "aria-pressed": e.categories.includes(i),
        onClick: () => r(i),
        className: `flex min-h-[96px] flex-col items-center justify-center gap-1 rounded-2xl border-4 p-2 text-base font-bold ${e.categories.includes(i) ? "border-brand bg-brand-soft text-brand" : "border-slate-200 bg-white"}`,
        children: [s.jsx(o, {
          size: 36
        }), a]
      }, i))
    }), s.jsx(E, {
      label: l("تفاصيل شكوى العميل"),
      children: s.jsx("textarea", {
        rows: 3,
        value: e.complaintText,
        onChange: i => t({
          complaintText: i.target.value
        })
      })
    }), s.jsx(E, {
      label: l("متعلقات داخل العربية (افصل بفاصلة)"),
      children: s.jsx("input", {
        value: e.belongings,
        onChange: i => t({
          belongings: i.target.value
        }),
        placeholder: l("شنطة، شاحن، نظارة…")
      })
    }), s.jsx(E, {
      label: l("الفني المسؤول"),
      children: s.jsxs("select", {
        value: e.technicianId,
        onChange: i => t({
          technicianId: i.target.value
        }),
        children: [s.jsx("option", {
          value: "",
          children: l("— بدون تحديد —")
        }), n.map(i => s.jsx("option", {
          value: i.id,
          children: i.name
        }, i.id))]
      })
    }), s.jsx(E, {
      label: l("ملاحظات"),
      children: s.jsx("input", {
        value: e.notes,
        onChange: i => t({
          notes: i.target.value
        })
      })
    })]
  });
}
// Recovered route component for /reception; original filename/name unknown.
function Aw() {
  var j, v, N, x, f, g, b, k;
  const e = es(),
    [t, n] = w.useState(Lw),
    [r, i] = w.useState({}),
    [a, o] = w.useState(""),
    c = _ => n(S => ({
      ...S,
      ..._
    })),
    d = W({
      queryKey: ["vehicle", (j = t.vehicle) == null ? void 0 : j.id],
      enabled: !!((v = t.vehicle) != null && v.id),
      queryFn: () => M.get(`/api/vehicles/${t.vehicle.id}`),
      refetchOnMount: "always",
      refetchInterval: 3e4
    });
  w.useEffect(() => {
    const _ = d.data;
    _ && n(S => {
      var T;
      return ((T = S.vehicle) == null ? void 0 : T.id) === _.id && JSON.stringify(S.vehicle) !== JSON.stringify(_) ? {
        ...S,
        vehicle: _
      } : S;
    });
  }, [d.data]), w.useEffect(() => {
    try {
      localStorage.setItem(Qa, JSON.stringify(t));
    } catch {}
  }, [t]);
  const u = W({
      queryKey: ["templates"],
      queryFn: () => M.get("/api/templates")
    }),
    h = W({
      queryKey: ["techs", !0],
      queryFn: () => M.get("/api/technicians?active=true")
    }),
    p = V({
      mutationFn: () => M.post("/api/reception", {
        vehicle_id: t.vehicle.id,
        mileage: Number(t.mileage),
        fuel_level: t.fuel,
        condition: t.condition,
        dashboard_lights: t.lights,
        complaints: [...t.categories.map(_ => ({
          category: _
        })), ...(t.complaintText ? [{
          text: t.complaintText
        }] : [])],
        belongings: t.belongings.split(/[,،]/).map(_ => _.trim()).filter(Boolean),
        technician_id: t.technicianId ? Number(t.technicianId) : null,
        notes: t.notes || null
      }),
      onSuccess: async _ => {
        const S = [];
        for (const [T, R] of Object.entries(r)) for (const F of R) try {
          await Pu("visit", _.id, F, "photo", T);
        } catch {
          S.push(F.name);
        }
        localStorage.removeItem(Qa), S.length ? (o(Z("تم فتح أمر الصيانة لكن تعذر رفع: {0} — أضفها من صفحة الأمر", S.join(l("، ")))), setTimeout(() => e(`/jobs/${_.id}`), 2500)) : e(`/jobs/${_.id}/receipt`);
      }
    }),
    m = t.step === 0 ? !!t.customer : t.step === 1 ? !!t.vehicle : t.step === 2 ? t.mileage !== "" && Number(t.mileage) >= 0 : t.step === 3 ? t.categories.length > 0 || t.complaintText.trim() !== "" : !0,
    y = () => {
      confirm(l("إلغاء الاستقبال ومسح البيانات المدخلة؟")) && (localStorage.removeItem(Qa), n(od), e("/"));
    };
  return s.jsxs(s.Fragment, {
    children: [s.jsx("h1", {
      className: "text-3xl font-extrabold",
      children: l("استقبال عربية")
    }), s.jsx($, {
      message: (N = d.error) == null ? void 0 : N.message
    }), s.jsx("ol", {
      className: "flex gap-2",
      "aria-label": l("خطوات الاستقبال"),
      children: Fw.map((_, S) => s.jsxs("li", {
        "aria-current": S === t.step,
        className: `min-w-0 flex-1 break-words rounded-xl p-1 text-center text-xs font-bold sm:p-2 sm:text-base ${S < t.step ? "bg-ok-soft text-ok" : S === t.step ? "bg-brand text-white" : "bg-slate-200 text-slate-600"}`,
        children: [S < t.step ? "✔ " : `${S + 1}. `, _]
      }, _))
    }), s.jsxs(B, {
      children: [t.step === 0 && s.jsx(Dw, {
        d: t,
        set: c
      }), t.step === 1 && s.jsx(zw, {
        d: t,
        set: c
      }), t.step === 2 && s.jsx(Iw, {
        d: t,
        set: c,
        tpl: u.data,
        shots: r,
        setShots: i
      }), t.step === 3 && s.jsx($w, {
        d: t,
        set: c,
        techs: h.data ?? []
      }), t.step === 4 && s.jsxs("div", {
        className: "space-y-3 text-xl",
        children: [s.jsxs("p", {
          children: [s.jsx("b", {
            children: l("العميل:")
          }), " ", (x = t.customer) == null ? void 0 : x.full_name]
        }), s.jsxs("p", {
          children: [s.jsx("b", {
            children: l("العربية:")
          }), " ", s.jsx("span", {
            dir: "ltr",
            children: (f = t.vehicle) == null ? void 0 : f.plate
          }), " ", (g = t.vehicle) == null ? void 0 : g.make, " ", (b = t.vehicle) == null ? void 0 : b.model]
        }), s.jsxs("p", {
          children: [s.jsx("b", {
            children: l("العداد:")
          }), " ", t.mileage, " ", l("كم ·"), " ", s.jsx("b", {
            children: l("البنزين:")
          }), " ", ld[t.fuel]]
        }), s.jsxs("p", {
          children: [s.jsx("b", {
            children: l("المشكلة:")
          }), " ", t.categories.map(_ => {
            var S;
            return (S = Hn.find(T => T.key === _)) == null ? void 0 : S.label;
          }).join(l("، ")), " ", t.complaintText]
        }), s.jsxs("p", {
          children: [s.jsx("b", {
            children: l("عيوب موجودة:")
          }), " ", Object.entries(t.condition).filter(([, _]) => _.state === "damaged").map(([_, S]) => {
            var T;
            return `${ii[_]}${S.kind ? ` — ${(T = Xl[S.kind]) == null ? void 0 : T.label}` : ""}${S.note ? ` (${S.note})` : ""}`;
          }).join(l("، ")) || l("لا يوجد")]
        }), s.jsxs("p", {
          children: [s.jsx("b", {
            children: l("صور مرفقة:")
          }), " ", Object.values(r).reduce((_, S) => _ + S.length, 0)]
        }), s.jsx($, {
          message: ((k = p.error) == null ? void 0 : k.message) ?? a
        })]
      })]
    }), s.jsxs("div", {
      className: "flex flex-col-reverse gap-3 sm:flex-row sm:justify-between [&_button]:w-full sm:[&_button]:w-auto",
      children: [s.jsxs("div", {
        className: "grid grid-cols-2 gap-3 sm:flex",
        children: [s.jsx(P, {
          kind: "secondary",
          icon: qi ? Ii : vl,
          disabled: t.step === 0,
          onClick: () => c({
            step: t.step - 1
          }),
          children: l("السابق")
        }), s.jsx(P, {
          kind: "secondary",
          icon: ia,
          onClick: y,
          children: l("إلغاء")
        })]
      }), t.step < 4 ? s.jsx(P, {
        icon: qi ? vl : Ii,
        disabled: !m,
        onClick: () => c({
          step: t.step + 1
        }),
        children: l("التالي")
      }) : s.jsx(P, {
        icon: Wx,
        disabled: p.isPending,
        onClick: () => p.mutate(),
        children: l("حفظ وفتح أمر الصيانة")
      })]
    })]
  });
}
const Ow = {
    empty: l("فاضي"),
    quarter: l("ربع"),
    half: l("نص"),
    three_quarters: l("تلات أرباع"),
    full: l("فل")
  },
  qw = {
    front_bumper: l("الصدام الأمامي"),
    rear_bumper: l("الصدام الخلفي"),
    left_side: l("الجنب الشمال"),
    right_side: l("الجنب اليمين"),
    windshield: l("الزجاج الأمامي"),
    headlights: l("الفوانيس الأمامية"),
    taillights: l("الفوانيس الخلفية"),
    tires: l("الكفرات"),
    interior: l("الداخلية"),
    dashboard: l("التابلوه"),
    scratches_dents: l("خدوش وطعجات")
  };
// Recovered route component for /jobs/:id/receipt; original filename/name unknown.
function Bw() {
  var r, i;
  const {
      id: e = ""
    } = Ds(),
    t = W({
      queryKey: ["receipt", e],
      queryFn: () => M.get(`/api/jobs/${e}/receipt`)
    });
  if (t.isLoading) return s.jsx(ie, {});
  if (t.error || !t.data) return s.jsx($, {
    message: (r = t.error) == null ? void 0 : r.message
  });
  const n = t.data;
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("div", {
      className: "no-print flex gap-3",
      children: [s.jsx(P, {
        icon: fn,
        onClick: () => window.print(),
        children: l("طباعة الإيصال")
      }), s.jsx(re, {
        to: `/jobs/${e}`,
        className: "inline-flex min-h-[56px] items-center rounded-2xl border-2 border-slate-300 bg-white px-6 text-xl font-bold",
        children: l("أمر الصيانة")
      })]
    }), s.jsxs("article", {
      className: "space-y-4 rounded-3xl bg-white p-8 shadow print:shadow-none",
      children: [s.jsx(qr, {}), s.jsxs("h1", {
        className: "border-b-2 pb-3 text-3xl font-extrabold",
        children: [l("إيصال استلام عربية — أمر #"), n.job_no]
      }), s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("التاريخ:")
        }), " ", new Date(n.arrival_at).toLocaleString($t)]
      }), s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("العميل:")
        }), " ", n.customer.name, " — ", s.jsx("span", {
          dir: "ltr",
          children: n.customer.mobile
        })]
      }), s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("العربية:")
        }), " ", n.vehicle.make, " ", n.vehicle.model, " ", n.vehicle.year ?? "", " — ", s.jsx("span", {
          dir: "ltr",
          children: n.vehicle.plate
        })]
      }), s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("العداد:")
        }), " ", Gn(n.mileage), " · ", s.jsx("b", {
          children: l("البنزين:")
        }), " ", n.fuel_level ? Ow[n.fuel_level] : "—"]
      }), s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("المشكلة:")
        }), " ", n.complaints.map(a => {
          var o;
          return a.category ? (o = Er(a.category)) == null ? void 0 : o.label : a.text;
        }).filter(Boolean).join(l("، ")) || "—"]
      }), s.jsxs("div", {
        children: [s.jsx("b", {
          children: l("حالة العربية عند الاستلام:")
        }), s.jsx("ul", {
          className: "mt-1 grid gap-1 sm:grid-cols-2",
          children: Object.entries(n.condition).map(([a, o]) => {
            var c;
            return s.jsxs("li", {
              children: [o.state === "ok" ? "✔" : "✖", " ", qw[a], o.kind ? ` — ${(c = Xl[o.kind]) == null ? void 0 : c.label}` : "", o.note ? ` — ${o.note}` : ""]
            }, a);
          })
        })]
      }), s.jsxs("div", {
        className: "no-print-break grid gap-3 sm:grid-cols-2",
        children: [s.jsx(zy, {
          condition: n.condition,
          onSelect: () => {}
        }), (((i = n.dashboard_lights) == null ? void 0 : i.length) ?? 0) > 0 && s.jsxs("div", {
          children: [s.jsx("b", {
            children: l("لمبات التابلوه المضيئة")
          }), s.jsx("div", {
            className: "mt-2",
            children: s.jsx(Iy, {
              value: n.dashboard_lights
            })
          })]
        })]
      }), s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("المتعلقات:")
        }), " ", n.belongings.join(l("، ")) || l("لا يوجد")]
      }), n.notes && s.jsxs("p", {
        children: [s.jsx("b", {
          children: l("ملاحظات:")
        }), " ", n.notes]
      }), s.jsxs("div", {
        className: "grid grid-cols-2 gap-8 pt-10 text-center",
        children: [s.jsx("p", {
          className: "border-t-2 pt-2",
          children: l("توقيع العميل")
        }), s.jsx("p", {
          className: "border-t-2 pt-2",
          children: l("توقيع موظف الاستقبال")
        })]
      })]
    })]
  });
}
const Tp = {
    in_person: l("حضورياً"),
    phone: l("تليفون"),
    whatsapp: l("واتساب"),
    signed: l("ورقة موقعة"),
    other: l("أخرى")
  },
  Fp = {
    labor: l("أجور"),
    part: l("قطع غيار"),
    other: l("أخرى")
  };
// Recovered route component for /quotations/:id; original filename/name unknown.
function Uw() {
  var b, k, _, S, T;
  const {
      id: e = ""
    } = Ds(),
    {
      can: t
    } = ce(),
    n = de(),
    r = W({
      queryKey: ["quote", e],
      queryFn: () => M.get(`/api/quotations/${e}`)
    }),
    i = () => {
      n.invalidateQueries({
        queryKey: ["quote", e]
      }), n.invalidateQueries({
        queryKey: ["quotes"]
      }), n.invalidateQueries({
        queryKey: ["job"]
      });
    },
    [a, o] = w.useState({
      kind: "other",
      description: "",
      unit_price: ""
    }),
    [c, d] = w.useState(null),
    [u, h] = w.useState({}),
    [p, m] = w.useState({
      decision: "approved",
      method: "in_person",
      evidence: ""
    }),
    y = V({
      mutationFn: () => M.post(`/api/quotations/${e}/items`, {
        ...a,
        unit_price: a.unit_price || "0"
      }),
      onSuccess: () => {
        o({
          kind: "other",
          description: "",
          unit_price: ""
        }), i();
      }
    }),
    j = V({
      mutationFn: () => M.patch(`/api/quotations/${e}`, {
        discount: c.discount || "0",
        tax_rate: c.tax_rate || "0",
        valid_until: c.valid_until || null
      }),
      onSuccess: () => {
        d(null), i();
      }
    }),
    v = V({
      mutationFn: () => M.post(`/api/quotations/${e}/send`),
      onSuccess: i
    }),
    N = V({
      mutationFn: () => {
        const R = Object.entries(u).filter(([, F]) => F).map(([F]) => Number(F));
        return M.post(`/api/quotations/${e}/approvals`, {
          method: p.method,
          evidence: p.evidence,
          decisions: R.map(F => ({
            item_id: F,
            decision: p.decision
          }))
        });
      },
      onSuccess: () => {
        h({}), m({
          ...p,
          evidence: ""
        }), i();
      }
    });
  if (r.isLoading) return s.jsx(ie, {});
  if (r.error || !r.data) return s.jsx($, {
    message: (b = r.error) == null ? void 0 : b.message
  });
  const x = r.data,
    f = x.items.filter(R => R.approval_state === "pending"),
    g = t("quotes.approve") && ["sent", "partially_approved"].includes(x.status) && f.length > 0;
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("div", {
      className: "no-print flex flex-wrap gap-3",
      children: [s.jsx(P, {
        icon: fn,
        kind: "secondary",
        onClick: () => window.print(),
        children: l("طباعة / حفظ PDF")
      }), s.jsxs(re, {
        to: `/jobs/${x.visit_id}`,
        className: "inline-flex min-h-[56px] items-center rounded-2xl border-2 border-slate-300 bg-white px-6 text-xl font-bold",
        children: [l("أمر الصيانة #"), x.job_no]
      })]
    }), s.jsx(qr, {}), s.jsxs(B, {
      children: [s.jsxs("div", {
        className: "flex flex-wrap items-center justify-between gap-3",
        children: [s.jsxs("h1", {
          className: "text-3xl font-extrabold",
          children: [l("عرض سعر #"), x.quote_no]
        }), s.jsx(Xe, {
          status: x.status
        })]
      }), x.valid_until && s.jsxs("p", {
        className: "text-slate-600",
        children: [l("ساري حتى"), " ", $e(x.valid_until)]
      }), s.jsx("div", {
        className: "overflow-x-auto print:overflow-visible",
        children: s.jsxs("table", {
          className: "mt-4 w-full text-start text-lg",
          children: [s.jsx("thead", {
            children: s.jsxs("tr", {
              className: "border-b-2 text-slate-500",
              children: [s.jsx("th", {
                className: "p-2 text-start",
                children: l("البند")
              }), s.jsx("th", {
                className: "p-2 text-start",
                children: l("النوع")
              }), s.jsx("th", {
                className: "p-2 text-start",
                children: l("المبلغ")
              }), s.jsx("th", {
                className: "p-2 text-start",
                children: l("القرار")
              }), s.jsx("th", {
                className: "no-print"
              })]
            })
          }), s.jsx("tbody", {
            children: x.items.map(R => s.jsxs("tr", {
              className: "border-b",
              children: [s.jsxs("td", {
                className: "p-2 font-semibold",
                children: [J(R.description), Number(R.quantity) !== 1 && s.jsxs("span", {
                  className: "text-slate-500",
                  children: [" × ", R.quantity]
                })]
              }), s.jsx("td", {
                className: "p-2",
                children: Fp[R.kind]
              }), s.jsx("td", {
                className: "p-2 font-bold",
                children: R.amount
              }), s.jsx("td", {
                className: "p-2",
                children: s.jsx(Xe, {
                  status: R.approval_state
                })
              }), s.jsx("td", {
                className: "no-print p-2",
                children: g && R.approval_state === "pending" && s.jsx("input", {
                  type: "checkbox",
                  "aria-label": l("اختيار البند"),
                  className: "!h-7 !w-7",
                  checked: !!u[R.id],
                  onChange: F => h({
                    ...u,
                    [R.id]: F.target.checked
                  })
                })
              })]
            }, R.id))
          })]
        })
      }), s.jsxs("dl", {
        className: "mt-4 ms-auto max-w-xs space-y-1 text-lg",
        children: [s.jsxs("div", {
          className: "flex justify-between",
          children: [s.jsx("dt", {
            children: l("الإجمالي")
          }), s.jsx("dd", {
            children: x.subtotal
          })]
        }), Number(x.discount) > 0 && s.jsxs("div", {
          className: "flex justify-between",
          children: [s.jsx("dt", {
            children: l("الخصم")
          }), s.jsxs("dd", {
            children: ["- ", x.discount]
          })]
        }), Number(x.tax_rate) > 0 && s.jsxs("div", {
          className: "flex justify-between",
          children: [s.jsxs("dt", {
            children: [l("الضريبة ("), x.tax_rate, "%)"]
          }), s.jsx("dd", {
            children: x.tax_amount
          })]
        }), s.jsxs("div", {
          className: "flex justify-between border-t-2 pt-1 text-2xl font-extrabold",
          children: [s.jsx("dt", {
            children: l("المطلوب")
          }), s.jsx("dd", {
            children: x.grand_total
          })]
        }), x.approvals.length > 0 && s.jsxs("div", {
          className: "flex justify-between font-bold text-ok",
          children: [s.jsx("dt", {
            children: l("المُوافق عليه")
          }), s.jsx("dd", {
            children: x.approved_amount
          })]
        })]
      })]
    }), x.status === "draft" && t("quotes.write") && s.jsxs(B, {
      title: l("تعديل المسودة"),
      children: [s.jsxs("div", {
        className: "grid gap-3 sm:grid-cols-4",
        children: [s.jsx(E, {
          label: l("النوع"),
          children: s.jsx("select", {
            value: a.kind,
            onChange: R => o({
              ...a,
              kind: R.target.value
            }),
            children: Object.entries(Fp).map(([R, F]) => s.jsx("option", {
              value: R,
              children: F
            }, R))
          })
        }), s.jsx("div", {
          className: "sm:col-span-2",
          children: s.jsx(E, {
            label: l("الوصف"),
            children: s.jsx("input", {
              value: a.description,
              onChange: R => o({
                ...a,
                description: R.target.value
              })
            })
          })
        }), s.jsx(E, {
          label: l("السعر"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            value: a.unit_price,
            onChange: R => o({
              ...a,
              unit_price: R.target.value
            }),
            dir: "ltr"
          })
        })]
      }), s.jsxs("div", {
        className: "mt-3",
        children: [s.jsx($, {
          message: (k = y.error) == null ? void 0 : k.message
        }), s.jsx(P, {
          icon: ts,
          disabled: a.description.length < 2 || y.isPending,
          onClick: () => y.mutate(),
          children: l("إضافة بند")
        })]
      }), c ? s.jsxs("div", {
        className: "mt-4 grid gap-3 sm:grid-cols-3",
        children: [s.jsx(E, {
          label: l("الخصم (مبلغ)"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            value: c.discount,
            onChange: R => d({
              ...c,
              discount: R.target.value
            }),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("نسبة الضريبة %"),
          children: s.jsx("input", {
            type: "number",
            step: "0.01",
            min: "0",
            max: "100",
            value: c.tax_rate,
            onChange: R => d({
              ...c,
              tax_rate: R.target.value
            }),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("ساري حتى"),
          children: s.jsx("input", {
            type: "date",
            value: c.valid_until,
            onChange: R => d({
              ...c,
              valid_until: R.target.value
            }),
            dir: "ltr"
          })
        }), s.jsxs("div", {
          className: "sm:col-span-3",
          children: [s.jsx($, {
            message: (_ = j.error) == null ? void 0 : _.message
          }), s.jsx(P, {
            onClick: () => j.mutate(),
            children: l("حفظ الخصم والضريبة")
          })]
        })]
      }) : s.jsx("div", {
        className: "mt-4",
        children: s.jsx(P, {
          kind: "secondary",
          onClick: () => d({
            discount: x.discount,
            tax_rate: x.tax_rate,
            valid_until: x.valid_until ?? ""
          }),
          children: l("الخصم والضريبة والصلاحية")
        })
      }), s.jsxs("div", {
        className: "mt-4",
        children: [s.jsx($, {
          message: (S = v.error) == null ? void 0 : S.message
        }), s.jsx(P, {
          icon: Tb,
          disabled: v.isPending,
          onClick: () => confirm(l("إرسال العرض للعميل؟ لن يمكن تعديله بعد الإرسال.")) && v.mutate(),
          children: l("تم إرسال العرض للعميل")
        })]
      })]
    }), g && s.jsxs(B, {
      title: l("تسجيل قرار العميل"),
      children: [s.jsx("p", {
        className: "mb-3 text-slate-600",
        children: l("علّم على البنود اللي العميل قرر فيها، واكتب إزاي وافق (لا تُسجّل موافقة بدون دليل).")
      }), s.jsxs("div", {
        className: "grid gap-3 sm:grid-cols-3",
        children: [s.jsx(E, {
          label: l("القرار"),
          children: s.jsxs("select", {
            value: p.decision,
            onChange: R => m({
              ...p,
              decision: R.target.value
            }),
            children: [s.jsx("option", {
              value: "approved",
              children: l("موافق ✔")
            }), s.jsx("option", {
              value: "rejected",
              children: l("رفض ✖")
            })]
          })
        }), s.jsx(E, {
          label: l("الطريقة"),
          children: s.jsx("select", {
            value: p.method,
            onChange: R => m({
              ...p,
              method: R.target.value
            }),
            children: Object.entries(Tp).map(([R, F]) => s.jsx("option", {
              value: R,
              children: F
            }, R))
          })
        }), s.jsx(E, {
          label: l("الدليل (مثلاً: رسالة واتساب الساعة ١٠:١٥)"),
          children: s.jsx("input", {
            value: p.evidence,
            onChange: R => m({
              ...p,
              evidence: R.target.value
            })
          })
        })]
      }), s.jsxs("div", {
        className: "mt-3",
        children: [s.jsx($, {
          message: (T = N.error) == null ? void 0 : T.message
        }), s.jsx(P, {
          icon: rr,
          disabled: N.isPending || p.evidence.trim().length < 3 || !Object.values(u).some(Boolean),
          onClick: () => N.mutate(),
          children: l("تسجيل القرار")
        })]
      })]
    }), x.approvals.length > 0 && s.jsx(B, {
      title: l("سجل القرارات"),
      children: s.jsx("ul", {
        className: "space-y-2",
        children: x.approvals.map(R => s.jsxs("li", {
          className: "rounded-xl bg-slate-50 p-3",
          children: [s.jsx(Xe, {
            status: R.decision
          }), " ", s.jsx("b", {
            children: Tp[R.method]
          }), " — ", R.evidence, " ", s.jsxs("span", {
            className: "text-slate-500",
            children: ["(", new Date(R.decided_at).toLocaleString($t), ")"]
          })]
        }, R.id))
      })
    })]
  });
}
// Recovered route component for /reminders; original filename/name unknown.
function Qw() {
  var c, d;
  const {
      can: e
    } = ce(),
    t = de(),
    n = W({
      queryKey: ["reminders"],
      queryFn: () => M.get("/api/reminders")
    }),
    r = W({
      queryKey: ["warranties-expiring"],
      queryFn: () => M.get("/api/warranties?expiring_days=30")
    }),
    i = V({
      mutationFn: u => M.post(`/api/reminders/${u.id}/${u.action}`),
      onSuccess: () => t.invalidateQueries({
        queryKey: ["reminders"]
      })
    }),
    a = {
      overdue: 0,
      due_soon: 1,
      upcoming: 2
    },
    o = [...(n.data ?? [])].sort((u, h) => a[u.status] - a[h.status]);
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(Qn, {
        size: 36
      }), l("تذكيرات الصيانة")]
    }), s.jsxs(B, {
      children: [n.isLoading ? s.jsx(ie, {}) : n.error ? s.jsx($, {
        message: n.error.message
      }) : o.length ? s.jsx("ul", {
        className: "space-y-3",
        children: o.map(u => s.jsxs("li", {
          className: "flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-50 p-4",
          children: [s.jsxs("div", {
            children: [s.jsx("p", {
              className: "text-xl font-bold",
              children: J(u.title)
            }), s.jsxs("p", {
              className: "text-slate-700",
              children: [s.jsx(re, {
                to: `/vehicles/${u.vehicle_id}`,
                className: "font-bold hover:text-brand",
                dir: "ltr",
                children: u.plate
              }), " · ", u.vehicle, " · ", u.customer]
            }), s.jsxs("p", {
              className: "flex items-center gap-1 text-slate-600",
              dir: "ltr",
              children: [s.jsx(Fg, {
                size: 16
              }), u.mobile]
            }), s.jsxs("p", {
              className: "text-slate-600",
              children: [u.due_date && Z("الموعد {0}", $e(u.due_date)), u.due_date && u.due_mileage && " · ", u.due_mileage && Z("عند {0} (الآن {1})", Gn(u.due_mileage), Gn(u.current_mileage))]
            })]
          }), s.jsxs("div", {
            className: "flex flex-col items-end gap-2",
            children: [s.jsx(Xe, {
              status: u.status
            }), e("visits.write") && s.jsxs("div", {
              className: "flex gap-2",
              children: [s.jsx(P, {
                kind: "secondary",
                onClick: () => i.mutate({
                  id: u.id,
                  action: "done"
                }),
                children: l("تم")
              }), s.jsx(P, {
                kind: "secondary",
                onClick: () => i.mutate({
                  id: u.id,
                  action: "dismiss"
                }),
                children: l("تجاهل")
              })]
            })]
          })]
        }, u.id))
      }) : s.jsx(Ie, {
        icon: Qn,
        text: l("مفيش تذكيرات دلوقتي")
      }), s.jsx($, {
        message: (c = i.error) == null ? void 0 : c.message
      })]
    }), !!((d = r.data) != null && d.length) && s.jsx(B, {
      title: l("ضمانات تنتهي خلال ٣٠ يوم"),
      children: s.jsx("ul", {
        className: "space-y-2",
        children: r.data.map(u => s.jsxs("li", {
          className: "flex flex-wrap items-center justify-between gap-2 rounded-xl bg-slate-50 p-3",
          children: [s.jsxs("span", {
            className: "font-bold",
            children: [J(u.description), " · ", s.jsx("span", {
              dir: "ltr",
              children: u.plate
            })]
          }), s.jsxs("span", {
            children: [l("تنتهي"), " ", $e(u.end_date)]
          })]
        }, u.id))
      })
    })]
  });
}
const Oo = new Set(["open-jobs", "delayed-jobs", "outstanding", "customer-history"]);
// Recovered route component for /reports; original filename/name unknown.
function Kw() {
  var t;
  const e = W({
    queryKey: ["reports"],
    queryFn: () => M.get("/api/reports")
  });
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(Kl, {
        size: 36
      }), l("التقارير")]
    }), e.isLoading ? s.jsx(ie, {}) : s.jsx("div", {
      className: "grid gap-4 sm:grid-cols-2 lg:grid-cols-3",
      children: (t = e.data) == null ? void 0 : t.map(n => s.jsx(re, {
        to: `/reports/${n.name}`,
        className: "flex min-h-[88px] items-center justify-center rounded-3xl bg-white p-5 text-center text-xl font-extrabold shadow hover:bg-brand-soft",
        children: J(n.title)
      }, n.name))
    })]
  });
}
// Recovered route component for /reports/:name; original filename/name unknown.
function Vw() {
  var u;
  const {
      name: e = ""
    } = Ds(),
    [t, n] = w.useState({
      date_from: Ns().slice(0, 8) + "01",
      date_to: Ns(),
      group: "day",
      days: "90",
      customer_id: ""
    }),
    [r, i] = w.useState(""),
    a = {};
  (!Oo.has(e) || e === "customer-history") && e !== "customer-history" && (a.date_from = t.date_from, a.date_to = t.date_to), e === "activity" && (a.group = t.group), e === "repeat-repairs" && (a.days = t.days), e === "customer-history" && (a.customer_id = t.customer_id);
  const o = W({
      queryKey: ["report", e, a],
      enabled: e !== "customer-history" || !!t.customer_id,
      queryFn: () => M.get(`/api/reports/${e}${Re(a)}`)
    }),
    c = W({
      queryKey: ["rep-cust", r],
      enabled: e === "customer-history" && r.length >= 2,
      queryFn: () => M.get(`/api/customers${Re({
        q: r,
        limit: 6
      })}`)
    }),
    d = o.data;
  return s.jsxs(s.Fragment, {
    children: [s.jsx(qr, {}), s.jsxs("div", {
      className: "no-print flex flex-wrap items-center justify-between gap-3",
      children: [s.jsx("h1", {
        className: "text-3xl font-extrabold",
        children: J(d == null ? void 0 : d.title) || l("تقرير")
      }), s.jsx(re, {
        to: "/reports",
        className: "font-bold text-brand underline",
        children: l("كل التقارير")
      })]
    }), s.jsx(B, {
      children: s.jsxs("div", {
        className: "no-print grid gap-3 sm:grid-cols-4",
        children: [!Oo.has(e) && s.jsxs(s.Fragment, {
          children: [s.jsx(E, {
            label: l("من"),
            children: s.jsx("input", {
              type: "date",
              value: t.date_from,
              onChange: h => n({
                ...t,
                date_from: h.target.value
              }),
              dir: "ltr"
            })
          }), s.jsx(E, {
            label: l("إلى"),
            children: s.jsx("input", {
              type: "date",
              value: t.date_to,
              onChange: h => n({
                ...t,
                date_to: h.target.value
              }),
              dir: "ltr"
            })
          })]
        }), e === "activity" && s.jsx(E, {
          label: l("التجميع"),
          children: s.jsxs("select", {
            value: t.group,
            onChange: h => n({
              ...t,
              group: h.target.value
            }),
            children: [s.jsx("option", {
              value: "day",
              children: l("يومي")
            }), s.jsx("option", {
              value: "week",
              children: l("أسبوعي")
            }), s.jsx("option", {
              value: "month",
              children: l("شهري")
            })]
          })
        }), e === "repeat-repairs" && s.jsx(E, {
          label: l("خلال كام يوم"),
          children: s.jsx("input", {
            type: "number",
            min: 1,
            value: t.days,
            onChange: h => n({
              ...t,
              days: h.target.value
            }),
            dir: "ltr"
          })
        }), e === "customer-history" && s.jsxs("div", {
          className: "sm:col-span-3",
          children: [s.jsx(E, {
            label: l("ابحث عن العميل"),
            children: s.jsx("input", {
              value: r,
              onChange: h => i(h.target.value)
            })
          }), (u = c.data) == null ? void 0 : u.items.map(h => s.jsxs("button", {
            onClick: () => {
              n({
                ...t,
                customer_id: h.id
              }), i(h.full_name);
            },
            className: "mt-2 block w-full rounded-xl bg-slate-100 p-3 text-start font-bold hover:bg-brand-soft",
            children: [h.full_name, " — ", s.jsx("span", {
              dir: "ltr",
              children: h.mobile
            })]
          }, h.id))]
        }), s.jsxs("div", {
          className: "flex flex-wrap items-end gap-2",
          children: [s.jsxs("a", {
            href: `/api/reports/${e}/export${Re({
              ...a,
              format: "xlsx",
              lang: Et
            })}`,
            className: "inline-flex min-h-[56px] items-center gap-2 rounded-2xl bg-ok px-5 text-lg font-bold text-white",
            children: [s.jsx(kb, {
              size: 22
            }), "Excel"]
          }), s.jsxs("a", {
            href: `/api/reports/${e}/export${Re({
              ...a,
              format: "csv",
              lang: Et
            })}`,
            className: "inline-flex min-h-[56px] items-center gap-2 rounded-2xl border-2 border-slate-300 bg-white px-5 text-lg font-bold",
            children: [s.jsx(xu, {
              size: 22
            }), "CSV"]
          }), s.jsx(P, {
            kind: "secondary",
            icon: fn,
            onClick: () => window.print(),
            children: l("طباعة / PDF")
          })]
        })]
      })
    }), o.isLoading ? s.jsx(ie, {}) : o.error ? s.jsx($, {
      message: o.error.message
    }) : d ? s.jsx(B, {
      title: Z("{0} صف{1}", d.count, Oo.has(e) ? "" : Z(" · من {0} إلى {1}", d.date_from, d.date_to)),
      children: d.rows.length ? s.jsx("div", {
        className: "overflow-x-auto",
        children: s.jsxs("table", {
          className: "w-full text-start text-base",
          children: [s.jsx("thead", {
            children: s.jsx("tr", {
              className: "border-b-2 text-slate-500",
              children: d.columns.map(h => s.jsx("th", {
                className: "whitespace-nowrap p-2 text-start",
                children: J(h.label)
              }, h.key))
            })
          }), s.jsx("tbody", {
            children: d.rows.map((h, p) => s.jsx("tr", {
              className: "border-b",
              children: d.columns.map(m => {
                var y, j, v;
                return s.jsx("td", {
                  className: `p-2 ${m.type === "money" ? "font-semibold" : ""}`,
                  dir: m.type === "text" ? void 0 : "ltr",
                  children: typeof h[m.key] == "string" ? m.key === "category" ? e === "expenses" ? h[m.key] : ((y = Er(h[m.key])) == null ? void 0 : y.label) ?? J(h[m.key]) : m.key === "status" ? ((j = (e === "parts" ? Bi : Ts)[h[m.key]]) == null ? void 0 : j.label) ?? ((v = Bi[h[m.key]]) == null ? void 0 : v.label) ?? J(h[m.key]) : J(h[m.key]) : h[m.key] ?? ""
                }, m.key);
              })
            }, p))
          }), Object.keys(d.totals).length > 0 && s.jsx("tfoot", {
            children: s.jsxs("tr", {
              className: "border-t-2 font-extrabold",
              children: [s.jsx("td", {
                className: "p-2",
                children: l("الإجمالي")
              }), d.columns.slice(1).map(h => s.jsx("td", {
                className: "p-2",
                dir: "ltr",
                children: d.totals[h.key] ?? ""
              }, h.key))]
            })
          })]
        })
      }) : s.jsx(Ie, {
        icon: Kl,
        text: l("لا توجد بيانات في هذه الفترة")
      })
    }) : s.jsx(Ie, {
      text: l("اختار العميل أولاً")
    })]
  });
}
function Lp(e) {
  return e.length <= 500 && e.every(t => t.name.trim().length > 0 && t.name.trim().length <= 200 && (t.initial_price === null || /^\d{1,10}(\.\d{1,2})?$/.test(t.initial_price))) && new Set(e.map(t => `${t.category}:${t.name.trim().toLocaleLowerCase()}`)).size === e.length;
}
function Ww({
  items: e,
  currency: t
}) {
  var j;
  const [n, r] = w.useState(e),
    [i, a] = w.useState(""),
    [o, c] = w.useState(""),
    [d, u] = w.useState(!1),
    h = de(),
    p = V({
      mutationFn: () => M.put("/api/settings/repair_catalog", {
        items: n.map(v => ({
          ...v,
          name: v.name.trim()
        }))
      }),
      onSuccess: v => {
        r(v.items), u(!1), h.invalidateQueries({
          queryKey: ["settings"]
        }), h.invalidateQueries({
          queryKey: ["templates"]
        });
      }
    }),
    m = (v, N) => {
      r(x => x.map(f => f.id === v ? {
        ...f,
        ...N
      } : f)), u(!0), p.reset();
    },
    y = n.filter(v => (!i || v.category === i) && `${v.name} ${J(v.name)}`.toLocaleLowerCase().includes(o.trim().toLocaleLowerCase()));
  return s.jsx("div", {
    id: "repair-catalog",
    className: "scroll-mt-24",
    children: s.jsxs(B, {
      title: l("إعداد الأعطال والأسعار المبدئية"),
      children: [s.jsx("p", {
        className: "mb-4 text-sm text-slate-600",
        children: l("أسعار تقديرية للمراجعة فقط؛ لا تغيّر أجور الإصلاح أو الفواتير تلقائيًا.")
      }), s.jsxs("div", {
        className: "grid gap-3 sm:grid-cols-2",
        children: [s.jsx(E, {
          label: l("بحث عن عطل أو خدمة"),
          children: s.jsxs("div", {
            className: "flex items-center gap-2",
            children: [s.jsx(Wn, {
              size: 18
            }), s.jsx("input", {
              value: o,
              onChange: v => c(v.target.value)
            })]
          })
        }), s.jsx(E, {
          label: l("نوع العطل"),
          children: s.jsxs("select", {
            value: i,
            onChange: v => a(v.target.value),
            children: [s.jsx("option", {
              value: "",
              children: l("الكل")
            }), Hn.map(v => s.jsx("option", {
              value: v.key,
              children: v.label
            }, v.key))]
          })
        })]
      }), s.jsxs("div", {
        className: "my-4 flex flex-wrap items-center justify-between gap-3",
        children: [s.jsx("span", {
          className: "font-semibold text-slate-600",
          children: Z("عرض {0} من {1} بند", y.length, n.length)
        }), s.jsx(P, {
          kind: "secondary",
          icon: ts,
          disabled: p.isPending || n.length >= 500,
          onClick: () => {
            r([...n, {
              id: crypto.randomUUID(),
              category: i || "engine",
              name: "",
              initial_price: null,
              active: !0
            }]), c(""), u(!0), p.reset();
          },
          children: l("إضافة عطل أو خدمة")
        })]
      }), s.jsx("div", {
        className: "max-h-[640px] space-y-3 overflow-y-auto pe-1",
        children: y.map(v => s.jsxs("div", {
          className: `grid gap-3 rounded-2xl border p-4 md:grid-cols-[2fr_1fr_1fr_auto] ${v.active ? "border-slate-200 bg-slate-50" : "border-slate-200 bg-slate-100"}`,
          children: [s.jsx(E, {
            label: l("اسم العطل أو الخدمة"),
            children: s.jsx("input", {
              maxLength: 200,
              value: v.name,
              disabled: p.isPending,
              onChange: N => m(v.id, {
                name: N.target.value
              })
            })
          }), s.jsx(E, {
            label: l("التصنيف"),
            children: s.jsx("select", {
              value: v.category,
              disabled: p.isPending,
              onChange: N => m(v.id, {
                category: N.target.value
              }),
              children: Hn.map(N => s.jsx("option", {
                value: N.key,
                children: N.label
              }, N.key))
            })
          }), s.jsx(E, {
            label: Z("السعر المبدئي ({0})", t),
            children: s.jsx("input", {
              type: "number",
              min: "0",
              max: "9999999999.99",
              step: "0.01",
              dir: "ltr",
              value: v.initial_price ?? "",
              placeholder: l("غير محدد"),
              disabled: p.isPending,
              onChange: N => m(v.id, {
                initial_price: N.target.value === "" ? null : N.target.value
              })
            })
          }), s.jsxs("label", {
            className: "flex min-h-[48px] items-center gap-2 self-end font-semibold",
            children: [s.jsx("input", {
              type: "checkbox",
              className: "!h-5 !w-5",
              checked: v.active,
              disabled: p.isPending,
              onChange: N => m(v.id, {
                active: N.target.checked
              })
            }), l("مفعّل")]
          })]
        }, v.id))
      }), !y.length && s.jsx("p", {
        className: "py-5 text-slate-500",
        children: l("لا توجد بنود مطابقة للبحث")
      }), s.jsxs("div", {
        className: "mt-4 border-t pt-4",
        children: [s.jsx($, {
          message: (j = p.error) == null ? void 0 : j.message
        }), d && !Lp(n) && s.jsx("p", {
          className: "mb-2 text-sm text-bad",
          children: l("راجع الأسماء المكررة أو الفارغة والأسعار غير الصحيحة قبل الحفظ.")
        }), s.jsx(P, {
          icon: et,
          disabled: !d || p.isPending || !Lp(n),
          onClick: () => p.mutate(),
          children: p.isPending ? l("جارٍ الحفظ…") : l("حفظ الأعطال والأسعار")
        }), p.isSuccess && s.jsx("p", {
          role: "status",
          className: "mt-2 font-bold text-ok",
          children: l("تم حفظ قائمة الأعطال والأسعار المبدئية")
        })]
      })]
    })
  });
}
const _l = e => /^\d{1,10}(\.\d{1,2})?$/.test(e.trim()),
  Dp = e => _l(e.default_labor_rate) && e.labor_rates.every(t => t.name.trim().length > 0 && t.name.trim().length <= 60 && _l(t.rate));
function Hw({
  value: e,
  onChange: t,
  disabled: n = !1
}) {
  const r = e.labor_rates,
    i = (a, o) => t({
      ...e,
      labor_rates: r.map((c, d) => d === a ? {
        ...c,
        ...o
      } : c)
    });
  return s.jsxs("section", {
    className: "mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-5",
    "aria-label": l("أسعار العمالة"),
    children: [s.jsxs("div", {
      className: "flex flex-wrap items-center justify-between gap-3",
      children: [s.jsxs("div", {
        className: "flex items-center gap-3",
        children: [s.jsx("span", {
          className: "rounded-xl bg-brand-soft p-3 text-brand",
          children: s.jsx(ns, {
            size: 24
          })
        }), s.jsxs("div", {
          children: [s.jsx("h3", {
            className: "text-xl font-extrabold",
            children: l("أسعار العمالة")
          }), s.jsx("p", {
            className: "mt-1 text-sm text-slate-600",
            children: l("نظّم أسعار العمل وحدّد السعر الافتراضي للساعة.")
          })]
        })]
      }), s.jsx("span", {
        className: "rounded-full bg-white px-3 py-1 text-sm font-bold text-brand",
        children: Z("عدد الأسعار: {0}", r.length)
      })]
    }), s.jsxs("div", {
      className: "mt-4 grid gap-4 rounded-xl border border-blue-100 bg-white p-4 sm:grid-cols-2",
      children: [s.jsx(E, {
        label: l("سعر ساعة العمل الافتراضي"),
        error: _l(e.default_labor_rate) ? void 0 : l("أدخل سعراً صحيحاً من صفر وبحد أقصى منزلتين عشريتين"),
        children: s.jsxs("div", {
          className: "flex items-center gap-2",
          children: [s.jsx(Le, {
            size: 20,
            className: "shrink-0 text-brand"
          }), s.jsx("input", {
            className: "min-w-0",
            "aria-label": l("سعر ساعة العمل الافتراضي"),
            type: "number",
            min: "0",
            max: "9999999999.99",
            step: "0.01",
            value: e.default_labor_rate,
            disabled: n,
            onChange: a => t({
              ...e,
              default_labor_rate: a.target.value
            }),
            dir: "ltr"
          }), s.jsxs("span", {
            className: "shrink-0 text-sm font-bold",
            children: [e.currency, " / ", l("ساعة")]
          })]
        })
      }), s.jsxs("div", {
        className: "self-center text-sm text-slate-600",
        children: [s.jsx("p", {
          children: l("أجر العمل = عدد الساعات × سعر الساعة.")
        }), s.jsx("p", {
          className: "mt-1",
          children: l("الأسعار أدناه قائمة مرجعية؛ تسجيلها لا يطبّقها تلقائياً على أوامر الشغل.")
        })]
      })]
    }), s.jsxs("div", {
      className: "mt-5 flex flex-wrap items-center justify-between gap-3",
      children: [s.jsx("h4", {
        className: "font-extrabold",
        children: l("قائمة أسعار العمالة")
      }), s.jsx(P, {
        kind: "secondary",
        icon: ts,
        disabled: n,
        onClick: () => t({
          ...e,
          labor_rates: [...r, {
            name: "",
            rate: ""
          }]
        }),
        children: l("إضافة سعر عمالة")
      })]
    }), r.length ? s.jsx("ul", {
      className: "mt-3 space-y-3",
      children: r.map((a, o) => s.jsxs("li", {
        className: "grid items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto]",
        children: [s.jsx(E, {
          label: Z("اسم العمل {0}", o + 1),
          error: a.name.trim() ? void 0 : l("اكتب اسم العمل"),
          children: s.jsx("input", {
            maxLength: 60,
            placeholder: l("مثال: أعمال ميكانيكا"),
            value: a.name,
            disabled: n,
            onChange: c => i(o, {
              name: c.target.value
            })
          })
        }), s.jsx(E, {
          label: Z("السعر ({0})", e.currency),
          error: _l(a.rate) ? void 0 : l("أدخل سعراً صحيحاً من صفر وبحد أقصى منزلتين عشريتين"),
          children: s.jsx("input", {
            type: "number",
            min: "0",
            max: "9999999999.99",
            step: "0.01",
            value: a.rate,
            disabled: n,
            onChange: c => i(o, {
              rate: c.target.value
            }),
            dir: "ltr"
          })
        }), s.jsxs("button", {
          type: "button",
          disabled: n,
          "aria-label": Z("حذف سعر العمالة {0}", o + 1),
          className: "inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl px-3 font-bold text-bad hover:bg-bad-soft disabled:opacity-50 sm:mt-7",
          onClick: () => t({
            ...e,
            labor_rates: r.filter((c, d) => d !== o)
          }),
          children: [s.jsx(Or, {
            size: 20
          }), l("حذف")]
        })]
      }, o))
    }) : s.jsxs("div", {
      className: "mt-3 rounded-xl border-2 border-dashed border-slate-200 bg-white px-4 py-6 text-center",
      children: [s.jsx("p", {
        className: "font-bold",
        children: l("لم تُضف أسعار عمالة بعد")
      }), s.jsx("p", {
        className: "mt-1 text-sm text-slate-500",
        children: l("أضف اسم العمل وسعره، مثل أعمال الميكانيكا أو الكهرباء.")
      })]
    })]
  });
}
const Gw = [l("الإثنين"), l("الثلاثاء"), l("الأربعاء"), l("الخميس"), l("الجمعة"), l("السبت"), l("الأحد")];
function Qi(e) {
  const t = de();
  return V({
    mutationFn: n => M.put(`/api/settings/${e}`, n),
    onSuccess: () => t.invalidateQueries({
      queryKey: ["settings"]
    })
  });
}
function Ki({
  m: e
}) {
  var t;
  return s.jsxs("div", {
    className: "mt-3 space-y-2",
    children: [s.jsx($, {
      message: (t = e.error) == null ? void 0 : t.message
    }), e.isSuccess && s.jsx("p", {
      className: "font-bold text-ok",
      children: l("✔ تم الحفظ")
    })]
  });
}
function Jw({
  s: e
}) {
  var c;
  const [t, n] = w.useState(e),
    r = Qi("workshop"),
    i = de(),
    a = V({
      mutationFn: d => Pu("workshop", "logo", d, "photo"),
      onSuccess: () => i.invalidateQueries({
        queryKey: ["logo"]
      })
    }),
    o = d => u => n({
      ...t,
      [d]: u.target.value
    });
  return s.jsxs(B, {
    title: l("بيانات الورشة"),
    children: [s.jsxs("div", {
      className: "grid gap-4 sm:grid-cols-2",
      children: [s.jsx(E, {
        label: l("اسم الورشة"),
        children: s.jsx("input", {
          value: t.name,
          onChange: o("name")
        })
      }), s.jsx(E, {
        label: l("الاسم بالإنجليزية (للفواتير)"),
        children: s.jsx("input", {
          value: t.name_en,
          onChange: o("name_en"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("العنوان"),
        children: s.jsx("input", {
          value: t.address,
          onChange: o("address")
        })
      }), s.jsx(E, {
        label: l("الموبايل"),
        children: s.jsx("input", {
          value: t.phone,
          onChange: o("phone"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("البريد الإلكتروني"),
        children: s.jsx("input", {
          value: t.email,
          onChange: o("email"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("الرقم الضريبي (إن وجد)"),
        children: s.jsx("input", {
          value: t.tax_number,
          onChange: o("tax_number"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("الشعار (صورة)"),
        children: s.jsx("input", {
          type: "file",
          accept: "image/*",
          onChange: d => {
            var u;
            return ((u = d.target.files) == null ? void 0 : u[0]) && a.mutate(d.target.files[0]);
          }
        })
      })]
    }), a.isSuccess && s.jsx("p", {
      className: "mt-2 font-bold text-ok",
      children: l("✔ تم رفع الشعار")
    }), s.jsx($, {
      message: (c = a.error) == null ? void 0 : c.message
    }), s.jsx("div", {
      className: "mt-3",
      children: s.jsx(P, {
        icon: et,
        disabled: r.isPending,
        onClick: () => r.mutate(t),
        children: l("حفظ")
      })
    }), s.jsx(Ki, {
      m: r
    })]
  });
}
function Yw({
  s: e
}) {
  const [t, n] = w.useState(e),
    r = Qi("finance"),
    i = a => o => n({
      ...t,
      [a]: o.target.value
    });
  return s.jsxs(B, {
    title: l("الحسابات والفواتير"),
    children: [s.jsxs("div", {
      className: "grid gap-4 sm:grid-cols-3",
      children: [s.jsx(E, {
        label: l("العملة (3 حروف)"),
        children: s.jsx("input", {
          value: t.currency,
          onChange: a => n({
            ...t,
            currency: a.target.value.toUpperCase()
          }),
          dir: "ltr",
          maxLength: 3
        })
      }), s.jsx(E, {
        label: l("نسبة الضريبة الافتراضية % (٠ = بدون ضريبة)"),
        children: s.jsx("input", {
          type: "number",
          step: "0.01",
          min: "0",
          max: "100",
          value: t.default_tax_rate,
          onChange: i("default_tax_rate"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("بادئة رقم الفاتورة"),
        children: s.jsx("input", {
          value: t.invoice_prefix,
          onChange: i("invoice_prefix"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("بادئة الإشعار الدائن"),
        children: s.jsx("input", {
          value: t.credit_prefix,
          onChange: i("credit_prefix"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("عدد خانات الرقم"),
        children: s.jsx("input", {
          type: "number",
          min: 1,
          max: 10,
          value: t.number_width,
          onChange: a => n({
            ...t,
            number_width: Number(a.target.value)
          }),
          dir: "ltr"
        })
      })]
    }), s.jsxs("p", {
      className: "mt-3 text-slate-600",
      children: [l("مثال رقم الفاتورة:"), " ", s.jsxs("b", {
        dir: "ltr",
        children: [t.invoice_prefix, "-", "1".padStart(Number(t.number_width) || 1, "0")]
      })]
    }), s.jsx("h3", {
      className: "mt-5 text-xl font-extrabold",
      children: l("طرق الدفع")
    }), s.jsx("ul", {
      className: "mt-2 space-y-2",
      children: t.payment_methods.map((a, o) => s.jsxs("li", {
        className: "flex gap-2",
        children: [s.jsx("input", {
          value: a.key,
          onChange: c => n({
            ...t,
            payment_methods: t.payment_methods.map((d, u) => u === o ? {
              ...d,
              key: c.target.value
            } : d)
          }),
          dir: "ltr",
          "aria-label": l("الرمز")
        }), s.jsx("input", {
          value: a.label,
          onChange: c => n({
            ...t,
            payment_methods: t.payment_methods.map((d, u) => u === o ? {
              ...d,
              label: c.target.value
            } : d)
          }),
          "aria-label": l("الاسم")
        }), s.jsx("button", {
          "aria-label": l("حذف"),
          className: "text-bad",
          onClick: () => n({
            ...t,
            payment_methods: t.payment_methods.filter((c, d) => d !== o)
          }),
          children: s.jsx(Or, {})
        })]
      }, o))
    }), s.jsx("div", {
      className: "mt-2",
      children: s.jsx(P, {
        kind: "secondary",
        icon: ts,
        onClick: () => n({
          ...t,
          payment_methods: [...t.payment_methods, {
            key: "",
            label: ""
          }]
        }),
        children: l("طريقة دفع جديدة")
      })
    }), s.jsx(Hw, {
      value: t,
      disabled: r.isPending,
      onChange: a => {
        n(a), r.reset();
      }
    }), s.jsxs("div", {
      className: "mt-5 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-4",
      children: [s.jsx(P, {
        icon: et,
        disabled: r.isPending || !Dp(t),
        onClick: () => r.mutate({
          ...t,
          labor_rates: t.labor_rates.map(a => ({
            name: a.name.trim(),
            rate: a.rate.trim()
          }))
        }),
        children: r.isPending ? l("جارٍ الحفظ…") : l("حفظ إعدادات الحسابات")
      }), s.jsx("p", {
        className: "text-sm text-slate-500",
        children: Dp(t) ? l("يحفظ الأسعار وباقي إعدادات الحسابات والفواتير.") : l("أكمل أسماء وأسعار العمالة لتفعيل الحفظ.")
      })]
    }), s.jsx(Ki, {
      m: r
    })]
  });
}
function Zw({
  s: e,
  w: t
}) {
  const [n, r] = w.useState(e),
    [i, a] = w.useState(t),
    o = Qi("general"),
    c = Qi("warranty"),
    d = n.working_hours;
  return s.jsxs(B, {
    title: l("عام"),
    children: [s.jsxs("div", {
      className: "grid gap-4 sm:grid-cols-3",
      children: [s.jsx(E, {
        label: l("لغة النظام الافتراضية"),
        children: s.jsxs("select", {
          value: n.language ?? "en",
          onChange: u => r({
            ...n,
            language: u.target.value
          }),
          children: [s.jsx("option", {
            value: "ar",
            children: "العربية"
          }), s.jsx("option", {
            value: "en",
            children: "English"
          })]
        })
      }), s.jsx(E, {
        label: l("المظهر"),
        children: s.jsxs("select", {
          value: n.theme,
          onChange: u => r({
            ...n,
            theme: u.target.value
          }),
          children: [s.jsx("option", {
            value: "light",
            children: l("فاتح")
          }), s.jsx("option", {
            value: "dark",
            children: l("داكن")
          })]
        })
      }), s.jsx(E, {
        label: l("بداية الدوام"),
        children: s.jsx("input", {
          type: "time",
          value: d.open,
          onChange: u => r({
            ...n,
            working_hours: {
              ...d,
              open: u.target.value
            }
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("نهاية الدوام"),
        children: s.jsx("input", {
          type: "time",
          value: d.close,
          onChange: u => r({
            ...n,
            working_hours: {
              ...d,
              close: u.target.value
            }
          }),
          dir: "ltr"
        })
      })]
    }), s.jsx("div", {
      className: "mt-3 flex flex-wrap gap-2",
      children: Gw.map((u, h) => s.jsx("button", {
        type: "button",
        "aria-pressed": d.days.includes(h),
        onClick: () => r({
          ...n,
          working_hours: {
            ...d,
            days: d.days.includes(h) ? d.days.filter(p => p !== h) : [...d.days, h].sort()
          }
        }),
        className: `min-h-[48px] rounded-xl border-4 px-4 font-bold ${d.days.includes(h) ? "border-brand bg-brand-soft text-brand" : "border-slate-200"}`,
        children: u
      }, u))
    }), s.jsx("div", {
      className: "mt-3",
      children: s.jsx(P, {
        icon: et,
        disabled: o.isPending,
        onClick: () => o.mutate(n),
        children: l("حفظ")
      })
    }), s.jsx(Ki, {
      m: o
    }), s.jsx("h3", {
      className: "mt-6 text-xl font-extrabold",
      children: l("الضمان الافتراضي (شهور، ٠ = بدون)")
    }), s.jsxs("div", {
      className: "mt-2 grid gap-4 sm:grid-cols-2",
      children: [s.jsx(E, {
        label: l("ضمان قطع الغيار"),
        children: s.jsx("input", {
          type: "number",
          min: 0,
          value: i.default_part_months,
          onChange: u => a({
            ...i,
            default_part_months: Number(u.target.value)
          }),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("ضمان العمالة"),
        children: s.jsx("input", {
          type: "number",
          min: 0,
          value: i.default_labor_months,
          onChange: u => a({
            ...i,
            default_labor_months: Number(u.target.value)
          }),
          dir: "ltr"
        })
      })]
    }), s.jsx("div", {
      className: "mt-3",
      children: s.jsx(P, {
        icon: et,
        disabled: c.isPending,
        onClick: () => c.mutate(i),
        children: l("حفظ الضمان")
      })
    }), s.jsx(Ki, {
      m: c
    })]
  });
}
function Xw() {
  const e = W({
      queryKey: ["security"],
      queryFn: () => M.get("/api/settings/security")
    }),
    [t, n] = w.useState(null);
  w.useEffect(() => {
    e.data && n(e.data);
  }, [e.data]);
  const r = Qi("security");
  if (!t) return null;
  const i = a => o => n({
    ...t,
    [a]: Number(o.target.value)
  });
  return s.jsxs(B, {
    title: l("الأمان"),
    children: [s.jsxs("div", {
      className: "grid gap-4 sm:grid-cols-3",
      children: [s.jsx(E, {
        label: l("مدة الجلسة (دقائق)"),
        children: s.jsx("input", {
          type: "number",
          min: 5,
          max: 1440,
          value: t.session_minutes,
          onChange: i("session_minutes"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("عدد محاولات الدخول الخاطئة"),
        children: s.jsx("input", {
          type: "number",
          min: 3,
          max: 20,
          value: t.max_failed_logins,
          onChange: i("max_failed_logins"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("مدة القفل (دقائق)"),
        children: s.jsx("input", {
          type: "number",
          min: 1,
          value: t.lockout_minutes,
          onChange: i("lockout_minutes"),
          dir: "ltr"
        })
      })]
    }), s.jsx("div", {
      className: "mt-3",
      children: s.jsx(P, {
        icon: et,
        disabled: r.isPending,
        onClick: () => r.mutate(t),
        children: l("حفظ")
      })
    }), s.jsx(Ki, {
      m: r
    })]
  });
}
// Recovered route component for /settings; original filename/name unknown.
function ek() {
  const {
      can: e
    } = ce(),
    t = zs();
  return t.isLoading || !t.data ? s.jsx(ie, {}) : s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(ra, {
        size: 36
      }), l("الإعدادات")]
    }), e("settings.manage") ? s.jsxs(s.Fragment, {
      children: [s.jsx(Jw, {
        s: t.data.workshop
      }), s.jsx(Yw, {
        s: t.data.finance
      }), t.data.repair_catalog && s.jsx(Ww, {
        items: t.data.repair_catalog.items,
        currency: t.data.finance.currency
      }), s.jsx(Zw, {
        s: t.data.general,
        w: t.data.warranty
      })]
    }) : s.jsx("p", {
      className: "rounded-2xl bg-wait-soft p-4 font-bold text-wait",
      children: l("ليس لديك صلاحية تعديل الإعدادات")
    }), e("users.manage") && s.jsx(Xw, {})]
  });
}
function tk({
  s: e,
  canCosts: t
}) {
  var a, o, c;
  const [n, r] = w.useState(!1),
    i = W({
      queryKey: ["sup-purchases", e.id],
      enabled: n,
      queryFn: () => M.get(`/api/suppliers/${e.id}/purchases`)
    });
  return s.jsxs("li", {
    className: "py-3",
    children: [s.jsxs("button", {
      onClick: () => r(!n),
      "aria-expanded": n,
      className: "flex w-full flex-wrap items-center justify-between gap-2 text-start",
      children: [s.jsxs("span", {
        className: "text-xl font-bold",
        children: [e.name, " ", !e.is_active && s.jsx("span", {
          className: "text-sm text-slate-500",
          children: l("(موقوف)")
        })]
      }), s.jsx("span", {
        dir: "ltr",
        className: "text-slate-600",
        children: e.phone
      })]
    }), n && (i.isLoading ? s.jsx(ie, {}) : s.jsxs("div", {
      className: "mt-2 space-y-2 rounded-2xl bg-slate-50 p-3",
      children: [t && ((a = i.data) == null ? void 0 : a.total_cost) !== void 0 && s.jsxs("p", {
        className: "font-bold",
        children: [l("إجمالي المشتريات:"), " ", i.data.total_cost, " ", l("· المسترد:"), " ", i.data.total_refunds]
      }), !((o = i.data) != null && o.parts.length) && s.jsx("p", {
        className: "text-slate-500",
        children: l("لا توجد مشتريات")
      }), (c = i.data) == null ? void 0 : c.parts.map(d => s.jsxs("div", {
        className: "flex flex-wrap items-center justify-between gap-2",
        children: [s.jsxs("span", {
          className: "font-semibold",
          children: [d.part_name, " ", s.jsx("span", {
            dir: "ltr",
            className: "text-slate-500",
            children: d.part_number
          })]
        }), s.jsx(Xe, {
          status: d.status
        })]
      }, d.id))]
    }))]
  });
}
// Recovered route component for /suppliers; original filename/name unknown.
function nk() {
  var h, p, m;
  const {
      can: e
    } = ce(),
    t = de(),
    [n, r] = w.useState({
      name: "",
      contact_person: "",
      phone: ""
    }),
    [i, a] = w.useState(""),
    o = W({
      queryKey: ["suppliers", "all"],
      queryFn: () => M.get("/api/suppliers")
    }),
    c = W({
      queryKey: ["part-search", i],
      enabled: i.length >= 2,
      queryFn: () => M.get(`/api/parts${Re({
        q: i
      })}`)
    }),
    d = V({
      mutationFn: () => M.post("/api/suppliers", {
        name: n.name,
        contact_person: n.contact_person || null,
        phone: n.phone || null
      }),
      onSuccess: () => {
        r({
          name: "",
          contact_person: "",
          phone: ""
        }), t.invalidateQueries({
          queryKey: ["suppliers"]
        });
      }
    }),
    u = y => {
      y.preventDefault(), d.mutate();
    };
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(Wl, {
        size: 36
      }), l("قطع الغيار والموردين")]
    }), s.jsxs(B, {
      title: l("بحث عن قطعة"),
      children: [s.jsx("div", {
        className: "relative",
        children: s.jsx("input", {
          value: i,
          onChange: y => a(y.target.value),
          placeholder: l("رقم القطعة أو الاسم أو الماركة"),
          "aria-label": l("بحث عن قطعة")
        })
      }), i.length >= 2 && (c.isLoading ? s.jsx(ie, {}) : (h = c.data) != null && h.length ? s.jsx("ul", {
        className: "mt-3 divide-y",
        children: c.data.map(y => s.jsx("li", {
          children: s.jsxs(re, {
            to: `/jobs/${y.visit_id}`,
            className: "flex flex-wrap items-center justify-between gap-2 py-3 hover:text-brand",
            children: [s.jsxs("span", {
              className: "text-lg font-bold",
              children: [y.part_name, " ", s.jsx("span", {
                dir: "ltr",
                className: "text-slate-500",
                children: y.part_number
              })]
            }), s.jsxs("span", {
              className: "text-slate-600",
              children: [l("أمر #"), y.job_no, " · ", s.jsx("span", {
                dir: "ltr",
                children: y.plate
              })]
            }), s.jsx(Xe, {
              status: y.status
            })]
          })
        }, y.id))
      }) : s.jsx(Ie, {
        icon: Wn,
        text: l("مفيش قطع بالاسم ده")
      }))]
    }), e("suppliers.write") && s.jsx(B, {
      title: l("مورد جديد"),
      children: s.jsxs("form", {
        onSubmit: u,
        className: "grid gap-4 sm:grid-cols-3",
        children: [s.jsx(E, {
          label: l("اسم المورد"),
          children: s.jsx("input", {
            value: n.name,
            onChange: y => r({
              ...n,
              name: y.target.value
            }),
            required: !0,
            minLength: 2
          })
        }), s.jsx(E, {
          label: l("الشخص المسؤول"),
          children: s.jsx("input", {
            value: n.contact_person,
            onChange: y => r({
              ...n,
              contact_person: y.target.value
            })
          })
        }), s.jsx(E, {
          label: l("الموبايل"),
          children: s.jsx("input", {
            value: n.phone,
            onChange: y => r({
              ...n,
              phone: y.target.value
            }),
            dir: "ltr"
          })
        }), s.jsxs("div", {
          className: "sm:col-span-3 space-y-2",
          children: [s.jsx($, {
            message: (p = d.error) == null ? void 0 : p.message
          }), s.jsx(P, {
            type: "submit",
            icon: et,
            disabled: d.isPending,
            children: l("حفظ")
          })]
        })]
      })
    }), s.jsx(B, {
      title: l("الموردين"),
      children: o.isLoading ? s.jsx(ie, {}) : (m = o.data) != null && m.length ? s.jsx("ul", {
        className: "divide-y",
        children: o.data.map(y => s.jsx(tk, {
          s: y,
          canCosts: e("parts.costs")
        }, y.id))
      }) : s.jsx(Ie, {
        icon: Hl,
        text: l("مفيش موردين مسجلين")
      })
    })]
  });
}
// Recovered route component for /users; original filename/name unknown.
function sk() {
  var p, m, y, j, v;
  const e = de(),
    [t, n] = w.useState({
      username: "",
      full_name: "",
      password: "",
      role: "receptionist"
    }),
    r = W({
      queryKey: ["users"],
      queryFn: () => M.get("/api/users")
    }),
    i = W({
      queryKey: ["roles"],
      queryFn: () => M.get("/api/roles")
    }),
    a = () => e.invalidateQueries({
      queryKey: ["users"]
    }),
    o = V({
      mutationFn: () => M.post("/api/users", t),
      onSuccess: () => {
        n({
          ...t,
          username: "",
          full_name: "",
          password: ""
        }), a();
      }
    }),
    c = V({
      mutationFn: N => M.patch(`/api/users/${N.id}`, N.body),
      onSuccess: a
    }),
    d = V({
      mutationFn: N => M.post(`/api/users/${N.id}/reset-password`, {
        password: N.password
      })
    }),
    u = N => {
      N.preventDefault(), o.mutate();
    },
    h = N => {
      const x = prompt(Z("كلمة مرور جديدة للمستخدم {0} (٨ أحرف على الأقل)", N.full_name));
      x && x.length >= 8 && d.mutate({
        id: N.id,
        password: x
      });
    };
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(Ms, {
        size: 36
      }), l("المستخدمين")]
    }), s.jsx(B, {
      title: l("مستخدم جديد"),
      children: s.jsxs("form", {
        onSubmit: u,
        className: "grid gap-4 sm:grid-cols-2",
        children: [s.jsx(E, {
          label: l("اسم المستخدم (إنجليزي)"),
          children: s.jsx("input", {
            value: t.username,
            onChange: N => n({
              ...t,
              username: N.target.value
            }),
            dir: "ltr",
            required: !0,
            minLength: 3
          })
        }), s.jsx(E, {
          label: l("الاسم بالكامل"),
          children: s.jsx("input", {
            value: t.full_name,
            onChange: N => n({
              ...t,
              full_name: N.target.value
            }),
            required: !0,
            minLength: 2
          })
        }), s.jsx(E, {
          label: l("كلمة المرور (٨ أحرف على الأقل)"),
          children: s.jsx("input", {
            type: "password",
            value: t.password,
            onChange: N => n({
              ...t,
              password: N.target.value
            }),
            dir: "ltr",
            required: !0,
            minLength: 8,
            autoComplete: "new-password"
          })
        }), s.jsx(E, {
          label: l("الدور"),
          children: s.jsx("select", {
            value: t.role,
            onChange: N => n({
              ...t,
              role: N.target.value
            }),
            children: (p = i.data) == null ? void 0 : p.map(N => s.jsx("option", {
              value: N.name,
              children: J(N.label)
            }, N.name))
          })
        }), s.jsxs("div", {
          className: "sm:col-span-2 space-y-2",
          children: [s.jsx($, {
            message: (m = o.error) == null ? void 0 : m.message
          }), s.jsx(P, {
            type: "submit",
            icon: vu,
            disabled: o.isPending,
            children: l("إضافة")
          })]
        })]
      })
    }), s.jsxs(B, {
      children: [r.isLoading ? s.jsx(ie, {}) : s.jsx("ul", {
        className: "divide-y",
        children: (y = r.data) == null ? void 0 : y.map(N => {
          var x;
          return s.jsxs("li", {
            className: "flex flex-wrap items-center justify-between gap-3 py-3",
            children: [s.jsxs("div", {
              children: [s.jsxs("p", {
                className: "text-xl font-bold",
                children: [N.full_name, " ", s.jsxs("span", {
                  className: "text-sm text-slate-500",
                  dir: "ltr",
                  children: ["@", N.username]
                })]
              }), !N.is_active && s.jsx("p", {
                className: "font-bold text-bad",
                children: l("⛔ معطّل")
              })]
            }), s.jsxs("div", {
              className: "flex flex-wrap items-center gap-2",
              children: [s.jsx("select", {
                value: N.role,
                onChange: f => c.mutate({
                  id: N.id,
                  body: {
                    role: f.target.value
                  }
                }),
                "aria-label": l("الدور"),
                className: "!w-auto",
                children: (x = i.data) == null ? void 0 : x.map(f => s.jsx("option", {
                  value: f.name,
                  children: J(f.label)
                }, f.name))
              }), s.jsx(P, {
                kind: "secondary",
                icon: gu,
                onClick: () => h(N),
                children: l("كلمة مرور")
              }), s.jsx(P, {
                kind: N.is_active ? "danger" : "primary",
                onClick: () => c.mutate({
                  id: N.id,
                  body: {
                    is_active: !N.is_active
                  }
                }),
                children: N.is_active ? l("تعطيل") : l("تفعيل")
              })]
            })]
          }, N.id);
        })
      }), s.jsx($, {
        message: ((j = c.error) == null ? void 0 : j.message) ?? ((v = d.error) == null ? void 0 : v.message)
      }), d.isSuccess && s.jsx("p", {
        className: "mt-2 font-bold text-ok",
        children: l("✔ تم تغيير كلمة المرور وتسجيل خروج المستخدم من كل الأجهزة")
      })]
    })]
  });
}
// Recovered route component for /technicians; original filename/name unknown.
function rk() {
  var d, u;
  const e = de(),
    [t, n] = w.useState({
      employee_no: "",
      name: "",
      phone: "",
      specialization: ""
    }),
    r = W({
      queryKey: ["techs", "all"],
      queryFn: () => M.get("/api/technicians")
    }),
    i = () => {
      e.invalidateQueries({
        queryKey: ["techs"]
      });
    },
    a = V({
      mutationFn: () => M.post("/api/technicians", {
        ...t,
        phone: t.phone || null,
        specialization: t.specialization || null
      }),
      onSuccess: () => {
        n({
          employee_no: "",
          name: "",
          phone: "",
          specialization: ""
        }), i();
      }
    }),
    o = V({
      mutationFn: h => M.patch(`/api/technicians/${h.id}`, {
        is_active: !h.is_active
      }),
      onSuccess: i
    }),
    c = h => {
      h.preventDefault(), a.mutate();
    };
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(wl, {
        size: 36
      }), l("الفنيين")]
    }), s.jsx(B, {
      title: l("فني جديد"),
      children: s.jsxs("form", {
        onSubmit: c,
        className: "grid gap-4 sm:grid-cols-2",
        children: [s.jsx(E, {
          label: l("رقم الموظف"),
          children: s.jsx("input", {
            value: t.employee_no,
            onChange: h => n({
              ...t,
              employee_no: h.target.value
            }),
            required: !0,
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("الاسم"),
          children: s.jsx("input", {
            value: t.name,
            onChange: h => n({
              ...t,
              name: h.target.value
            }),
            required: !0,
            minLength: 2
          })
        }), s.jsx(E, {
          label: l("الموبايل"),
          children: s.jsx("input", {
            value: t.phone,
            onChange: h => n({
              ...t,
              phone: h.target.value
            }),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("التخصص"),
          children: s.jsx("input", {
            value: t.specialization,
            onChange: h => n({
              ...t,
              specialization: h.target.value
            })
          })
        }), s.jsxs("div", {
          className: "sm:col-span-2 space-y-2",
          children: [s.jsx($, {
            message: (d = a.error) == null ? void 0 : d.message
          }), s.jsx(P, {
            type: "submit",
            icon: et,
            disabled: a.isPending,
            children: l("حفظ")
          })]
        })]
      })
    }), s.jsx(B, {
      children: r.isLoading ? s.jsx(ie, {}) : (u = r.data) != null && u.length ? s.jsx("ul", {
        className: "divide-y",
        children: r.data.map(h => s.jsxs("li", {
          className: "flex flex-wrap items-center justify-between gap-3 py-3",
          children: [s.jsxs("div", {
            children: [s.jsxs("p", {
              className: "text-xl font-bold",
              children: [h.name, " ", s.jsxs("span", {
                className: "text-sm text-slate-500",
                children: ["#", h.employee_no]
              })]
            }), s.jsx("p", {
              className: "text-slate-600",
              children: h.specialization ?? ""
            })]
          }), s.jsx(P, {
            kind: "secondary",
            onClick: () => o.mutate(h),
            children: h.is_active ? l("✔ شغال — إيقاف") : l("⏸ موقوف — تفعيل")
          })]
        }, h.id))
      }) : s.jsx(Ie, {
        icon: wl,
        text: l("مفيش فنيين مسجلين")
      })
    })]
  });
}
// Recovered route component for /search; original filename/name unknown.
function ik() {
  var a;
  const [e] = sa(),
    t = e.get("q") ?? "",
    n = W({
      queryKey: ["search", t],
      enabled: !!t,
      queryFn: () => M.get(`/api/search?q=${encodeURIComponent(t)}`)
    });
  if (!t) return s.jsx(Ie, {
    text: l("اكتب في خانة البحث فوق")
  });
  if (n.isLoading) return s.jsx(ie, {});
  const r = n.data,
    i = !r || Object.values(r).every(o => !o.length);
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("h1", {
      className: "flex items-center gap-2 text-3xl font-extrabold",
      children: [s.jsx(Wn, {
        size: 32
      }), l("نتائج البحث:"), " ", t]
    }), s.jsx($, {
      message: (a = n.error) == null ? void 0 : a.message
    }), i && s.jsx(B, {
      children: s.jsx(Ie, {
        text: l("مفيش نتائج")
      })
    }), !!(r != null && r.vehicles.length) && s.jsx(B, {
      title: l("العربيات"),
      children: s.jsx("div", {
        className: "grid gap-3 sm:grid-cols-2",
        children: r.vehicles.map(o => s.jsxs(re, {
          to: `/vehicles/${o.id}`,
          className: "flex items-center gap-3 rounded-2xl border-2 border-slate-200 p-4 hover:border-brand",
          children: [s.jsx(un, {
            size: 36,
            className: "text-brand"
          }), s.jsxs("div", {
            children: [s.jsx("p", {
              className: "text-xl font-extrabold",
              dir: "ltr",
              children: o.plate ?? l("بدون لوحة")
            }), s.jsxs("p", {
              className: "font-semibold",
              children: [o.make, " ", o.model]
            })]
          })]
        }, o.id))
      })
    }), !!(r != null && r.jobs.length) && s.jsx(B, {
      title: l("أوامر الصيانة"),
      children: s.jsx("ul", {
        className: "divide-y",
        children: r.jobs.map(o => s.jsx("li", {
          children: s.jsxs(re, {
            to: `/jobs/${o.id}`,
            className: "flex min-h-[56px] flex-wrap items-center gap-3 py-2 hover:text-brand",
            children: [s.jsx(fu, {
              size: 26
            }), s.jsxs("span", {
              className: "text-xl font-bold",
              children: [l("أمر #"), o.job_no]
            }), s.jsx("span", {
              dir: "ltr",
              children: o.plate
            }), s.jsx("span", {
              children: o.vehicle
            }), s.jsx(Pr, {
              status: o.status
            })]
          })
        }, o.id))
      })
    }), !!(r != null && r.customers.length) && s.jsx(B, {
      title: l("العملاء"),
      children: s.jsx("ul", {
        className: "divide-y",
        children: r.customers.map(o => s.jsx("li", {
          children: s.jsxs(re, {
            to: `/vehicles?customer=${o.id}`,
            className: "flex min-h-[56px] items-center gap-3 py-2 hover:text-brand",
            children: [s.jsx(Ms, {
              size: 28
            }), s.jsx("span", {
              className: "text-xl font-bold",
              children: o.name
            }), s.jsx("span", {
              dir: "ltr",
              className: "text-slate-500",
              children: o.mobile
            })]
          })
        }, o.id))
      })
    }), !!(r != null && r.invoices.length) && s.jsx(B, {
      title: l("الفواتير"),
      children: s.jsx("ul", {
        className: "divide-y",
        children: r.invoices.map(o => s.jsx("li", {
          children: s.jsxs(re, {
            to: `/invoices/${o.id}`,
            className: "flex min-h-[56px] items-center gap-3 py-2 hover:text-brand",
            children: [s.jsx($i, {
              size: 26
            }), s.jsxs("span", {
              className: "text-xl font-bold",
              children: [l("فاتورة #"), o.invoice_no]
            }), s.jsx("span", {
              children: o.total
            })]
          })
        }, o.id))
      })
    }), !!(r != null && r.parts.length) && s.jsx(B, {
      title: l("قطع الغيار"),
      children: s.jsx("ul", {
        className: "divide-y",
        children: r.parts.map(o => s.jsx("li", {
          children: s.jsxs(re, {
            to: `/jobs/${o.visit_id}`,
            className: "flex min-h-[56px] items-center gap-3 py-2 hover:text-brand",
            children: [s.jsx(Wl, {
              size: 26
            }), s.jsx("span", {
              className: "font-bold",
              children: o.name
            }), s.jsx("span", {
              dir: "ltr",
              className: "text-slate-500",
              children: o.part_number
            }), s.jsxs("span", {
              children: [l("أمر #"), o.job_no]
            })]
          })
        }, o.id))
      })
    })]
  });
}
function ak({
  id: e
}) {
  const [t, n] = w.useState("");
  return w.useEffect(() => {
    Br.toDataURL(`${window.location.origin}/vehicles/${e}`, {
      margin: 1,
      width: 160
    }).then(n).catch(() => n(""));
  }, [e]), t ? s.jsxs("div", {
    className: "flex flex-col items-center gap-1",
    children: [s.jsx("img", {
      src: t,
      alt: l("QR للعربية"),
      className: "h-28 w-28"
    }), s.jsx("span", {
      className: "text-xs text-slate-500",
      children: l("امسح للفتح (يتطلب تسجيل دخول)")
    })]
  }) : null;
}
function lk({
  v: e,
  onDone: t
}) {
  var c, d, u;
  const n = de(),
    [r, i] = w.useState({
      make: e.make,
      model: e.model,
      model_year: ((c = e.model_year) == null ? void 0 : c.toString()) ?? "",
      plate: e.plate ?? "",
      vin: e.vin ?? "",
      color: e.color ?? "",
      current_mileage: ((d = e.current_mileage) == null ? void 0 : d.toString()) ?? ""
    }),
    a = V({
      mutationFn: () => M.patch(`/api/vehicles/${e.id}`, {
        make: r.make,
        model: r.model,
        model_year: r.model_year ? Number(r.model_year) : null,
        plate: r.plate || null,
        vin: r.vin || null,
        color: r.color || null,
        current_mileage: r.current_mileage ? Number(r.current_mileage) : null
      }),
      onSuccess: h => {
        n.setQueryData(["vehicle", e.id], p => ({
          ...p,
          ...h
        })), n.invalidateQueries({
          queryKey: ["vehicle", e.id]
        });
        for (const p of ["vehicles", "rc-veh", "board", "job", "search"]) n.invalidateQueries({
          queryKey: [p]
        });
        t();
      }
    }),
    o = h => p => i({
      ...r,
      [h]: p.target.value
    });
  return s.jsxs(B, {
    title: l("تعديل بيانات العربية"),
    children: [s.jsxs("div", {
      className: "grid gap-4 sm:grid-cols-3",
      children: [s.jsx(E, {
        label: l("الماركة"),
        children: s.jsx("input", {
          value: r.make,
          onChange: o("make")
        })
      }), s.jsx(E, {
        label: l("الموديل"),
        children: s.jsx("input", {
          value: r.model,
          onChange: o("model")
        })
      }), s.jsx(E, {
        label: l("السنة"),
        children: s.jsx("input", {
          type: "number",
          value: r.model_year,
          onChange: o("model_year"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("رقم اللوحة (التغيير يُسجَّل في سجل اللوحات)"),
        children: s.jsx("input", {
          value: r.plate,
          onChange: o("plate"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("رقم الشاسيه"),
        children: s.jsx("input", {
          value: r.vin,
          onChange: o("vin"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("اللون"),
        children: s.jsx("input", {
          value: r.color,
          onChange: o("color")
        })
      }), s.jsx(E, {
        label: l("العداد (كم)"),
        children: s.jsx("input", {
          type: "number",
          min: 0,
          value: r.current_mileage,
          onChange: o("current_mileage"),
          dir: "ltr"
        })
      })]
    }), s.jsxs("div", {
      className: "mt-3 space-y-2",
      children: [s.jsx($, {
        message: (u = a.error) == null ? void 0 : u.message
      }), s.jsxs("div", {
        className: "flex gap-3",
        children: [s.jsx(P, {
          icon: et,
          disabled: a.isPending,
          onClick: () => a.mutate(),
          children: l("حفظ")
        }), s.jsx(P, {
          kind: "secondary",
          onClick: t,
          children: l("إلغاء")
        })]
      })]
    })]
  });
}
function ok({
  v: e,
  onDone: t
}) {
  var p, m;
  const n = de(),
    [r, i] = w.useState(""),
    [a, o] = w.useState(),
    [c, d] = w.useState(""),
    u = W({
      queryKey: ["owner-pick", r],
      enabled: r.length >= 2 && !a,
      queryFn: () => M.get(`/api/customers${Re({
        q: r,
        limit: 6
      })}`)
    }),
    h = V({
      mutationFn: () => M.post(`/api/vehicles/${e.id}/change-owner`, {
        new_customer_id: a.id,
        reason: c || null
      }),
      onSuccess: () => {
        n.invalidateQueries({
          queryKey: ["vehicle", e.id]
        }), t();
      }
    });
  return s.jsxs(B, {
    title: l("نقل ملكية العربية"),
    children: [s.jsx("p", {
      className: "mb-3 text-slate-600",
      children: l("تاريخ الصيانة السابق يبقى باسم المالك القديم، والزيارات الجديدة تُسجَّل باسم المالك الجديد.")
    }), a ? s.jsxs("div", {
      className: "flex items-center justify-between rounded-xl bg-ok-soft p-3 font-bold text-ok",
      children: ["✔ ", a.full_name, s.jsx("button", {
        className: "underline",
        onClick: () => o(void 0),
        children: l("تغيير")
      })]
    }) : s.jsxs("div", {
      children: [s.jsx(E, {
        label: l("المالك الجديد"),
        children: s.jsx("input", {
          value: r,
          onChange: y => i(y.target.value),
          placeholder: l("ابحث بالاسم أو الموبايل")
        })
      }), (p = u.data) == null ? void 0 : p.items.map(y => s.jsxs("button", {
        onClick: () => o(y),
        className: "mt-2 block w-full rounded-xl bg-slate-100 p-3 text-start font-semibold hover:bg-brand-soft",
        children: [y.full_name, " — ", s.jsx("span", {
          dir: "ltr",
          children: y.mobile
        })]
      }, y.id))]
    }), s.jsx("div", {
      className: "mt-3",
      children: s.jsx(E, {
        label: l("السبب (اختياري)"),
        children: s.jsx("input", {
          value: c,
          onChange: y => d(y.target.value)
        })
      })
    }), s.jsxs("div", {
      className: "mt-3 space-y-2",
      children: [s.jsx($, {
        message: (m = h.error) == null ? void 0 : m.message
      }), s.jsxs("div", {
        className: "flex gap-3",
        children: [s.jsx(P, {
          icon: Ag,
          disabled: !a || h.isPending,
          onClick: () => confirm(l("تأكيد نقل الملكية؟")) && h.mutate(),
          children: l("نقل الملكية")
        }), s.jsx(P, {
          kind: "secondary",
          onClick: t,
          children: l("إلغاء")
        })]
      })]
    })]
  });
}
function ck({
  v: e
}) {
  const {
      can: t
    } = ce(),
    [n, r] = w.useState("");
  return t("vehicles.write") ? s.jsxs("div", {
    className: "no-print space-y-4",
    children: [s.jsxs("div", {
      className: "flex flex-wrap gap-3",
      children: [s.jsx(P, {
        kind: "secondary",
        icon: Mg,
        onClick: () => r(n === "edit" ? "" : "edit"),
        children: l("تعديل البيانات")
      }), s.jsx(P, {
        kind: "secondary",
        icon: Ag,
        onClick: () => r(n === "owner" ? "" : "owner"),
        children: l("نقل الملكية")
      })]
    }), n === "edit" && s.jsx(lk, {
      v: e,
      onDone: () => r("")
    }), n === "owner" && s.jsx(ok, {
      v: e,
      onDone: () => r("")
    })]
  }) : null;
}
function dk({
  value: e,
  onChange: t
}) {
  return s.jsx("div", {
    className: "grid grid-cols-3 gap-3 sm:grid-cols-5 lg:grid-cols-7",
    role: "radiogroup",
    "aria-label": l("نوع العطل"),
    children: Hn.map(({
      key: n,
      label: r,
      icon: i
    }) => s.jsxs("button", {
      type: "button",
      role: "radio",
      "aria-checked": e === n,
      onClick: () => t(e === n ? "" : n),
      className: `flex min-h-[96px] flex-col items-center justify-center gap-1 rounded-2xl border-4 p-2 text-base font-bold transition ${e === n ? "border-brand bg-brand-soft text-brand" : "border-slate-200 bg-white hover:border-brand/50"}`,
      children: [s.jsx(i, {
        size: 36,
        "aria-hidden": !0
      }), r]
    }, n))
  });
}
function uk({
  vehicle: e,
  onDone: t
}) {
  var p, m;
  const n = de(),
    [r, i] = w.useState(""),
    [a, o] = w.useState(((p = e.current_mileage) == null ? void 0 : p.toString()) ?? ""),
    [c, d] = w.useState(""),
    u = V({
      mutationFn: () => M.post("/api/visits", {
        vehicle_id: e.id,
        category: r || null,
        mileage: a ? Number(a) : null,
        complaint: c || null
      }),
      onSuccess: () => {
        n.invalidateQueries({
          queryKey: ["vehicle", e.id]
        }), n.invalidateQueries({
          queryKey: ["history", e.id]
        }), t();
      }
    }),
    h = y => {
      y.preventDefault(), u.mutate();
    };
  return s.jsx(B, {
    title: l("زيارة جديدة للورشة"),
    children: s.jsxs("form", {
      onSubmit: h,
      className: "space-y-4",
      children: [s.jsx(dk, {
        value: r,
        onChange: i
      }), s.jsxs("div", {
        className: "grid gap-4 sm:grid-cols-2",
        children: [s.jsx(E, {
          label: l("قراءة العداد (كم)"),
          children: s.jsx("input", {
            type: "number",
            min: 0,
            value: a,
            onChange: y => o(y.target.value),
            dir: "ltr",
            inputMode: "numeric"
          })
        }), s.jsx(E, {
          label: l("شكوى العميل"),
          children: s.jsx("input", {
            value: c,
            onChange: y => d(y.target.value)
          })
        })]
      }), s.jsx($, {
        message: (m = u.error) == null ? void 0 : m.message
      }), s.jsx(P, {
        type: "submit",
        icon: et,
        disabled: u.isPending,
        children: l("حفظ الزيارة")
      })]
    })
  });
}
function hk({
  v: e
}) {
  const [t, n] = w.useState(!1),
    r = Er(e.category),
    i = (r == null ? void 0 : r.icon) ?? ns,
    a = [[l("رقم الزيارة"), `#${e.visit_no}`], [l("العميل وقت الزيارة"), e.customer_name], [l("رقم اللوحة وقتها"), e.plate_at_visit], [l("الشكوى"), e.complaint], [l("التشخيص"), e.diagnosis], [l("الإصلاحات"), e.actual_repairs], [l("ملاحظات"), e.notes], [l("التكلفة"), Number(e.total_cost) ? Z("{0} ر.ق", e.total_cost) : void 0], [l("تاريخ التسليم"), e.delivered_at ? $e(e.delivered_at) : void 0]];
  return s.jsxs("li", {
    className: "relative ps-10",
    children: [s.jsx("span", {
      className: "absolute start-0 top-3 flex h-8 w-8 items-center justify-center rounded-full bg-brand text-white",
      children: s.jsx(i, {
        size: 18,
        "aria-hidden": !0
      })
    }), s.jsxs("button", {
      onClick: () => n(!t),
      "aria-expanded": t,
      className: "flex w-full flex-col items-stretch gap-3 rounded-2xl border-2 border-slate-200 bg-white p-4 text-start hover:border-brand sm:flex-row sm:items-center sm:justify-between",
      children: [s.jsxs("div", {
        className: "min-w-0",
        children: [s.jsxs("p", {
          className: "text-xl font-extrabold",
          children: [$e(e.arrival_at), " — ", (r == null ? void 0 : r.label) ?? l("زيارة")]
        }), s.jsx("p", {
          className: "text-slate-600",
          children: Gn(e.mileage)
        })]
      }), s.jsxs("div", {
        className: "flex items-center justify-between gap-2 sm:shrink-0",
        children: [s.jsxs("div", {
          className: "flex min-w-0 flex-wrap items-center gap-2 sm:justify-end",
          children: [s.jsx(Pr, {
            status: e.status
          }), s.jsx("span", {
            className: `rounded-full border px-3 py-1 text-xs font-bold ${e.invoice_status === "issued" ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-800"}`,
            children: e.invoice_status === "issued" ? l("تم إصدار الفاتورة") : e.invoice_status === "draft" ? l("مسودة فاتورة") : e.invoice_status === "cancelled" ? l("فاتورة ملغاة") : e.invoice_status === "not_invoiced" ? l("لم تصدر فاتورة") : l("حالة الفاتورة غير متاحة")
          })]
        }), t ? s.jsx(gb, {}) : s.jsx(Gx, {})]
      })]
    }), t && s.jsxs("dl", {
      className: "mt-2 grid gap-2 rounded-2xl bg-slate-50 p-4 sm:grid-cols-2",
      children: [a.filter(([, o]) => o).map(([o, c]) => s.jsxs("div", {
        children: [s.jsx("dt", {
          className: "text-sm font-semibold text-slate-500",
          children: o
        }), s.jsx("dd", {
          className: "text-lg font-bold",
          children: c
        })]
      }, o)), s.jsx(re, {
        to: `/jobs/${e.id}`,
        className: "no-print font-bold text-brand underline sm:col-span-2",
        children: l("فتح أمر الصيانة بكل التفاصيل ←")
      })]
    })]
  });
}
// Recovered route component for /vehicles/:id; original filename/name unknown.
function pk() {
  var k, _, S, T, R, F, X, te;
  const {
      id: e = ""
    } = Ds(),
    {
      can: t
    } = ce(),
    [n, r] = w.useState(!1),
    [i, a] = w.useState(""),
    [o, c] = w.useState(""),
    [d, u] = w.useState(""),
    h = W({
      queryKey: ["vehicle", e],
      queryFn: () => M.get(`/api/vehicles/${e}`)
    }),
    p = W({
      queryKey: ["history", e, i, o, d],
      queryFn: () => M.get(`/api/vehicles/${e}/history${Re({
        category: i,
        mileage_min: o,
        mileage_max: d
      })}`)
    }),
    m = W({
      queryKey: ["health", e],
      queryFn: () => M.get(`/api/vehicles/${e}/health`)
    }),
    y = W({
      queryKey: ["history-all", e],
      queryFn: () => M.get(`/api/vehicles/${e}/history${Re({
        limit: 100
      })}`)
    }),
    j = W({
      queryKey: ["vehicle-photo", e],
      queryFn: () => M.get(`/api/attachments?owner_type=vehicle&owner_id=${e}`)
    });
  if (h.isLoading) return s.jsx(ie, {});
  if (h.error || !h.data) return s.jsx($, {
    message: ((k = h.error) == null ? void 0 : k.message) ?? l("السيارة غير موجودة")
  });
  const v = h.data,
    N = (_ = j.data) == null ? void 0 : _.find(L => L.mime.startsWith("image/")),
    x = (((S = y.data) == null ? void 0 : S.items) ?? []).filter(L => L.mileage != null).map(L => ({
      x: new Date(L.arrival_at).getTime(),
      y: Number(L.mileage)
    })).sort((L, I) => L.x - I.x),
    f = m.data,
    g = f ? [f.overdue_reminders ? Z("{0} تذكير صيانة متأخر", f.overdue_reminders) : "", f.due_soon_reminders ? Z("{0} تذكير قريب الاستحقاق", f.due_soon_reminders) : "", f.critical_items ? Z("{0} بند حرج في آخر فحص", f.critical_items) : "", f.attention_items ? Z("{0} بند يحتاج انتباه في آخر فحص", f.attention_items) : ""].filter(Boolean) : [],
    b = (T = v.ownership_history) == null ? void 0 : T.find(L => !L.end_at);
  return s.jsxs(s.Fragment, {
    children: [s.jsxs(B, {
      action: s.jsx("div", {
        className: "no-print flex gap-2",
        children: s.jsx(P, {
          kind: "secondary",
          icon: fn,
          onClick: () => window.print(),
          children: l("طباعة")
        })
      }),
      children: [s.jsxs("div", {
        className: "flex items-start justify-between gap-4",
        children: [s.jsx("p", {
          className: "text-4xl font-extrabold",
          dir: "ltr",
          children: v.plate ?? l("بدون لوحة")
        }), s.jsx(ak, {
          id: v.id
        })]
      }), s.jsxs("p", {
        className: "mt-1 text-2xl font-bold",
        children: [v.make, " ", v.model, " ", v.model_year ?? "", " ", v.color ? `· ${v.color}` : ""]
      }), s.jsxs("div", {
        className: "mt-4 grid gap-4 sm:grid-cols-3",
        children: [s.jsx("div", {
          className: "flex h-36 items-center justify-center overflow-hidden rounded-2xl bg-slate-100",
          children: N ? s.jsx("img", {
            src: N.url,
            alt: N.name,
            className: "h-full w-full object-cover"
          }) : s.jsx("span", {
            className: "text-slate-400",
            children: l("لا توجد صورة")
          })
        }), s.jsxs("div", {
          children: [s.jsx("p", {
            className: "mb-1 text-sm font-semibold text-slate-500",
            children: l("تطور قراءة العداد")
          }), s.jsx(Mw, {
            points: x
          })]
        }), s.jsxs("div", {
          children: [s.jsx("p", {
            className: "mb-1 text-sm font-semibold text-slate-500",
            children: l("صحة العربية")
          }), f ? s.jsxs(s.Fragment, {
            children: [s.jsx(Tw, {
              score: f.score,
              level: f.level
            }), s.jsxs("p", {
              className: "mt-1 text-lg font-extrabold",
              children: [f.score, "% — ", f.level === "good" ? l("ممتازة") : f.level === "fair" ? l("تحتاج متابعة") : l("تحتاج صيانة عاجلة")]
            }), s.jsx("ul", {
              className: "text-sm text-slate-600",
              children: g.length ? g.map(L => s.jsxs("li", {
                children: ["• ", L]
              }, L)) : s.jsx("li", {
                children: l("لا توجد ملاحظات")
              })
            })]
          }) : s.jsx(ie, {})]
        })]
      }), s.jsxs("dl", {
        className: "mt-4 grid gap-3 sm:grid-cols-3",
        children: [s.jsxs("div", {
          children: [s.jsx("dt", {
            className: "text-sm font-semibold text-slate-500",
            children: l("المالك الحالي")
          }), s.jsx("dd", {
            className: "text-xl font-bold",
            children: (b == null ? void 0 : b.customer_name) ?? "—"
          })]
        }), s.jsxs("div", {
          children: [s.jsx("dt", {
            className: "text-sm font-semibold text-slate-500",
            children: l("العداد")
          }), s.jsx("dd", {
            className: "text-xl font-bold",
            children: Gn(v.current_mileage)
          })]
        }), s.jsxs("div", {
          children: [s.jsx("dt", {
            className: "text-sm font-semibold text-slate-500",
            children: l("رقم الشاسيه")
          }), s.jsx("dd", {
            className: "text-xl font-bold",
            dir: "ltr",
            children: v.vin ?? "—"
          })]
        })]
      }), (((R = v.plate_history) == null ? void 0 : R.length) ?? 0) > 1 && s.jsxs("p", {
        className: "mt-3 text-slate-600",
        children: [l("لوحات سابقة:"), " ", s.jsx("span", {
          dir: "ltr",
          children: v.plate_history.filter(L => L.end_at).map(L => L.plate).join(l("، "))
        })]
      }), (((F = v.ownership_history) == null ? void 0 : F.length) ?? 0) > 1 && s.jsxs("p", {
        className: "mt-1 text-slate-600",
        children: [l("ملاك سابقون:"), " ", v.ownership_history.filter(L => L.end_at).map(L => L.customer_name).join(l("، "))]
      })]
    }), s.jsx(ck, {
      v
    }), s.jsx("div", {
      className: "no-print",
      children: s.jsx(Ru, {
        ownerType: "vehicle",
        ownerId: v.id,
        title: l("صور العربية")
      })
    }), t("visits.write") && !n && s.jsx("div", {
      className: "no-print",
      children: s.jsx(P, {
        icon: ts,
        onClick: () => r(!0),
        children: l("زيارة جديدة")
      })
    }), n && s.jsx(uk, {
      vehicle: v,
      onDone: () => r(!1)
    }), s.jsxs(B, {
      title: Z("تاريخ العربية ({0})", ((X = p.data) == null ? void 0 : X.total) ?? 0),
      children: [s.jsxs("div", {
        className: "no-print mb-4 grid gap-3 sm:grid-cols-3",
        children: [s.jsx(E, {
          label: l("نوع الصيانة"),
          children: s.jsxs("select", {
            value: i,
            onChange: L => a(L.target.value),
            children: [s.jsx("option", {
              value: "",
              children: l("الكل")
            }), Hn.map(L => s.jsx("option", {
              value: L.key,
              children: L.label
            }, L.key))]
          })
        }), s.jsx(E, {
          label: l("من عداد"),
          children: s.jsx("input", {
            type: "number",
            min: 0,
            value: o,
            onChange: L => c(L.target.value),
            dir: "ltr"
          })
        }), s.jsx(E, {
          label: l("إلى عداد"),
          children: s.jsx("input", {
            type: "number",
            min: 0,
            value: d,
            onChange: L => u(L.target.value),
            dir: "ltr"
          })
        })]
      }), p.isLoading ? s.jsx(ie, {}) : p.error ? s.jsx($, {
        message: p.error.message
      }) : (te = p.data) != null && te.items.length ? s.jsx("ol", {
        className: "relative space-y-4 before:absolute before:start-4 before:top-4 before:bottom-4 before:w-0.5 before:bg-slate-300",
        children: p.data.items.map(L => s.jsx(hk, {
          v: L
        }, L.id))
      }) : s.jsx(Ie, {
        icon: fu,
        text: l("لسه مفيش زيارات مسجلة للعربية دي")
      })]
    })]
  });
}
const fk = ["Toyota", "Nissan", "Hyundai", "Kia", "Honda", "Mitsubishi", "Chevrolet", "Ford", "Mercedes-Benz", "BMW", "Audi", "Lexus", "Suzuki", "Mazda", "Peugeot", "Renault", "Volkswagen", "Jeep", "Land Rover", "Isuzu"];
function mk({
  value: e,
  onChange: t
}) {
  var a;
  const [n, r] = w.useState(""),
    i = W({
      queryKey: ["cust-pick", n],
      enabled: n.length >= 2,
      queryFn: () => M.get(`/api/customers${Re({
        q: n,
        limit: 6
      })}`)
    });
  return e ? s.jsxs("div", {
    className: "flex items-center justify-between rounded-xl bg-ok-soft p-3 font-bold text-ok",
    children: ["✔ ", e.full_name, " ", s.jsx("button", {
      type: "button",
      className: "underline",
      onClick: () => t(void 0),
      children: l("تغيير")
    })]
  }) : s.jsxs("div", {
    children: [s.jsx("input", {
      value: n,
      onChange: o => r(o.target.value),
      placeholder: l("اكتب اسم العميل أو موبايله")
    }), (a = i.data) == null ? void 0 : a.items.map(o => s.jsxs("button", {
      type: "button",
      onClick: () => t(o),
      className: "mt-2 block w-full rounded-xl bg-slate-100 p-3 text-start text-lg font-semibold hover:bg-brand-soft",
      children: [o.full_name, " — ", s.jsx("span", {
        dir: "ltr",
        children: o.mobile
      })]
    }, o.id)), i.data && !i.data.items.length && s.jsx("p", {
      className: "mt-2 text-slate-500",
      children: l("مفيش نتيجة — سجّل العميل الأول من صفحة العملاء")
    })]
  });
}
function xk({
  presetCustomer: e,
  onDone: t
}) {
  var y;
  const n = de(),
    r = es(),
    [i, a] = w.useState(),
    [o, c] = w.useState({
      make: "",
      model: "",
      model_year: "",
      plate: "",
      vin: "",
      color: "",
      current_mileage: ""
    }),
    d = W({
      queryKey: ["customer", e],
      enabled: !!e,
      queryFn: () => M.get(`/api/customers/${e}`)
    }),
    u = i ?? d.data,
    h = V({
      mutationFn: () => M.post("/api/vehicles", {
        customer_id: u == null ? void 0 : u.id,
        make: o.make,
        model: o.model,
        plate: o.plate || null,
        vin: o.vin || null,
        color: o.color || null,
        model_year: o.model_year ? Number(o.model_year) : null,
        current_mileage: o.current_mileage ? Number(o.current_mileage) : null
      }),
      onSuccess: j => {
        n.invalidateQueries({
          queryKey: ["vehicles"]
        }), t(), r(`/vehicles/${j.id}`);
      }
    }),
    p = j => v => c({
      ...o,
      [j]: v.target.value
    }),
    m = j => {
      j.preventDefault(), h.mutate();
    };
  return s.jsx(B, {
    title: l("تسجيل عربية جديدة"),
    children: s.jsxs("form", {
      onSubmit: m,
      className: "grid gap-4 sm:grid-cols-2",
      children: [s.jsx("div", {
        className: "sm:col-span-2",
        children: s.jsx(E, {
          label: l("صاحب العربية"),
          children: s.jsx(mk, {
            value: u,
            onChange: a
          })
        })
      }), s.jsxs(E, {
        label: l("الماركة"),
        children: [s.jsx("input", {
          list: "makes",
          value: o.make,
          onChange: p("make"),
          required: !0
        }), s.jsx("datalist", {
          id: "makes",
          children: fk.map(j => s.jsx("option", {
            value: j
          }, j))
        })]
      }), s.jsx(E, {
        label: l("الموديل"),
        children: s.jsx("input", {
          value: o.model,
          onChange: p("model"),
          required: !0
        })
      }), s.jsx(E, {
        label: l("سنة الصنع"),
        children: s.jsx("input", {
          value: o.model_year,
          onChange: p("model_year"),
          type: "number",
          min: 1900,
          max: 2100,
          inputMode: "numeric",
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("رقم اللوحة"),
        children: s.jsx("input", {
          value: o.plate,
          onChange: p("plate"),
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("رقم الشاسيه (VIN)"),
        children: s.jsx("input", {
          value: o.vin,
          onChange: p("vin"),
          dir: "ltr",
          maxLength: 32
        })
      }), s.jsx(E, {
        label: l("العداد (كم)"),
        children: s.jsx("input", {
          value: o.current_mileage,
          onChange: p("current_mileage"),
          type: "number",
          min: 0,
          inputMode: "numeric",
          dir: "ltr"
        })
      }), s.jsx(E, {
        label: l("اللون"),
        children: s.jsx("input", {
          value: o.color,
          onChange: p("color")
        })
      }), s.jsxs("div", {
        className: "sm:col-span-2 space-y-3",
        children: [s.jsx($, {
          message: (y = h.error) == null ? void 0 : y.message
        }), s.jsx(P, {
          type: "submit",
          icon: et,
          disabled: h.isPending || !u,
          children: l("حفظ")
        }), !u && s.jsx("p", {
          className: "text-slate-500",
          children: l("اختار صاحب العربية الأول")
        })]
      })]
    })
  });
}
// Recovered route component for /vehicles; original filename/name unknown.
function gk() {
  var d;
  const {
      can: e
    } = ce(),
    [t, n] = sa(),
    [r, i] = w.useState(""),
    a = t.get("customer") ?? void 0,
    o = t.get("new") === "1" && e("vehicles.write"),
    c = W({
      queryKey: ["vehicles", r, a],
      queryFn: () => M.get(`/api/vehicles${Re({
        q: r,
        customer_id: a
      })}`)
    });
  return s.jsxs(s.Fragment, {
    children: [s.jsxs("div", {
      className: "flex flex-wrap items-center justify-between gap-3",
      children: [s.jsxs("h1", {
        className: "flex items-center gap-2 text-3xl font-extrabold",
        children: [s.jsx(un, {
          size: 36
        }), l("العربيات")]
      }), e("vehicles.write") && !o && s.jsx(P, {
        icon: Bx,
        onClick: () => n(a ? {
          customer: a,
          new: "1"
        } : {
          new: "1"
        }),
        children: l("عربية جديدة")
      })]
    }), o && s.jsx(xk, {
      presetCustomer: a,
      onDone: () => n({})
    }), s.jsxs(B, {
      children: [s.jsx("input", {
        value: r,
        onChange: u => i(u.target.value),
        placeholder: l("ابحث برقم اللوحة أو الماركة أو الموديل"),
        className: "mb-4",
        "aria-label": l("بحث في العربيات")
      }), c.isLoading ? s.jsx(ie, {}) : c.error ? s.jsx($, {
        message: c.error.message
      }) : (d = c.data) != null && d.items.length ? s.jsx("div", {
        className: "grid gap-4 sm:grid-cols-2",
        children: c.data.items.map(u => s.jsxs(re, {
          to: `/vehicles/${u.id}`,
          className: "rounded-2xl border-2 border-slate-200 p-4 hover:border-brand",
          children: [s.jsx("p", {
            className: "text-2xl font-extrabold",
            dir: "ltr",
            children: u.plate ?? l("بدون لوحة")
          }), s.jsxs("p", {
            className: "text-lg font-semibold",
            children: [u.make, " ", u.model, " ", u.model_year ?? ""]
          }), s.jsx("p", {
            className: "text-slate-500",
            children: Gn(u.current_mileage)
          })]
        }, u.id))
      }) : s.jsx(Ie, {
        icon: un,
        text: l("مفيش عربيات مسجلة")
      })]
    })]
  });
}
function yk() {
  var f, g, b;
  const {
      user: e,
      loading: t,
      logout: n,
      can: r
    } = ce(),
    i = es(),
    [a, o] = w.useState(""),
    [c, d] = w.useState(!1),
    [u, h] = w.useState(!1),
    p = zs(),
    m = Xn();
  if (w.useEffect(() => {
    const k = () => d(!0);
    return window.addEventListener("autocare-maintenance", k), () => window.removeEventListener("autocare-maintenance", k);
  }, []), w.useEffect(() => {
    h(!1);
  }, [m.pathname]), t) return s.jsx(ie, {});
  if (!e) return s.jsx(hu, {
    to: "/login",
    replace: !0
  });
  const y = k => {
      k.preventDefault(), a.trim() && i(`/search?q=${encodeURIComponent(a.trim())}`);
    },
    j = (g = (f = p.data) == null ? void 0 : f.workshop) != null && g.name ? J(p.data.workshop.name) : "AutoCare Pro",
    v = s.jsxs("div", {
      className: "space-y-2 border-t border-white/10 pt-3",
      children: [s.jsxs(re, {
        to: "/account",
        className: "flex items-center gap-3 rounded-xl p-2 hover:bg-white/10",
        children: [s.jsx("span", {
          className: "flex h-10 w-10 items-center justify-center rounded-full bg-white/15 font-extrabold",
          children: e.full_name.slice(0, 1)
        }), s.jsxs("span", {
          className: "min-w-0 text-sm leading-tight",
          children: [s.jsx("b", {
            className: "block truncate",
            children: e.full_name
          }), s.jsx("span", {
            className: "text-white/60",
            children: J(e.role_label)
          })]
        })]
      }), s.jsxs("div", {
        className: "flex gap-2",
        children: [s.jsx(ad, {}), s.jsxs("button", {
          onClick: n,
          className: "flex min-h-[48px] flex-1 items-center justify-center gap-2 rounded-xl bg-white/10 px-3 font-bold hover:bg-white/20",
          children: [s.jsx(Eb, {
            size: 20
          }), l("خروج")]
        })]
      })]
    }),
    N = s.jsxs("div", {
      className: "flex items-center gap-3 px-1",
      children: [s.jsx("span", {
        className: "flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-brand-dark shadow",
        children: s.jsx(ns, {
          size: 24
        })
      }), s.jsx("span", {
        className: "truncate text-lg font-extrabold",
        children: j
      })]
    }),
    x = [{
      to: "/",
      icon: bg,
      label: l("الرئيسية"),
      show: !0,
      end: !0
    }, {
      to: "/reception",
      icon: mu,
      label: l("استقبال"),
      show: r("visits.write"),
      end: !1
    }, {
      to: "/board",
      icon: Vl,
      label: l("متابعة"),
      show: r("visits.read"),
      end: !1
    }, {
      to: "/search",
      icon: Wn,
      label: l("بحث"),
      show: r("vehicles.read"),
      end: !1
    }].filter(k => k.show);
  return s.jsxs("div", {
    className: "min-h-screen",
    children: [s.jsx(d2, {}), s.jsxs("aside", {
      className: "no-print fixed inset-y-0 start-0 z-20 hidden w-72 flex-col gap-5 bg-gradient-to-b from-navy to-brand-dark p-4 text-white lg:flex",
      children: [N, s.jsx("div", {
        className: "-mx-1 flex-1 overflow-y-auto px-1",
        children: s.jsx(fp, {})
      }), v]
    }), s.jsxs("div", {
      className: "lg:ps-72 print:ps-0",
      children: [((b = p.data) == null ? void 0 : b.demo) && s.jsx("div", {
        role: "note",
        className: "bg-wait p-2 text-center font-bold text-white",
        children: l("⚠️ بيانات تجريبية للعرض فقط — ليست سجلات حقيقية")
      }), s.jsxs("header", {
        className: "no-print sticky top-0 z-10 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur",
        children: [s.jsx("button", {
          onClick: () => h(!0),
          "aria-label": l("القائمة"),
          className: "flex min-h-[48px] min-w-[48px] items-center justify-center rounded-xl bg-brand-soft text-brand lg:hidden",
          children: s.jsx(up, {
            size: 26
          })
        }), s.jsxs("form", {
          onSubmit: y,
          className: "relative flex-1",
          children: [s.jsx(Wn, {
            size: 20,
            className: "pointer-events-none absolute start-4 top-1/2 -translate-y-1/2 text-slate-400",
            "aria-hidden": !0
          }), s.jsx("input", {
            value: a,
            onChange: k => o(k.target.value),
            placeholder: l("ابحث برقم اللوحة أو اسم العميل أو الموبايل…"),
            className: "!ps-12",
            "aria-label": l("بحث")
          })]
        })]
      }), c && s.jsxs("div", {
        role: "alert",
        className: "bg-wait p-4 text-center text-xl font-extrabold text-white",
        children: [l("النظام تحت الصيانة (استعادة نسخة احتياطية). انتظر دقائق ثم"), " ", s.jsx("button", {
          className: "underline",
          onClick: () => window.location.reload(),
          children: l("حدّث الصفحة")
        })]
      }), s.jsx("main", {
        className: "mx-auto max-w-6xl space-y-6 p-4 pb-28 sm:p-6 lg:pb-8",
        children: s.jsx(Aj, {})
      })]
    }), s.jsxs("nav", {
      "aria-label": l("القائمة"),
      className: "no-print fixed inset-x-0 bottom-0 z-20 flex border-t border-slate-200 bg-white/95 px-1 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden",
      children: [x.map(({
        to: k,
        icon: _,
        label: S,
        end: T
      }) => s.jsxs(Mx, {
        to: k,
        end: T,
        className: ({
          isActive: R
        }) => `flex min-h-[64px] flex-1 flex-col items-center justify-center gap-0.5 text-xs font-bold ${R ? "text-brand" : "text-slate-500"}`,
        children: [s.jsx(_, {
          size: 24,
          "aria-hidden": !0
        }), S]
      }, k)), s.jsxs("button", {
        onClick: () => h(!0),
        className: "flex min-h-[64px] flex-1 flex-col items-center justify-center gap-0.5 text-xs font-bold text-slate-500",
        children: [s.jsx(up, {
          size: 24,
          "aria-hidden": !0
        }), l("القائمة")]
      })]
    }), u && s.jsxs("div", {
      className: "no-print fixed inset-0 z-30 lg:hidden",
      children: [s.jsx("button", {
        "aria-label": l("إغلاق"),
        className: "absolute inset-0 bg-black/50",
        onClick: () => h(!1)
      }), s.jsxs("div", {
        className: "absolute inset-y-0 start-0 flex w-80 max-w-[85vw] flex-col gap-4 bg-gradient-to-b from-navy to-brand-dark p-4 text-white shadow-2xl",
        children: [s.jsxs("div", {
          className: "flex items-center justify-between",
          children: [N, s.jsx("button", {
            onClick: () => h(!1),
            "aria-label": l("إغلاق"),
            className: "flex h-11 w-11 items-center justify-center rounded-xl bg-white/10",
            children: s.jsx(ia, {
              size: 22
            })
          })]
        }), s.jsx("div", {
          className: "flex-1 overflow-y-auto",
          children: s.jsx(fp, {
            onNavigate: () => h(!1)
          })
        }), v]
      })]
    })]
  });
}
function vk() {
  return s.jsxs(qj, {
    children: [s.jsx(le, {
      path: "/login",
      element: s.jsx(Pw, {})
    }), s.jsxs(le, {
      element: s.jsx(yk, {}),
      children: [s.jsx(le, {
        index: !0,
        element: s.jsx(cw, {})
      }), s.jsx(le, {
        path: "/search",
        element: s.jsx(ik, {})
      }), s.jsx(le, {
        path: "/customers",
        element: s.jsx(c2, {})
      }), s.jsx(le, {
        path: "/vehicles",
        element: s.jsx(gk, {})
      }), s.jsx(le, {
        path: "/vehicles/:id",
        element: s.jsx(pk, {})
      }), s.jsx(le, {
        path: "/reception",
        element: s.jsx(Aw, {})
      }), s.jsx(le, {
        path: "/board",
        element: s.jsx(a2, {})
      }), s.jsx(le, {
        path: "/jobs/:id",
        element: s.jsx(_w, {})
      }), s.jsx(le, {
        path: "/jobs/:id/receipt",
        element: s.jsx(Bw, {})
      }), s.jsx(le, {
        path: "/technicians",
        element: s.jsx(rk, {})
      }), s.jsx(le, {
        path: "/suppliers",
        element: s.jsx(nk, {})
      }), s.jsx(le, {
        path: "/invoices",
        element: s.jsx(ow, {})
      }), s.jsx(le, {
        path: "/invoices/:id",
        element: s.jsx(aw, {})
      }), s.jsx(le, {
        path: "/expenses",
        element: s.jsx(h2, {})
      }), s.jsx(le, {
        path: "/finance",
        element: s.jsx(p2, {})
      }), s.jsx(le, {
        path: "/reminders",
        element: s.jsx(Qw, {})
      }), s.jsx(le, {
        path: "/backup",
        element: s.jsx(i2, {})
      }), s.jsx(le, {
        path: "/reports",
        element: s.jsx(Kw, {})
      }), s.jsx(le, {
        path: "/reports/:name",
        element: s.jsx(Vw, {})
      }), s.jsx(le, {
        path: "/settings",
        element: s.jsx(ek, {})
      }), s.jsx(le, {
        path: "/users",
        element: s.jsx(sk, {})
      }), s.jsx(le, {
        path: "/audit",
        element: s.jsx(Yb, {})
      }), s.jsx(le, {
        path: "/alerts",
        element: s.jsx(xy, {
          full: !0
        })
      }), s.jsx(le, {
        path: "/account",
        element: s.jsx(Kb, {})
      }), s.jsx(le, {
        path: "/jobs/:id/delivery-report",
        element: s.jsx(u2, {})
      }), s.jsx(le, {
        path: "/quotations/:id",
        element: s.jsx(Uw, {})
      })]
    }), s.jsx(le, {
      path: "*",
      element: s.jsx(hu, {
        to: "/",
        replace: !0
      })
    })]
  });
}
const jk = new D0({
  defaultOptions: {
    queries: {
      retry: !1,
      refetchOnWindowFocus: !1
    }
  }
});
ec.createRoot(document.getElementById("root")).render(s.jsx(sf.StrictMode, {
  children: s.jsx(c0, {
    client: jk,
    children: s.jsx(Jj, {
      children: s.jsx(Ub, {
        children: s.jsx(vk, {})
      })
    })
  })
}));
