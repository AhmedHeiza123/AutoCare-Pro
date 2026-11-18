import re

_AR_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640]")
_AR_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize(text: str | None) -> str:
    """Lowercase, strip Arabic diacritics, unify alef/yaa/taa-marbuta, map Arabic digits, drop separators."""
    if not text:
        return ""
    t = _AR_DIACRITICS.sub("", text).translate(_AR_MAP).translate(_AR_DIGITS).lower()
    return re.sub(r"\s+", " ", t).strip()


def compact(text: str | None) -> str:
    """Normalized with all spaces/dashes removed (for plates, VINs, phones)."""
    return re.sub(r"[\s\-]", "", normalize(text))


def digits(text: str | None) -> str:
    """Digits only (Arabic digits mapped), for phone-number comparison."""
    return re.sub(r"\D", "", normalize(text))
