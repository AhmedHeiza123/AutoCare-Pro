from datetime import date, datetime, time, timedelta, tzinfo


def next_day_start(d: date, tz: tzinfo) -> datetime:
    """Exclusive upper bound of the calendar day `d` (the start of the next day).

    The last representable day (9999-12-31) has no next day; it is clamped to its own last instant instead of raising
    OverflowError (which used to surface as an HTTP 500 on any report / filter whose end date was typed as year 9999)."""
    if d >= date.max:
        return datetime.combine(date.max, time.max, tz)
    return datetime.combine(d + timedelta(days=1), time.min, tz)
