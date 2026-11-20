"""Shared helpers for the financial regression tests.

The tests call the API functions directly against a REAL PostgreSQL database and TRUNCATE every table before each test, so they
must never be pointed at a production database. They refuse to run unless AUTOCARE_TEST_DATABASE_URL names a database whose name
contains "test". Example (a throw-away server on another port):

    set AUTOCARE_TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5599/autocare_test
    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import sys
import unittest
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

TEST_URL = os.environ.get("AUTOCARE_TEST_DATABASE_URL", "")
_name = TEST_URL.rsplit("/", 1)[-1].split("?")[0].lower()
ENABLED = bool(TEST_URL) and "test" in _name

if ENABLED:
    os.environ["AUTOCARE_DATABASE_URL"] = TEST_URL
    os.environ["AUTOCARE_MIGRATE_URL"] = TEST_URL
    os.environ.setdefault("AUTOCARE_SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    os.environ["AUTOCARE_DISABLE_SCHEDULER"] = "true"
    for _root in (BACKEND.parent, BACKEND.parent.parent):  # installed layout, or the installer package (<package>\app\backend)
        _pg_bin = _root / "runtime" / "pgsql" / "bin"  # pg_dump / pg_restore for the backup-compatibility tests
        if _pg_bin.is_dir():
            os.environ.setdefault("AUTOCARE_PG_BIN_DIR", str(_pg_bin))
            break
    import app.core.config as _config

    _config.Settings.model_config["env_file"] = None  # never read the real backend\.env during tests

    from sqlalchemy import select, text

    from app.api import auth, billing, finance, jobs, parts, quotes, reports
    from app.db import Base, SessionLocal, engine
    from app.models import Customer, Vehicle, VehicleVisit
    from app.models.auth import Role, User

D = Decimal


class FakeRequest:
    """Stand-in for fastapi.Request (the API only reads request.client for the audit trail)."""
    client = None
    headers: dict = {}


REQ = FakeRequest()


def migrate() -> None:
    from alembic import command
    from alembic.config import Config
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")


def reset_database() -> None:
    names = [t.name for t in Base.metadata.sorted_tables]
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE " + ", ".join(f'"{n}"' for n in names) + " RESTART IDENTITY CASCADE"))


class FinanceCase(unittest.TestCase):
    """Fresh, seeded database for every test + small builders that go through the real API functions."""

    @classmethod
    def setUpClass(cls):
        if not ENABLED:
            raise unittest.SkipTest("set AUTOCARE_TEST_DATABASE_URL to a database whose name contains 'test'")
        migrate()

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        auth.seed_roles(self.db)
        finance.seed_expense_categories(self.db)
        from app.models import Warehouse  # the migration seeds the default warehouse; TRUNCATE removed it, so seed it again
        self.db.add(Warehouse(code="MAIN", name_en="Main Workshop Warehouse", name_ar="المخزن الرئيسي للورشة", is_default=True, is_active=True))
        self.db.commit()
        role = self.db.scalar(select(Role).where(Role.name == "admin"))
        self.user = User(username="audit", full_name="Audit Tester", password_hash="x", role_id=role.id)
        self.db.add(self.user)
        self.db.commit()
        self._n = 0

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    # ---- builders ---------------------------------------------------------------
    def new_job(self) -> VehicleVisit:
        self._n += 1
        c = Customer(full_name=f"Customer {self._n}", mobile=f"5550{self._n:04d}", mobile_compact=f"5550{self._n:04d}", search_text="x")
        self.db.add(c)
        self.db.flush()
        v = Vehicle(make="Toyota", model="Camry", plate=f"A{self._n}", current_customer_id=c.id)
        self.db.add(v)
        self.db.flush()
        job = VehicleVisit(vehicle_id=v.id, customer_id=c.id, plate_at_visit=v.plate, status="in_progress")
        self.db.add(job)
        self.db.commit()
        return job

    def add_labor(self, job, amount, description="Labor"):
        body = jobs.OpIn(description=description, labor_hours=D("1"), labor_rate=D(str(amount)))
        op = jobs.add_operation(job.id, body, REQ, user=self.user, db=self.db)
        self.db.commit()
        return op

    def add_part(self, job, qty, cost, price, name="Brake pad", status="received"):
        body = parts.PartIn(part_name=name, quantity=D(str(qty)), unit_cost=D(str(cost)), unit_price=D(str(price)), status=status)
        out = parts.add_part(job.id, body, REQ, force=False, user=self.user, db=self.db)
        self.db.commit()
        return out

    def invoice(self, job, *, discount=None, tax_rate="0", issue=True, **extra):
        body = billing.InvoiceCreate(discount=None if discount is None else D(str(discount)), tax_rate=D(str(tax_rate)), **extra)
        inv = billing.create_invoice(job.id, body, REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        if issue:
            inv = billing.issue_invoice(inv["id"], REQ, user=self.user, db=self.db)
            self.db.commit()
        return inv

    def pay(self, invoice_id, amount):
        out = billing.record_payment(invoice_id, billing.PaymentIn(amount=D(str(amount)), method="cash"), REQ,
                                     idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        return out

    def credit(self, invoice_id, amount, reason="goodwill"):
        out = billing.create_credit_note(invoice_id, billing.CreditIn(amount=D(str(amount)), reason=reason), REQ, user=self.user, db=self.db)
        self.db.commit()
        return out

    def return_part(self, part_id, qty, refund=0):
        out = parts.return_part(part_id, parts.ReturnIn(quantity=D(str(qty)), refund_amount=D(str(refund)), reason="returned to supplier"),
                                REQ, user=self.user, db=self.db)
        self.db.commit()
        return out

    def summary(self):
        return {k: (D(v) if isinstance(v, str) and k not in ("currency",) else v)
                for k, v in finance.financial_summary(date_from=None, date_to=None, _=self.user, db=self.db).items()
                if k not in ("date_from", "date_to")}

    def report(self, name, **params):
        return reports.run(name, self.db, self.user, None, None, params)
