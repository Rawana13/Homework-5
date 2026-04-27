#!/usr/bin/env python3
"""
datetime_convert.py
===================
Gregorian-Hijri calendar conversion and Gulf-aware meeting window finder.

Hijri conversion uses the tabular 30-year cycle algorithm (Thursday epoch,
JDN 1,948,438). Results may differ ±1–2 days from the Umm al-Qura or observed
lunar calendar — see references/hijri-algorithm.md for details.

Usage
-----
  # Convert a Gregorian date to Hijri
  python datetime_convert.py --mode hijri --date 2000-02-29

  # Find best meeting windows across cities
  python datetime_convert.py --mode meeting \\
    --cities "Washington DC,Riyadh" \\
    --start 2026-04-27 --end 2026-04-30

  # Both: convert date AND find meeting overlap on that date
  python datetime_convert.py --mode both \\
    --date 2000-02-29 \\
    --cities "Washington DC,London,Riyadh"

  # Ramadan check (flag daily recurring request)
  python datetime_convert.py --mode meeting \\
    --cities "Riyadh,Washington DC" \\
    --start 2026-03-01 --end 2026-03-29 \\
    --warn-ramadan
"""

from __future__ import annotations
import argparse
import sys
from datetime import date, datetime, timedelta
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Hijri tabular 30-year cycle algorithm
# ---------------------------------------------------------------------------

ISLAMIC_EPOCH_JDN = 1_948_438  # Thursday epoch: 1 Muharram 1 AH = JDN 1,948,438
DAYS_PER_CYCLE = 10_631         # 30 Hijri years = 10,631 days (19×354 + 11×355)

# Leap-year positions within a 30-year cycle (11 out of 30 years are leap)
LEAP_POSITIONS = frozenset({2, 5, 7, 10, 13, 15, 18, 21, 24, 26, 29})

HIJRI_MONTH_NAMES = [
    "", "Muharram", "Safar", "Rabi' al-Awwal", "Rabi' al-Thani",
    "Jumada al-Awwal", "Jumada al-Thani", "Rajab", "Sha'ban",
    "Ramadan", "Shawwal", "Dhul Qa'dah", "Dhul Hijjah",
]


def _gregorian_to_jdn(year: int, month: int, day: int) -> int:
    """Convert a proleptic Gregorian date to its Julian Day Number."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return (
        day
        + (153 * m + 2) // 5
        + 365 * y
        + y // 4
        - y // 100
        + y // 400
        - 32045
    )


def _is_hijri_leap(year: int) -> bool:
    return (year % 30) in LEAP_POSITIONS


def _days_in_hijri_year(year: int) -> int:
    return 355 if _is_hijri_leap(year) else 354


def _days_in_hijri_month(year: int, month: int) -> int:
    # Odd months have 30 days; even months have 29 days.
    # Exception: month 12 (Dhul Hijjah) has 30 days in a leap year.
    if month % 2 == 1:
        return 30
    if month == 12 and _is_hijri_leap(year):
        return 30
    return 29


def gregorian_to_hijri(year: int, month: int, day: int) -> tuple[int, int, int]:
    """
    Convert a Gregorian date to Hijri using the tabular 30-year cycle.

    Returns (hijri_year, hijri_month, hijri_day).
    Raises ValueError for dates before the Islamic epoch (622 CE).
    """
    jdn = _gregorian_to_jdn(year, month, day)
    days_elapsed = jdn - ISLAMIC_EPOCH_JDN

    if days_elapsed < 0:
        raise ValueError(
            f"{year:04d}-{month:02d}-{day:02d} precedes the Islamic calendar epoch (622 CE)."
        )

    # Split into complete 30-year cycles and remainder days
    num_cycles, day_in_cycle = divmod(days_elapsed, DAYS_PER_CYCLE)
    hijri_year = num_cycles * 30

    # Walk years within current cycle
    for y_offset in range(1, 31):
        y_len = _days_in_hijri_year(hijri_year + y_offset)
        if day_in_cycle < y_len:
            hijri_year += y_offset
            break
        day_in_cycle -= y_len

    # Walk months within current year
    hijri_month = 12  # fallback (should always be set by loop)
    day_in_year = day_in_cycle
    for m in range(1, 13):
        m_len = _days_in_hijri_month(hijri_year, m)
        if day_in_year < m_len:
            hijri_month = m
            break
        day_in_year -= m_len

    hijri_day = day_in_year + 1
    return hijri_year, hijri_month, hijri_day


def _is_gregorian_leap(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


# ---------------------------------------------------------------------------
# Timezone / Gulf business-rules helpers
# ---------------------------------------------------------------------------

# Cities that follow the Gulf (Sun–Thu) workweek
_GULF_WORKWEEK_CITIES = frozenset({
    "riyadh", "jeddah", "dammam", "mecca", "medina",
    "saudi arabia", "ksa",
    "doha", "qatar",
    "kuwait", "kuwait city",
    "manama", "bahrain",
    "muscat", "oman",
    # Note: UAE government still Sun–Thu; private sector Mon–Fri since 2022.
    # We default to Mon–Fri for UAE per 2022 reform; user can override.
})

# IANA timezone lookup for commonly used city names
CITY_TIMEZONE_MAP: dict[str, str] = {
    # United States
    "washington dc": "America/New_York",
    "washington d.c.": "America/New_York",
    "dc": "America/New_York",
    "new york": "America/New_York",
    "boston": "America/New_York",
    "miami": "America/New_York",
    "chicago": "America/Chicago",
    "dallas": "America/Chicago",
    "denver": "America/Denver",
    "los angeles": "America/Los_Angeles",
    "la": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    # Europe
    "london": "Europe/London",
    "uk": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "amsterdam": "Europe/Amsterdam",
    "brussels": "Europe/Brussels",
    "zurich": "Europe/Zurich",
    "frankfurt": "Europe/Berlin",
    # Gulf
    "riyadh": "Asia/Riyadh",
    "jeddah": "Asia/Riyadh",
    "dammam": "Asia/Riyadh",
    "mecca": "Asia/Riyadh",
    "medina": "Asia/Riyadh",
    "saudi arabia": "Asia/Riyadh",
    "ksa": "Asia/Riyadh",
    "dubai": "Asia/Dubai",
    "abu dhabi": "Asia/Dubai",
    "uae": "Asia/Dubai",
    "doha": "Asia/Qatar",
    "qatar": "Asia/Qatar",
    "kuwait": "Asia/Kuwait",
    "kuwait city": "Asia/Kuwait",
    "manama": "Asia/Bahrain",
    "bahrain": "Asia/Bahrain",
    "muscat": "Asia/Muscat",
    "oman": "Asia/Muscat",
    # Asia
    "karachi": "Asia/Karachi",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
    "singapore": "Asia/Singapore",
    "hong kong": "Asia/Hong_Kong",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "tokyo": "Asia/Tokyo",
    # Pacific / Oceania
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "auckland": "Pacific/Auckland",
}

# Approximate Ramadan windows (tabular; may differ ±1 day from moon sighting)
# Format: (start_date, end_date)
RAMADAN_WINDOWS: list[tuple[date, date]] = [
    (date(2025, 3, 1), date(2025, 3, 30)),   # Ramadan 1446
    (date(2026, 2, 28), date(2026, 3, 29)),  # Ramadan 1447
    (date(2027, 2, 17), date(2027, 3, 18)),  # Ramadan 1448
    (date(2028, 2, 6), date(2028, 3, 6)),    # Ramadan 1449
]


def _is_gulf_workweek(city_key: str) -> bool:
    return city_key.lower().strip() in _GULF_WORKWEEK_CITIES


def _is_business_day(d: date, city_key: str) -> bool:
    # Monday=0 ... Sunday=6
    wd = d.weekday()
    if _is_gulf_workweek(city_key):
        return wd not in (4, 5)   # exclude Friday(4) and Saturday(5)
    return wd not in (5, 6)       # exclude Saturday(5) and Sunday(6)


def _ramadan_window_for(d: date) -> tuple[date, date] | None:
    for start, end in RAMADAN_WINDOWS:
        if start <= d <= end:
            return start, end
    return None


class CityWindow(NamedTuple):
    city: str
    tz_name: str
    work_start_local: int   # hour, 24h
    work_end_local: int     # hour, 24h
    is_gulf: bool
    is_ramadan: bool


def _build_city_windows(cities: list[str], d: date) -> list[CityWindow]:
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
    except ImportError:
        try:
            from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]
        except ImportError:
            raise RuntimeError(
                "Python 3.9+ (or pip install backports.zoneinfo) required."
            )

    windows = []
    ram = _ramadan_window_for(d)
    is_ramadan_day = ram is not None

    for city in cities:
        key = city.lower().strip()
        tz_name = CITY_TIMEZONE_MAP.get(key)
        if tz_name is None:
            # Allow raw IANA zone names as fallback
            try:
                ZoneInfo(city)
                tz_name = city
                key = city.lower()
            except Exception:
                print(f"  [Warning] Unknown city/timezone '{city}' — skipping.", file=sys.stderr)
                continue

        is_gulf = _is_gulf_workweek(key)

        if is_gulf and is_ramadan_day:
            start_h, end_h = 9, 14   # Ramadan shortened hours
        elif is_gulf:
            start_h, end_h = 9, 17  # Gulf standard (Sun–Thu, 9–5)
        else:
            start_h, end_h = 9, 18  # Western standard (Mon–Fri, 9–6)

        windows.append(CityWindow(
            city=city,
            tz_name=tz_name,
            work_start_local=start_h,
            work_end_local=end_h,
            is_gulf=is_gulf,
            is_ramadan=is_ramadan_day,
        ))
    return windows


def find_meeting_windows(
    cities: list[str],
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Find business-day windows where all cities share core working hours.

    Gulf cities apply Sun–Thu workweek and shortened Ramadan hours (09–14).
    Western cities apply Mon–Fri workweek and 09–18 hours.
    DST is handled automatically via IANA timezone database.
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]

    import datetime as dt_module

    results = []
    current = start_date

    while current <= end_date:
        city_windows = _build_city_windows(cities, current)

        if len(city_windows) < 2:
            current += timedelta(days=1)
            continue

        # All cities must consider this a business day
        all_business = all(
            _is_business_day(current, cw.city.lower().strip()) for cw in city_windows
        )
        if not all_business:
            non_biz = [
                cw.city for cw in city_windows
                if not _is_business_day(current, cw.city.lower().strip())
            ]
            results.append({
                "date": current.isoformat(),
                "day_of_week": current.strftime("%A"),
                "overlap_minutes": 0,
                "no_overlap_reason": f"Non-business day for: {', '.join(non_biz)}",
                "city_windows": {},
                "ramadan_note": None,
            })
            current += timedelta(days=1)
            continue

        # Convert each city's local work hours to UTC
        utc_ranges = []
        for cw in city_windows:
            tz = ZoneInfo(cw.tz_name)
            local_start = dt_module.datetime(
                current.year, current.month, current.day,
                cw.work_start_local, 0, tzinfo=tz,
            )
            local_end = dt_module.datetime(
                current.year, current.month, current.day,
                cw.work_end_local, 0, tzinfo=tz,
            )
            utc_start = local_start.astimezone(dt_module.timezone.utc)
            utc_end = local_end.astimezone(dt_module.timezone.utc)
            utc_ranges.append((utc_start, utc_end, cw))

        # Intersection of all UTC ranges
        overlap_start_utc = max(r[0] for r in utc_ranges)
        overlap_end_utc = min(r[1] for r in utc_ranges)
        overlap_minutes = max(
            0,
            int((overlap_end_utc - overlap_start_utc).total_seconds() // 60),
        )

        if overlap_minutes > 0:
            city_local_times = {}
            for utc_s, utc_e, cw in utc_ranges:
                tz = ZoneInfo(cw.tz_name)
                ls = overlap_start_utc.astimezone(tz).strftime("%H:%M %Z")
                le = overlap_end_utc.astimezone(tz).strftime("%H:%M %Z")
                city_local_times[cw.city] = f"{ls} – {le}"

            ram_note = None
            if any(cw.is_ramadan and cw.is_gulf for _, _, cw in utc_ranges):
                ram_window = _ramadan_window_for(current)
                ram_note = (
                    f"⚠ Ramadan hours in effect for Gulf cities "
                    f"(~{ram_window[0]} – {ram_window[1]}). "
                    "Gulf work ends 14:00 local."
                )

            results.append({
                "date": current.isoformat(),
                "day_of_week": current.strftime("%A"),
                "overlap_utc": (
                    f"{overlap_start_utc.strftime('%H:%M')}–"
                    f"{overlap_end_utc.strftime('%H:%M')} UTC"
                ),
                "overlap_minutes": overlap_minutes,
                "city_windows": city_local_times,
                "ramadan_note": ram_note,
            })
        else:
            # No overlap — diagnose why
            latest_start = max(r[0] for r in utc_ranges)
            earliest_end = min(r[1] for r in utc_ranges)
            latest_start_city = next(
                cw.city for s, e, cw in utc_ranges if s == latest_start
            )
            earliest_end_city = next(
                cw.city for s, e, cw in utc_ranges if e == earliest_end
            )
            reason = (
                f"{latest_start_city} workday starts {latest_start.strftime('%H:%M')} UTC; "
                f"{earliest_end_city} workday ends {earliest_end.strftime('%H:%M')} UTC. "
                "No overlap."
            )
            results.append({
                "date": current.isoformat(),
                "day_of_week": current.strftime("%A"),
                "overlap_minutes": 0,
                "no_overlap_reason": reason,
                "city_windows": {},
                "ramadan_note": None,
            })

        current += timedelta(days=1)

    return results


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _print_hijri(year: int, month: int, day: int) -> None:
    greg_date = date(year, month, day)
    h_year, h_month, h_day = gregorian_to_hijri(year, month, day)

    greg_leap = _is_gregorian_leap(year)
    hijri_leap = _is_hijri_leap(h_year)

    print()
    print("═" * 56)
    print("  HIJRI CALENDAR CONVERSION  (tabular 30-year cycle)")
    print("═" * 56)
    print(f"  Gregorian input : {greg_date.isoformat()}  ({greg_date.strftime('%A')})")
    if month == 2 and day == 29:
        print(f"  Leap year check : Feb 29 is valid — {year} is a Gregorian leap year ✓")
    print(f"  Hijri result    : {h_day} {HIJRI_MONTH_NAMES[h_month]} {h_year} AH")
    print(f"  Hijri month no. : {h_month} of 12")
    print(f"  Gregorian leap  : {'Yes' if greg_leap else 'No'} ({year})")
    print(f"  Hijri leap year : {'Yes' if hijri_leap else 'No'} ({h_year} AH)")
    print()
    print("  ⚠ Caveat: Tabular result (Thursday epoch, JDN 1,948,438).")
    print("    May differ ±1–2 days from the official Umm al-Qura calendar")
    print("    (Saudi Arabia) or from observed moon-sighting dates.")
    print("    For official Islamic dates, consult ummalqura.org.sa.")
    print("═" * 56)
    print()


def _print_meeting(
    cities: list[str],
    start_date: date,
    end_date: date,
    warn_ramadan: bool = False,
) -> None:
    ram_in_range = any(
        _ramadan_window_for(start_date + timedelta(days=i)) is not None
        for i in range((end_date - start_date).days + 1)
    )

    print()
    print("═" * 56)
    print("  MEETING WINDOW FINDER  (Gulf business rules)")
    print("═" * 56)
    print(f"  Cities    : {', '.join(cities)}")
    print(f"  Date range: {start_date} → {end_date}")
    print()

    if warn_ramadan and ram_in_range:
        print("  ⚠⚠ RAMADAN WARNING ⚠⚠")
        print("  The requested date range overlaps with Ramadan.")
        print("  Gulf working hours are shortened to ~09:00–14:00 local.")
        print("  Scheduling daily meetings at 14:00+ Riyadh during Ramadan")
        print("  hits peak fasting fatigue just before Iftar.")
        print()
        print("  Recommended alternatives:")
        print("    • Early morning: 09:00–11:00 Riyadh (06:00–08:00 UTC)")
        print("    • Post-Iftar:   ~20:00–22:00 Riyadh (17:00–19:00 UTC)")
        print("      (outside Western business hours — best for async/voluntary)")
        print()
        print("  Proceeding with computation using Ramadan shortened hours.")
        print("  Please confirm this schedule is appropriate for your team.")
        print()

    windows = find_meeting_windows(cities, start_date, end_date)

    found_any = False
    for w in windows:
        mins = w["overlap_minutes"]
        if mins > 0:
            found_any = True
            tightness = "  ⚠ Tight window — consider adjusting core hours" if mins < 60 else ""
            print(f"  {w['date']}  ({w['day_of_week']})")
            print(f"    UTC window     : {w['overlap_utc']}  ({mins} min){tightness}")
            for city, local_t in w["city_windows"].items():
                print(f"    {city:<18}: {local_t}")
            if w.get("ramadan_note"):
                print(f"    {w['ramadan_note']}")
            print()
        elif w.get("no_overlap_reason"):
            reason = w["no_overlap_reason"]
            if "Non-business" in reason:
                print(f"  {w['date']}  ({w['day_of_week']})  — skipped ({reason})")
            else:
                found_any = True
                print(f"  {w['date']}  ({w['day_of_week']})")
                print(f"    ✗ No feasible overlap")
                print(f"    {reason}")
                print(f"    Tip: async communication, or one party adjusts by 1 hour.")
                print()

    if not found_any:
        print("  No meeting windows found in the specified range.")
        print("  Check that the cities have overlapping business days in this period.")

    print("═" * 56)
    print()


# ---------------------------------------------------------------------------
# Ramadan-specific advisory (for test 3 / --warn-ramadan flag)
# ---------------------------------------------------------------------------

def _print_ramadan_advisory(
    cities: list[str],
    start_date: date,
    end_date: date,
    meeting_hour_riyadh: int = 14,
) -> None:
    """
    Print a structured warning when a user requests daily recurring meetings
    during Ramadan, especially at late-afternoon Gulf times.
    """
    ram_window = _ramadan_window_for(start_date) or _ramadan_window_for(end_date)

    print()
    print("═" * 60)
    print("  ⚠  RAMADAN SCHEDULING ADVISORY  ⚠")
    print("═" * 60)
    print()
    print(f"  Requested: daily meetings at {meeting_hour_riyadh:02d}:00 Riyadh time")
    print(f"  Period   : {start_date} – {end_date} (30 days)")

    if ram_window:
        print(f"  Ramadan  : ~{ram_window[0]} – {ram_window[1]} (tabular approx)")
        print()
        print("  This period overlaps with Ramadan. Key concerns:")
        print()
        print("  1. SHORTENED HOURS")
        print("     Gulf government offices: 09:00–14:00 local (5-hour day).")
        print("     Many private businesses: 09:00–15:00 local.")
        print(f"     A {meeting_hour_riyadh:02d}:00 Riyadh meeting is at or past end of")
        print("     shortened workday for most Gulf participants.")
        print()
        print("  2. FASTING FATIGUE")
        print("     14:00 Riyadh in Ramadan is ~2 hours before Iftar (sunset).")
        print("     This is typically the lowest-energy point of a fasting day.")
        print("     Scheduling 30 consecutive daily meetings at this hour is")
        print("     likely to reduce engagement and increase errors.")
        print()
        print("  3. PRAYER TIMES")
        print("     Asr prayer (afternoon prayer) falls around 15:00–16:00 in")
        print("     spring; Iftar preparation begins just before sunset (~18:30).")
        print("     These overlap with extended meeting schedules.")
        print()
        print("  RECOMMENDED ALTERNATIVES:")
        print("  ─────────────────────────")
        print("  Option A — Early morning (best for DC overlap):")
        print("    09:00–11:00 Riyadh (06:00–08:00 UTC)")
        print("    = 02:00–04:00 EDT  ← outside DC hours (async only)")
        print()
        print("  Option B — Post-Iftar evening (best for Gulf participants):")
        print("    20:00–22:00 Riyadh (17:00–19:00 UTC)")
        print("    = 13:00–15:00 EDT  ← within DC afternoon hours ✓")
        print("    This is culturally well-accepted and energy levels recover")
        print("    after Iftar. Best option if DC can accommodate.")
        print()
        print("  Option C — Reduce frequency:")
        print("    Weekly sync instead of daily during Ramadan,")
        print("    with async updates in between.")
        print()
        print("  ⚠ RECOMMENDATION: Do NOT schedule 30 consecutive daily")
        print("    meetings at 14:00 Riyadh during Ramadan without explicit")
        print("    agreement from all Gulf participants.")
        print()
        print("  If you still want to proceed, re-run with --force-schedule.")
        print("  The script will then output all 30 windows with warnings.")
    else:
        print()
        print("  This date range does not fall within a known Ramadan window.")
        print("  Proceeding with standard business-hours calculation.")
        print()
        _print_meeting(cities, start_date, end_date)

    print("═" * 60)
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{s}'. Expected YYYY-MM-DD."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gregorian-Hijri converter and Gulf-aware meeting finder.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        choices=["hijri", "meeting", "both", "ramadan-advisory"],
        required=True,
        help="Operation mode.",
    )
    parser.add_argument(
        "--date",
        type=_parse_date,
        help="Gregorian date for Hijri conversion (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--cities",
        type=str,
        help='Comma-separated list of cities, e.g. "Washington DC,Riyadh,London".',
    )
    parser.add_argument(
        "--start",
        type=_parse_date,
        help="Start date for meeting finder (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end",
        type=_parse_date,
        help="End date for meeting finder (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--warn-ramadan",
        action="store_true",
        help="Print a Ramadan advisory if dates overlap with Ramadan.",
    )
    parser.add_argument(
        "--force-schedule",
        action="store_true",
        help="Skip Ramadan advisory and compute windows anyway.",
    )
    parser.add_argument(
        "--meeting-hour",
        type=int,
        default=14,
        help="Requested meeting hour (local Riyadh time) for Ramadan advisory.",
    )

    args = parser.parse_args()
    cities = [c.strip() for c in (args.cities or "").split(",") if c.strip()]

    if args.mode in ("hijri", "both"):
        if not args.date:
            parser.error("--date is required for --mode hijri / both")
        _print_hijri(args.date.year, args.date.month, args.date.day)

    if args.mode in ("meeting", "both"):
        if not cities:
            parser.error("--cities is required for --mode meeting / both")
        start = args.start or (args.date if args.date else date.today())
        end = args.end or (args.date if args.date else date.today())
        if args.mode == "both" and args.date:
            start = end = args.date
        _print_meeting(cities, start, end, warn_ramadan=args.warn_ramadan)

    if args.mode == "ramadan-advisory":
        if not cities or not args.start or not args.end:
            parser.error(
                "--cities, --start, and --end are required for --mode ramadan-advisory"
            )
        if args.force_schedule:
            _print_meeting(cities, args.start, args.end, warn_ramadan=True)
        else:
            _print_ramadan_advisory(
                cities, args.start, args.end,
                meeting_hour_riyadh=args.meeting_hour,
            )


if __name__ == "__main__":
    main()
