"""Password hashing (Argon2id), session tokens, role/permission catalogue, rate limiting."""
import hashlib
import secrets
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()  # argon2-cffi defaults to Argon2id

MIN_PASSWORD_LEN = 8


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(hash_: str, password: str) -> bool:
    try:
        return _hasher.verify(hash_, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# A valid hash to verify against when the user does not exist (constant-ish timing).
DUMMY_HASH = hash_password("dummy-password-for-timing")


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---- permissions -----------------------------------------------------------
ALL_PERMISSIONS = [
    "customers.read", "customers.write",
    "vehicles.read", "vehicles.write",
    "visits.read", "visits.write",
    "users.manage", "audit.read",
    "backup.manage", "settings.manage",
    "technicians.manage", "jobs.override",
    "parts.write", "parts.costs", "suppliers.write", "quotes.write", "quotes.approve",
    "billing.read", "billing.write", "billing.refund", "expenses.read", "expenses.write", "reports.financial",
    "qc.write", "delivery.write", "warranties.decide",
]

ROLES: dict[str, tuple[str, list[str]]] = {
    "admin": ("مدير النظام", ALL_PERMISSIONS),
    "manager": ("مدير الورشة", ["customers.read", "customers.write", "vehicles.read", "vehicles.write",
                                "visits.read", "visits.write", "audit.read", "settings.manage",
                                "technicians.manage", "jobs.override", "parts.write", "parts.costs",
                                "suppliers.write", "quotes.write", "quotes.approve", "billing.read", "billing.write",
                                "billing.refund", "expenses.read", "expenses.write", "reports.financial",
                                "qc.write", "delivery.write", "warranties.decide"]),
    "receptionist": ("موظف استقبال", ["customers.read", "customers.write", "vehicles.read",
                                      "vehicles.write", "visits.read", "visits.write", "parts.write",
                                      "quotes.write", "quotes.approve", "billing.read", "billing.write", "delivery.write"]),
    "technician": ("فني", ["customers.read", "vehicles.read", "visits.read", "visits.write", "parts.write"]),
    "accountant": ("محاسب", ["customers.read", "vehicles.read", "visits.read", "parts.costs",
                             "suppliers.write", "billing.read", "billing.write", "billing.refund", "expenses.read",
                             "expenses.write", "reports.financial"]),
}


# ---- simple in-memory login rate limiter (per key, sliding window) ----------
class RateLimiter:
    def __init__(self, max_events: int, window_s: int):
        self.max, self.window = max_events, window_s
        self.events: dict[str, deque] = defaultdict(deque)

    def hit(self, key: str) -> bool:
        """Record an attempt; return False if the limit is exceeded."""
        now = time.monotonic()
        q = self.events[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max:
            return False
        q.append(now)
        return True

    def reset(self) -> None:
        self.events.clear()


login_limiter = RateLimiter(max_events=20, window_s=300)
