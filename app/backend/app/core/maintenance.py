"""Maintenance mode: while a restore runs, the API refuses requests (503). A flag file works across processes."""
from app.core.config import get_settings


def flag_path():
    return get_settings().storage_dir / "maintenance.flag"


def is_active() -> bool:
    return flag_path().exists()


def enter(reason: str = "restore") -> None:
    p = flag_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(reason, encoding="utf-8")


def leave() -> None:
    try:
        flag_path().unlink()
    except FileNotFoundError:
        pass
