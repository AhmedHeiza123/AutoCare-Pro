"""Realistic demonstration data, created in a SEPARATE database so it can never mix with real records.

    python -m app.sample_data --database autocare_demo
    set AUTOCARE_DATABASE_URL=postgresql+psycopg://user:pass@127.0.0.1:5432/autocare_demo   (then start the server)

Set AUTOCARE_DEMO_PASSWORD privately before running (at least 8 characters).
There is no default demo password, and it is never printed by this script.

The data is created through the real API (so every business rule applies) and then back-dated to look like a few
months of workshop activity. The database is flagged as demo and the screens show a "demo data" banner.
"""
import argparse
import os
import random
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

DEMO_USER = "demo"
NAMES = ["أحمد الكواري", "محمد المري", "خالد السليطي", "يوسف النعيمي", "سارة الهاجري", "فاطمة الدوسري", "عبدالله الكبيسي",
         "حمد العذبة", "ناصر الأنصاري", "ماجد البوعينين", "ريم الشمري", "علي المنصوري", "شركة النقل السريع", "مؤسسة الأفق للمقاولات"]
CARS = [("Toyota", "Camry", 2020), ("Toyota", "Land Cruiser", 2018), ("Nissan", "Patrol", 2019), ("Hyundai", "Sonata", 2021),
        ("Kia", "Sportage", 2022), ("Honda", "Accord", 2017), ("Mitsubishi", "Pajero", 2016), ("Ford", "F-150", 2020),
        ("Chevrolet", "Tahoe", 2019), ("Mercedes-Benz", "C200", 2018), ("BMW", "X5", 2021), ("Lexus", "ES350", 2019),
        ("Nissan", "Sunny", 2015), ("Toyota", "Hilux", 2022), ("Suzuki", "Swift", 2020)]
JOBS = [("oil", "تغيير زيت المحرك والفلتر", 0.5, 80, [("Engine oil 5W-30", "Mobil", 45, 70), ("Oil filter", "Toyota", 12, 30)]),
        ("brakes", "تغيير فحمات فرامل أمامية", 1.5, 90, [("Brake pads front", "Brembo", 110, 190)]),
        ("ac", "شحن فريون وفحص تسريب", 1.0, 90, [("R134a gas", "Generic", 40, 90)]),
        ("battery", "تغيير بطارية", 0.5, 70, [("Battery 70Ah", "Varta", 280, 420)]),
        ("tires", "ترصيص وميزان", 1.0, 60, []), ("suspension", "تغيير مساعدين أمامية", 3.0, 90, [("Front shock absorber", "KYB", 260, 400)]),
        ("cooling", "تغيير رادياتير", 2.0, 90, [("Radiator", "Denso", 350, 520)]), ("inspection", "فحص عام شامل", 1.0, 80, [])]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database", default="autocare_demo")
    ap.add_argument("--jobs", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)
    if not (a.database.startswith("autocare_demo") or a.database.endswith("_demo")):
        print("refusing: the demo database name must start with 'autocare_demo' or end with '_demo'")
        return 2

    demo_password = os.environ.get("AUTOCARE_DEMO_PASSWORD", "")
    if len(demo_password) < 8 or not demo_password.strip():
        print("refusing: set AUTOCARE_DEMO_PASSWORD privately to at least 8 characters (not whitespace only)")
        return 2

    from app.core import config  # no database engine is created by importing this
    base = config.get_settings().database_url
    from sqlalchemy.engine import make_url
    from app.backup import pgtools
    url = make_url(base)
    if not pgtools.database_exists(url, a.database):
        pgtools.create_database(url, a.database)
    demo_url = url.set(database=a.database).render_as_string(hide_password=False)
    env = {**os.environ, "AUTOCARE_MIGRATE_URL": demo_url}
    proc = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=config.BACKEND_DIR, env=env, capture_output=True)
    if proc.returncode:
        print(proc.stderr.decode()[-400:])
        return 1
    # point the application at the demo database BEFORE importing it
    os.environ["AUTOCARE_DATABASE_URL"] = demo_url
    os.environ["AUTOCARE_DISABLE_SCHEDULER"] = "1"
    config.get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from app.db import engine
    from app.main import app

    rnd = random.Random(a.seed)
    with TestClient(app, client=("127.0.0.1", 50000)) as c:
        if c.get("/api/auth/setup-needed").json()["setup_needed"] is False:
            print("demo database already contains data; use a new --database name")
            return 1
        c.post("/api/auth/setup", json={"username": DEMO_USER, "full_name": "مدير تجريبي", "password": demo_password,
                                        "workshop": {"name": "ورشة النموذج (بيانات تجريبية)", "phone": "44000000", "address": "الدوحة"},
                                        "currency": "QAR", "default_tax_rate": 0}).raise_for_status()
        csrf = c.post("/api/auth/login", json={"username": DEMO_USER, "password": demo_password}).json()["csrf_token"]
        H = {"X-CSRF-Token": csrf}

        def post(url, body=None, **kw):
            r = c.post(url, json=body or {}, headers=H, **kw)
            if r.status_code >= 400:
                raise SystemExit(f"{url} -> {r.status_code} {r.text[:200]}")
            return r.json()

        techs = [post("/api/technicians", {"employee_no": f"T{i + 1}", "name": n, "specialization": s})
                 for i, (n, s) in enumerate([("حسن الفني", "فرامل وعفشة"), ("إبراهيم", "كهرباء وتكييف"), ("سعيد", "موتور وفتيس"), ("طارق", "سمكرة ودهان")])]
        sups = [post("/api/suppliers", {"name": n, "phone": f"4455{i}000"}) for i, n in enumerate(["الفهد لقطع الغيار", "مؤسسة الخليج للبطاريات", "الدوحة للزيوت"])]
        custs = []
        for i, n in enumerate(NAMES):
            custs.append(post("/api/customers?force=true", {"full_name": n, "mobile": f"55{rnd.randint(100000, 999999)}",
                                                            "customer_type": "company" if "شركة" in n or "مؤسسة" in n else "individual"}))
        vehicles = []
        for i, (mk, md, yr) in enumerate(CARS):
            owner = custs[i % len(custs)]
            vehicles.append(post("/api/vehicles", {"customer_id": owner["id"], "make": mk, "model": md, "model_year": yr, "plate": f"{rnd.randint(100000, 999999)}",
                                                   "current_mileage": rnd.randint(20000, 160000), "color": rnd.choice(["أبيض", "أسود", "فضي", "رمادي", "أزرق"])}))
        cats = c.get("/api/expense-categories").json()
        done_jobs, open_jobs = [], []
        for n in range(a.jobs):
            v = vehicles[n % len(vehicles)]
            if any(j["vehicle_id"] == v["id"] for j in open_jobs):
                continue
            cat, desc, hrs, rate, parts = rnd.choice(JOBS)
            mileage = (v["current_mileage"] or 0) + rnd.randint(200, 4000)
            t = rnd.choice(techs)
            job = post("/api/reception", {"vehicle_id": v["id"], "mileage": mileage, "fuel_level": rnd.choice(["quarter", "half", "full"]),
                                          "complaints": [{"category": cat, "text": desc}], "technician_id": t["id"]})
            op = post(f"/api/jobs/{job['id']}/operations", {"category": cat, "description": desc, "technician_id": t["id"], "labor_hours": str(hrs), "labor_rate": str(rate)})
            for name, brand, cost, price in parts:
                p = post(f"/api/jobs/{job['id']}/parts", {"part_name": name, "brand": brand, "supplier_id": rnd.choice(sups)["id"], "quantity": "1", "unit_cost": str(cost),
                                                          "unit_price": str(price), "status": "received", "warranty_months": rnd.choice([0, 3, 6]) or None})
                post(f"/api/parts/{p['id']}/status", {"status": "installed", "technician_id": t["id"]})
            finished = n < a.jobs - 5  # the last few jobs stay open on the workshop board
            if not finished:
                if rnd.random() < 0.5:
                    c.patch(f"/api/operations/{op['id']}", json={"status": "in_progress"}, headers=H)
                post(f"/api/jobs/{job['id']}/status", {"status": rnd.choice(["under_inspection", "waiting_parts", "in_progress"])})
                open_jobs.append({**job, "vehicle_id": v["id"]})
                continue
            c.patch(f"/api/operations/{op['id']}", json={"status": "done"}, headers=H)
            post(f"/api/jobs/{job['id']}/quality-check", {"result": "passed", "repairs_verified": True, "parts_verified": True, "road_test_ok": True})
            inv = post(f"/api/jobs/{job['id']}/invoices", {"discount": str(rnd.choice([0, 0, 0, 10, 20]))})
            inv = post(f"/api/invoices/{inv['id']}/issue")
            if rnd.random() < 0.85:
                amount = inv["total"] if rnd.random() < 0.8 else str(round(float(inv["total"]) / 2, 2))
                post(f"/api/invoices/{inv['id']}/payments", {"amount": amount, "method": rnd.choice(["cash", "card", "bank_transfer"])})
            settled = c.get(f"/api/invoices/{inv['id']}").json()["outstanding"] == "0.00"
            # unpaid jobs leave through the audited manager override, like a trusted customer paying later
            post(f"/api/jobs/{job['id']}/deliver", {"final_mileage": mileage, "ack_name": "العميل", **({} if settled else {"override_reason": "عميل دائم - يسدد لاحقاً"})})
            done_jobs.append((job, v))
        for i in range(10):
            post("/api/expenses", {"category_id": rnd.choice(cats)["id"], "amount": str(rnd.choice([150, 300, 1200, 2500, 400])), "expense_date": str(date.today() - timedelta(days=rnd.randint(0, 80))),
                                   "description": rnd.choice(["فاتورة كهرباء", "إيجار الورشة", "صيانة رافعة", "أدوات وعدة", "مصاريف نظافة"])})
        # back-date everything so the history spans ~4 months
        with engine.begin() as conn:
            conn.execute(text("""
                update vehicle_visits set arrival_at = now() - (random() * interval '120 days') - interval '1 hour'
                where status in ('delivered', 'ready', 'quality_check') or delivered_at is not null"""))
            conn.execute(text("update vehicle_visits set delivered_at = arrival_at + interval '2 days', completed_at = arrival_at + interval '2 days' where delivered_at is not null"))
            conn.execute(text("update invoices set issued_at = (select arrival_at + interval '2 days' from vehicle_visits where id = invoices.visit_id), invoice_date = (select (arrival_at + interval '2 days')::date from vehicle_visits where id = invoices.visit_id)"))
            conn.execute(text("update payments set paid_at = (select arrival_at + interval '2 days' from vehicle_visits where id = payments.visit_id)"))
            conn.execute(text("insert into app_settings (key, value) values ('demo', '{\"demo\": true}') on conflict (key) do nothing"))
    print(f"demo database '{a.database}' ready: {len(done_jobs)} completed jobs, {len(open_jobs)} open, username {DEMO_USER}")
    print("Use the password supplied through AUTOCARE_DEMO_PASSWORD; it is not displayed.")
    print(f"start it with AUTOCARE_DATABASE_URL={url.set(database=a.database).render_as_string(hide_password=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
