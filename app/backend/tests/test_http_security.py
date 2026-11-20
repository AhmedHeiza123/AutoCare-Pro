"""HTTP-level QA tests: authentication, CSRF, role permissions, injection/XSS, uploads, information leakage, concurrency.

Unlike the other suites (which call the API functions directly) these tests talk to a REAL server process over HTTP, started against
the throw-away test database (see tests/_harness.py; never a production database).  Sessions are inserted directly for each role so
the in-memory login rate limiter (20 sign-ins / 5 min / IP) is only exercised by the tests that are about logging in.
"""
import http.client
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests._harness import BACKEND, D, ENABLED, FinanceCase, REQ

if ENABLED:
    import importlib
    import pkgutil

    from sqlalchemy import func, select

    import app.api as api_pkg
    from app.core.security import ROLES, hash_password, new_token, token_digest
    from app.db import SessionLocal
    from app.models import Customer, Payment
    from app.models.auth import Role, Session, User

PASSWORD = "Qa-Test-Pass-2026"  # throw-away value for users that exist only in the temporary database
PUBLIC = {("GET", "/api/auth/setup-needed"), ("POST", "/api/auth/setup"), ("POST", "/api/auth/login"), ("GET", "/api/restore/status")}
# never fuzzed: a (garbage-bodied) restore must not even be attempted against anything
SKIP_FUZZ = {("POST", "/api/restore"), ("POST", "/api/restore/preview"), ("POST", "/api/backups"), ("POST", "/api/backups/rescan"),
             ("POST", "/api/backups/recovery-secret"), ("PUT", "/api/backup-settings"),
             ("POST", "/api/auth/logout"), ("POST", "/api/auth/change-password")}  # these would end / change the sessions the other tests use


def all_routes():
    rows = []
    for mod in pkgutil.iter_modules(api_pkg.__path__):
        router = getattr(importlib.import_module("app.api." + mod.name), "router", None)
        for r in (router.routes if router else []):
            for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
                rows.append((m, r.path))
    return rows


def fill(path: str) -> str:
    """Replace path parameters with plausible values (a random uuid / 1) so the request reaches the authorization layer."""
    return re.sub(r"\{(\w+)\}", lambda m: "1" if m.group(1) in ("part_id", "payment_id", "credit_id", "op_id", "mid", "item_id", "rid", "pid")
                  else str(uuid.uuid4()), path)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Client:
    def __init__(self, port, token=None, csrf=None):
        self.port, self.token, self.csrf = port, token, csrf

    def call(self, method, path, body=None, headers=None, raw=None, timeout=30):
        h = {"Accept": "application/json"}
        if self.token:
            h["Cookie"] = f"ac_session={self.token}"
        if self.csrf:
            h["X-CSRF-Token"] = self.csrf
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        try:
            conn.request(method, path, body=data, headers=h)
            r = conn.getresponse()
            payload = r.read()
            try:
                js = json.loads(payload) if payload else None
            except ValueError:
                js = None
            return r.status, js, payload, r
        finally:
            conn.close()


class HttpCase(FinanceCase):
    """One server for the whole class; one shared database state (no per-test TRUNCATE: the sessions must survive)."""

    @classmethod
    def setUpClass(cls):
        if not ENABLED:
            raise unittest.SkipTest("set AUTOCARE_TEST_DATABASE_URL to a database whose name contains 'test'")
        from tests._harness import migrate, reset_database
        from app.api import auth, finance
        from app.models import Warehouse
        migrate()
        reset_database()
        db = SessionLocal()
        auth.seed_roles(db)
        finance.seed_expense_categories(db)
        db.add(Warehouse(code="MAIN", name_en="Main Workshop Warehouse", name_ar="المخزن الرئيسي للورشة", is_default=True, is_active=True))
        db.commit()
        cls.tokens = {}
        for name in ROLES:
            role = db.scalar(select(Role).where(Role.name == name))
            u = User(username=f"qa_{name}", full_name=f"QA {name}", password_hash=hash_password(PASSWORD), role_id=role.id)
            db.add(u)
            db.flush()
            token, csrf = new_token(), new_token()
            db.add(Session(token_hash=token_digest(token), user_id=u.id, csrf_token=csrf, expires_at=datetime.now(timezone.utc) + timedelta(hours=2)))
            cls.tokens[name] = (token, csrf)
        db.commit()
        db.close()
        cls.storage = tempfile.mkdtemp(prefix="autocare-http-")
        cls.port = free_port()
        env = dict(os.environ, AUTOCARE_PORT=str(cls.port), AUTOCARE_HOST="127.0.0.1", AUTOCARE_STORAGE_DIR=cls.storage, AUTOCARE_DISABLE_SCHEDULER="true")
        code = ("import sys; sys.path.insert(0, %r); import app.core.config as c; c.Settings.model_config['env_file']=None; "
                "from app.server import main; raise SystemExit(main())" % str(BACKEND))
        cls.proc = subprocess.Popen([sys.executable, "-X", "utf8", "-W", "ignore", "-c", code], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                if Client(cls.port).call("GET", "/health")[0] == 200:
                    break
            except OSError:
                pass
            time.sleep(0.5)
        else:
            cls.proc.kill()
            raise RuntimeError("the test server did not start")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "proc", None):
            cls.proc.terminate()
            try:
                cls.proc.wait(10)
            except subprocess.TimeoutExpired:
                cls.proc.kill()

    def setUp(self):  # deliberately NOT FinanceCase.setUp: keep the database (and the sessions) across tests
        self.db = SessionLocal()
        from app.models.auth import User as U
        self.user = self.db.scalar(select(U).where(U.username == "qa_admin"))
        self._n = getattr(type(self), "_counter", 0) + 100
        type(self)._counter = self._n

    def as_role(self, role="admin") -> Client:
        token, csrf = self.tokens[role]
        return Client(self.port, token, csrf)


class AuthenticationTests(HttpCase):
    def test_anonymous_requests_are_refused_on_every_route(self):
        anon = Client(self.port)
        bad = []
        for method, path in all_routes():
            if (method, path) in PUBLIC:
                continue
            status, _, _, _ = anon.call(method, fill(path), body={} if method != "GET" else None)
            if status != 401:
                bad.append((method, path, status))
        self.assertEqual(bad, [], "routes reachable without signing in")

    def test_csrf_token_is_required_for_every_state_changing_route(self):
        no_csrf = Client(self.port, self.tokens["admin"][0], None)
        bad = []
        for method, path in all_routes():
            if method == "GET" or (method, path) in PUBLIC or (method, path) in SKIP_FUZZ:
                continue
            status, js, _, _ = no_csrf.call(method, fill(path), body={})
            if status != 403 or (js or {}).get("error") not in ("csrf", None):
                bad.append((method, path, status))
        self.assertEqual(bad, [], "state-changing routes that work without the CSRF token")

    def test_wrong_csrf_token_is_refused(self):
        c = Client(self.port, self.tokens["admin"][0], "not-the-token")
        self.assertEqual(c.call("POST", "/api/expense-categories", body={"name": "x"})[0], 403)

    def test_login_failure_messages_do_not_reveal_whether_the_user_exists(self):
        anon = Client(self.port)
        a = anon.call("POST", "/api/auth/login", body={"username": "qa_admin", "password": "wrong-password"})
        b = anon.call("POST", "/api/auth/login", body={"username": "nobody_here", "password": "wrong-password"})
        self.assertEqual((a[0], b[0]), (401, 401))
        self.assertEqual(a[1]["message"], b[1]["message"])

    def test_session_cookie_flags_and_logout_invalidates_the_session(self):
        anon = Client(self.port)
        status, js, _, resp = anon.call("POST", "/api/auth/login", body={"username": "qa_receptionist", "password": PASSWORD})
        self.assertEqual(status, 200)
        cookie = resp.getheader("Set-Cookie")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        token = re.search(r"ac_session=([^;]+)", cookie).group(1)
        c = Client(self.port, token, js["csrf_token"])
        self.assertEqual(c.call("GET", "/api/auth/me")[0], 200)
        self.assertEqual(c.call("POST", "/api/auth/logout", body={})[0], 200)
        self.assertEqual(c.call("GET", "/api/auth/me")[0], 401, "the old cookie must stop working after logout")

    def test_account_is_locked_after_repeated_failures_even_with_the_right_password(self):
        from app.models.auth import User as U
        role = self.db.scalar(select(Role).where(Role.name == "technician"))
        self.db.add(U(username="qa_locktest", full_name="Lock test", password_hash=hash_password(PASSWORD), role_id=role.id))
        self.db.commit()
        anon = Client(self.port)
        codes = [anon.call("POST", "/api/auth/login", body={"username": "qa_locktest", "password": "bad"})[0] for _ in range(5)]
        self.assertEqual(codes, [401] * 5)
        self.assertEqual(anon.call("POST", "/api/auth/login", body={"username": "qa_locktest", "password": PASSWORD})[0], 423)

    def test_inactive_user_session_stops_working(self):
        from app.models.auth import User as U
        role = self.db.scalar(select(Role).where(Role.name == "technician"))
        u = U(username="qa_leaver", full_name="Leaver", password_hash=hash_password(PASSWORD), role_id=role.id)
        self.db.add(u)
        self.db.flush()
        token, csrf = new_token(), new_token()
        self.db.add(Session(token_hash=token_digest(token), user_id=u.id, csrf_token=csrf, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        self.db.commit()
        c = Client(self.port, token, csrf)
        self.assertEqual(c.call("GET", "/api/auth/me")[0], 200)
        u.is_active = False
        self.db.commit()
        self.assertEqual(c.call("GET", "/api/auth/me")[0], 401)

    def test_expired_session_is_refused(self):
        from app.models.auth import User as U
        u = self.db.scalar(select(U).where(U.username == "qa_manager"))
        token, csrf = new_token(), new_token()
        self.db.add(Session(token_hash=token_digest(token), user_id=u.id, csrf_token=csrf, expires_at=datetime.now(timezone.utc) - timedelta(seconds=5)))
        self.db.commit()
        self.assertEqual(Client(self.port, token, csrf).call("GET", "/api/auth/me")[0], 401)


class AuthorizationTests(HttpCase):
    def test_technician_cannot_reach_money_users_backup_or_audit(self):
        t = self.as_role("technician")
        for path in ("/api/users", "/api/backups", "/api/audit", "/api/expenses", "/api/reports/financial-summary", "/api/inventory/valuation",
                     "/api/inventory/supplier-balances", "/api/inventory/purchase-invoices", "/api/settings/security"):
            self.assertEqual(t.call("GET", path)[0], 403, path)
        for method, path in (("POST", "/api/users"), ("POST", "/api/expenses"), ("POST", "/api/inventory/adjustments"), ("POST", "/api/backups/rescan"),
                             ("POST", "/api/inventory/purchase-invoices")):
            self.assertEqual(t.call(method, path, body={})[0], 403, (method, path))

    def test_receptionist_and_storekeeper_limits(self):
        r, s = self.as_role("receptionist"), self.as_role("storekeeper")
        self.assertEqual(r.call("GET", "/api/inventory/purchase-invoices")[0], 403)
        self.assertEqual(r.call("POST", "/api/inventory/adjustments", body={})[0], 403)
        self.assertEqual(s.call("GET", "/api/users")[0], 403)
        self.assertEqual(s.call("GET", "/api/reports/financial-summary")[0], 403)

    def test_only_the_administrator_manages_users_and_nobody_sees_password_hashes(self):
        for role in ("manager", "accountant", "storekeeper", "receptionist", "technician"):
            self.assertEqual(self.as_role(role).call("POST", "/api/users", body={"username": "evil", "password": PASSWORD, "full_name": "x", "role": "admin"})[0], 403, role)
        status, _, payload, _ = self.as_role("admin").call("GET", "/api/users")
        self.assertEqual(status, 200)
        self.assertNotIn(b"password", payload.lower().replace(b"must_change_password", b""))
        self.assertNotIn(b"$argon2", payload)

    def test_no_route_ever_answers_500_to_any_role_with_empty_or_garbage_input(self):
        """Bounded fuzz over all routes x all roles: empty body, wrong types, absurd numbers. 5xx means an unhandled error."""
        garbage = [{}, {"amount": -1, "quantity": "abc", "name": "x" * 5000, "id": "not-a-uuid"}, {"amount": 10 ** 40, "qty": -10 ** 9}, [1, 2, 3]]
        bad = []
        started = time.time()
        for role in ("admin", "technician", "storekeeper"):
            c = self.as_role(role)
            for method, path in all_routes():
                if (method, path) in PUBLIC or (method, path) in SKIP_FUZZ:
                    continue
                if method == "GET":
                    status, _, _, _ = c.call("GET", fill(path) + ("?limit=-5&offset=abc&date_from=garbage&q=%27" if "?" not in path else ""))
                    if status >= 500:
                        bad.append((role, method, path, status))
                    continue
                for body in garbage:
                    status, _, _, _ = c.call(method, fill(path), body=body)
                    if status >= 500:
                        bad.append((role, method, path, status))
                if time.time() - started > 420:  # stop condition
                    break
        self.assertEqual(bad, [], "routes that return a server error for bad input")

    def test_extreme_dates_never_crash_a_report_or_filter(self):
        """BUG-001 regression: an end date of 9999-12-31 overflowed `date + 1 day` and returned HTTP 500 in five modules."""
        c = self.as_role("admin")
        ends = ("9999-12-31", "9999-12-30", "0001-01-01")
        for end in ends:
            for path in ("/api/reports/financial-summary?date_from=2026-01-01&date_to=%s", "/api/reports/received?date_from=0001-01-01&date_to=%s",
                         "/api/reports/inventory-stock?date_from=2026-01-01&date_to=%s", "/api/audit?date_from=2026-01-01&date_to=%s",
                         "/api/inventory/movements?date_to=%s", "/api/inventory/dashboard?date_to=%s", "/api/invoices?date_to=%s", "/api/expenses?date_to=%s"):
                status, js, _, _ = c.call("GET", path % end)
                self.assertIn(status, (200, 422), (path % end, status, js))
        status, js, _, _ = c.call("GET", "/api/reports/financial-summary?date_from=2026-01-01&date_to=9999-12-31")
        self.assertEqual(status, 200)
        self.assertEqual(js["date_to"], "9999-12-31")

    def test_money_amounts_are_always_echoed_with_two_decimals(self):
        """BUG-002 regression: an amount sent as 1e2 / 10 was echoed (and written to the audit trail) as "1E+2" / "10"."""
        c = self.as_role("admin")
        cat = c.call("GET", "/api/expense-categories")[1]
        cid = (cat.get("items") if isinstance(cat, dict) else cat)[0]["id"]
        for sent, expected in (("1e2", "100.00"), ("10", "10.00"), ("12.5", "12.50"), ("0.10", "0.10")):
            status, js, _, _ = c.call("POST", "/api/expenses", body={"category_id": cid, "amount": sent, "expense_date": "2026-11-19", "description": "format check"})
            self.assertEqual((status, js["amount"]), (201, expected), (sent, js))

    def test_payment_refund_and_credit_amounts_are_echoed_with_two_decimals(self):
        job = self.new_job()
        self.add_labor(job, 300)
        inv = self.invoice(job)
        c = self.as_role("admin")
        status, pay, _, _ = c.call("POST", f"/api/invoices/{inv['id']}/payments", body={"amount": "1e2", "method": "cash"}, headers={"Idempotency-Key": f"fmt-{uuid.uuid4()}"})
        self.assertEqual((status, pay["amount"]), (201, "100.00"), pay)
        status, ref, _, _ = c.call("POST", f"/api/payments/{pay['id']}/refunds", body={"amount": "5", "reason": "format check"})
        self.assertEqual((status, ref["amount"]), (201, "5.00"), ref)
        status, cn, _, _ = c.call("POST", f"/api/invoices/{inv['id']}/credit-notes", body={"amount": "1e1", "reason": "format check"})
        self.assertIn(status, (200, 201), cn)
        shown = c.call("GET", f"/api/invoices/{inv['id']}")[1]
        self.assertEqual([p["amount"] for p in shown["payments"]], ["100.00"])
        self.assertEqual([x["amount"] for x in shown["credit_notes"]], ["10.00"])

    def test_malformed_json_is_a_client_error(self):
        c = self.as_role("admin")
        for raw in (b"{not json", b"", b"\xff\xfe"):
            status, _, _, _ = c.call("POST", "/api/expense-categories", raw=raw, headers={"Content-Type": "application/json"})
            self.assertTrue(400 <= status < 500, status)


class InjectionAndLeakageTests(HttpCase):
    PAYLOADS = ["' OR 1=1 --", "'; DROP TABLE customers; --", "%' UNION SELECT password_hash FROM users --", "<script>alert(1)</script>", "\x00", "../../etc/passwd"]

    def test_search_and_filters_are_not_injectable(self):
        c = self.as_role("admin")
        self.db.add(Customer(full_name="Safe Customer", mobile="5551110000", mobile_compact="5551110000", search_text="safe customer"))
        self.db.commit()
        for p in self.PAYLOADS:
            from urllib.parse import quote
            for path in (f"/api/search?q={quote(p)}", f"/api/customers?search={quote(p)}", f"/api/vehicles?search={quote(p)}",
                         f"/api/inventory/items?q={quote(p)}", f"/api/inventory/movements?type={quote(p)}", f"/api/parts?q={quote(p)}",
                         f"/api/invoices?status={quote(p)}", f"/api/reports/inventory-stock?q={quote(p)}"):
                status, js, payload, _ = c.call("GET", path)
                self.assertLess(status, 500, (path, status))
                self.assertNotIn(b"password_hash", payload)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Customer)), 1, "the customers table must still exist and be intact")

    def test_stored_text_round_trips_as_data_and_is_served_as_json(self):
        c = self.as_role("admin")
        evil = "<img src=x onerror=alert(1)>'; DROP TABLE users;--"
        status, js, _, resp = c.call("POST", "/api/customers", body={"full_name": evil, "mobile": "5559990001"})
        self.assertEqual(status, 201, js)
        got = c.call("GET", f"/api/customers/{js['id']}")
        self.assertEqual(got[1]["full_name"], evil)
        self.assertTrue(got[3].getheader("Content-Type").startswith("application/json"))
        self.assertEqual(got[3].getheader("X-Content-Type-Options"), "nosniff")

    def test_security_headers_and_no_api_documentation_exposed(self):
        anon = Client(self.port)
        _, _, _, r = anon.call("GET", "/health")
        self.assertEqual(r.getheader("X-Frame-Options"), "DENY")
        self.assertIn("default-src 'self'", r.getheader("Content-Security-Policy"))
        for path in ("/docs", "/redoc", "/openapi.json"):
            status, js, payload, _ = anon.call("GET", path)
            self.assertNotIn(b"swagger", payload.lower())
            self.assertNotIn(b'"openapi"', payload)

    def test_static_file_server_cannot_be_walked_out_of_the_web_folder(self):
        anon = Client(self.port)
        for path in ("/..%2f..%2fbackend%2f.env", "/%2e%2e/%2e%2e/backend/.env", "/..\\..\\backend\\.env", "/assets/..%2f..%2f..%2fbackend%2falembic.ini",
                     "/%2e%2e%2f%2e%2e%2fbackend%2fapp%2fcore%2fconfig.py"):
            status, _, payload, _ = anon.call("GET", path)
            self.assertNotIn(b"SECRET_KEY", payload, path)
            self.assertNotIn(b"sqlalchemy.url", payload, path)
            self.assertNotIn(b"class Settings", payload, path)

    def test_error_responses_do_not_leak_internals(self):
        c = self.as_role("admin")
        status, _, payload, _ = c.call("GET", f"/api/customers/{uuid.uuid4()}")
        self.assertEqual(status, 404)
        for needle in (b"Traceback", b"sqlalchemy", b"psycopg", b"File \"", b"C:\\\\"):
            self.assertNotIn(needle, payload)
        status, _, payload, _ = c.call("GET", "/api/customers/not-a-uuid")
        self.assertLess(status, 500)
        self.assertNotIn(b"Traceback", payload)


class UploadTests(HttpCase):
    PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

    def multipart(self, owner_type, owner_id, filename, content, kind="photo"):
        b = "----qa" + secrets.token_hex(8)
        parts = []
        for k, v in (("owner_type", owner_type), ("owner_id", owner_id), ("kind", kind)):
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: image/png\r\n\r\n'.encode() + content + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        return b"".join(parts), {"Content-Type": f"multipart/form-data; boundary={b}"}

    def test_upload_accepts_real_images_only_and_never_trusts_the_file_name(self):
        job = self.new_job()
        c = self.as_role("admin")
        for name, content, expect in (("shell.exe", b"MZ\x90\x00" + b"\x00" * 100, 422), ("page.html.png", b"<html><script>alert(1)</script>", 422),
                                      ("fake.png", b"GIF" + b"\x00" * 20, 422), ("empty.png", b"", 422)):
            raw, h = self.multipart("visit", str(job.id), name, content)
            self.assertEqual(c.call("POST", "/api/attachments", raw=raw, headers=h)[0], expect, name)
        raw, h = self.multipart("visit", str(job.id), "..\\..\\..\\windows\\evil<name>.png", self.PNG)
        status, js, _, _ = c.call("POST", "/api/attachments", raw=raw, headers=h)
        self.assertEqual(status, 201, js)
        self.assertNotIn("..", js["name"])
        self.assertNotIn("\\", js["name"])
        stored = list(Path(self.storage, "attachments").rglob("*.png"))
        self.assertTrue(stored and all(Path(self.storage).resolve() in p.resolve().parents for p in stored), "files must stay inside the storage folder")
        status, _, payload, resp = c.call("GET", js["url"])
        self.assertEqual((status, resp.getheader("X-Content-Type-Options")), (200, "nosniff"))
        self.assertEqual(Client(self.port).call("GET", js["url"])[0], 401, "downloads need a session")

    def test_upload_size_limit_is_enforced_while_streaming(self):
        job = self.new_job()
        raw, h = self.multipart("visit", str(job.id), "big.png", self.PNG + b"\x00" * (10 * 1024 * 1024 + 1024))
        self.assertEqual(self.as_role("admin").call("POST", "/api/attachments", raw=raw, headers=h, timeout=60)[0], 413)

    def test_upload_to_unknown_owner_or_without_permission_is_refused(self):
        job = self.new_job()
        raw, h = self.multipart("visit", str(uuid.uuid4()), "a.png", self.PNG)
        self.assertEqual(self.as_role("admin").call("POST", "/api/attachments", raw=raw, headers=h)[0], 404)
        raw, h = self.multipart("purchase_invoice", str(uuid.uuid4()), "a.png", self.PNG, kind="document")
        self.assertEqual(self.as_role("technician").call("POST", "/api/attachments", raw=raw, headers=h)[0], 403)


class ConcurrencyOverHttpTests(HttpCase):
    def run_parallel(self, n, fn):
        results, lock = [], threading.Lock()

        def worker(i):
            r = fn(i)
            with lock:
                results.append(r)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(60)
        return results

    def test_same_idempotency_key_posts_one_payment_even_when_sent_in_parallel(self):
        job = self.new_job()
        self.add_labor(job, 100)
        inv = self.invoice(job)
        key = f"qa-{uuid.uuid4()}"
        c = self.as_role("admin")
        res = self.run_parallel(8, lambda i: c.call("POST", f"/api/invoices/{inv['id']}/payments", body={"amount": "100", "method": "cash"},
                                                    headers={"Idempotency-Key": key})[0])
        self.assertTrue(all(s in (200, 201, 409) for s in res), res)
        self.db.expire_all()
        n = self.db.scalar(select(func.count()).select_from(Payment).where(Payment.invoice_id == uuid.UUID(inv["id"])))
        total = self.db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.invoice_id == uuid.UUID(inv["id"])))
        self.assertEqual((n, total), (1, D("100")))

    def test_parallel_payments_with_different_keys_never_overpay_the_invoice(self):
        job = self.new_job()
        self.add_labor(job, 100)
        inv = self.invoice(job)
        c = self.as_role("admin")
        res = self.run_parallel(8, lambda i: c.call("POST", f"/api/invoices/{inv['id']}/payments", body={"amount": "100", "method": "cash"},
                                                    headers={"Idempotency-Key": f"qa-{uuid.uuid4()}"})[0])
        self.assertFalse(any(s >= 500 for s in res), res)
        self.db.expire_all()
        total = self.db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.invoice_id == uuid.UUID(inv["id"])))
        self.assertLessEqual(total, D("100"), f"invoice of 100 was paid {total} in parallel")

    def test_bounded_parallel_read_load_stays_healthy(self):
        c = self.as_role("admin")
        start = time.time()
        res = self.run_parallel(16, lambda i: [c.call("GET", p)[0] for p in ("/api/board", "/api/inventory/dashboard", "/api/reports/financial-summary", "/api/invoices?limit=50")])
        self.assertTrue(all(s == 200 for r in res for s in r), res)
        self.assertLess(time.time() - start, 60)


if __name__ == "__main__":
    unittest.main()
