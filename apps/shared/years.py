"""One place that knows what an A.Y. is: two consecutive years, June to May."""
import re
from datetime import date

AY_PATTERN = re.compile(r"^\s*(\d{4})\s*[-\u2013\u2014]\s*(\d{4})\s*$")


def parse_ay(text):
    """'2026-2027' -> (2026, 2027), or None when it is not two consecutive, plausible years."""
    m = AY_PATTERN.match(text or "")
    if not m:
        return None
    start, end = int(m.group(1)), int(m.group(2))
    if end != start + 1 or not 2000 <= start <= 2100:
        return None
    return start, end


def ay_dates(start_year):
    """An A.Y. runs 1 June of the first year to 31 May of the next."""
    return date(start_year, 6, 1), date(start_year + 1, 5, 31)
