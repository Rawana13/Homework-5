# Hijri Calendar — Tabular 30-Year Cycle Algorithm

## Overview

The **Islamic (Hijri) calendar** is a purely lunar calendar of 12 months totaling
354 or 355 days per year. The year count begins from the **Hijra** (Prophet
Muhammad's migration from Mecca to Medina), corresponding to **622 CE** in the
Julian calendar.

Because a pure lunar calendar cannot be tied to a simple arithmetic rule the way
the Gregorian calendar can, several tabular approximations have been developed.
This skill uses the most widely cited one: the **30-year cycle** (also called the
"tabular" or "arithmetical" Islamic calendar).

---

## Epoch

The starting point of the Islamic calendar is **1 Muharram 1 AH**.

| Epoch variant | JDN | Julian calendar | Notes |
|---|---|---|---|
| **Thursday (civil)** | 1,948,438 | Thursday, ~July 15, 622 CE | Used in this script |
| Friday (astronomical) | 1,948,439 | Friday, July 16, 622 CE | Some Western sources |

The **Thursday epoch** (JDN 1,948,438) is used by most computational
implementations (e.g., Dershowitz & Reingold "Calendrical Calculations") and is
adopted by this script. The Friday epoch gives results one day later.

> **Converting to JDN from Gregorian:**
> ```
> a = (14 - month) // 12
> y = year + 4800 - a
> m = month + 12*a - 3
> JDN = day + (153*m + 2)//5 + 365*y + y//4 - y//100 + y//400 - 32045
> ```

---

## The 30-Year Cycle

The Islamic calendar uses a **30-year intercalation cycle** containing:
- **19 ordinary years** of 354 days each
- **11 leap years** of 355 days each

**Cycle length:** 19 × 354 + 11 × 355 = 6,726 + 3,905 = **10,631 days**

This is a close approximation of 30 true synodic lunar years (30 × 354.3672 ≈
10,631.0 days). The error is roughly 1 day per 2,500 years.

### Leap year positions within each 30-year cycle

The 11 leap years in a 30-year cycle occur at positions (when year mod 30 equals):

```
{2, 5, 7, 10, 13, 15, 18, 21, 24, 26, 29}
```

> **Check:** `year % 30 in {2, 5, 7, 10, 13, 15, 18, 21, 24, 26, 29}`

**Variant sets:** Some historical sources use `{2, 5, 7, 10, 13, 16, 18, 21, 24, 26, 29}`
(differing at position 15 vs. 16). This is the "Ulugh Beg" set used in some Ottoman
calendars. The difference shifts results by at most 1 day starting from year 435 AH.
This script uses the more common Kūshyār ibn Labbān set.

---

## Month Structure

The Islamic year has **12 months**:

| # | Month name | Ordinary length | Length in Hijri leap year |
|---|-----------|----------------|--------------------------|
| 1 | Muharram | 30 days | 30 days |
| 2 | Safar | 29 days | 29 days |
| 3 | Rabi' al-Awwal | 30 days | 30 days |
| 4 | Rabi' al-Thani | 29 days | 29 days |
| 5 | Jumada al-Awwal | 30 days | 30 days |
| 6 | Jumada al-Thani | 29 days | 29 days |
| 7 | Rajab | 30 days | 30 days |
| 8 | Sha'ban | 29 days | 29 days |
| 9 | Ramadan | 30 days | 30 days |
| 10 | Shawwal | 29 days | 29 days |
| 11 | Dhul Qa'dah | 30 days | 30 days |
| 12 | Dhul Hijjah | 29 days | **30 days** (leap years only) |

**Pattern:** Odd months = 30 days; even months = 29 days.
**Leap exception:** Only month 12 gains a day in a leap year.

**Ordinary year total:** 6×30 + 6×29 = 180 + 174 = **354 days**
**Leap year total:** 6×30 + 5×29 + 1×30 = 180 + 145 + 30 = **355 days** ✓

---

## Conversion Algorithm (Gregorian → Hijri)

```python
EPOCH = 1_948_438        # Thursday epoch JDN
CYCLE = 10_631           # days per 30-year cycle
LEAP_SET = {2,5,7,10,13,15,18,21,24,26,29}

def gregorian_to_hijri(year, month, day):
    jdn          = gregorian_to_jdn(year, month, day)
    elapsed      = jdn - EPOCH
    cycles, rem  = divmod(elapsed, CYCLE)
    h_year       = cycles * 30

    for y in range(1, 31):
        y_len = 355 if (h_year + y) % 30 in LEAP_SET else 354
        if rem < y_len:
            h_year += y
            break
        rem -= y_len

    h_month = 1
    for m in range(1, 13):
        # odd months = 30; month 12 in leap year = 30; else 29
        m_len = 30 if m % 2 == 1 or (m == 12 and h_year % 30 in LEAP_SET) else 29
        if rem < m_len:
            h_month = m
            break
        rem -= m_len

    return h_year, h_month, rem + 1   # rem+1 converts 0-based to 1-based day
```

---

## Worked Example: February 29, 2000

**Step 1 — JDN of Feb 29, 2000:**
```
a = (14−2)//12 = 1;  y = 2000+4800−1 = 6799;  m = 2+12−3 = 11
JDN = 29 + (153×11+2)//5 + 365×6799 + 6799//4 − 6799//100 + 6799//400 − 32045
    = 29 + 337 + 2,481,635 + 1,699 − 67 + 16 − 32,045
    = 2,451,604
```

**Step 2 — Elapsed days:**
`2,451,604 − 1,948,438 = 503,166`

**Step 3 — 30-year cycles:**
`503,166 ÷ 10,631 = 47 cycles remainder 3,509`
`h_year = 47 × 30 = 1,410`

**Step 4 — Year within cycle (cycle years 1411–1440):**

| Offset | Year AH | Leap? | Days | Running rem |
|--------|---------|-------|------|-------------|
| 1 | 1411 | No | 354 | 3,155 |
| 2 | 1412 | No | 354 | 2,801 |
| 3 | 1413 | **Yes** | 355 | 2,446 |
| 4 | 1414 | No | 354 | 2,092 |
| 5 | 1415 | **Yes** | 355 | 1,737 |
| 6 | 1416 | No | 354 | 1,383 |
| 7 | 1417 | No | 354 | 1,029 |
| 8 | 1418 | **Yes** | 355 | 674 |
| 9 | 1419 | No | 354 | 320 |
| **10** | **1420** | **No** | **354** | **320 < 354 → stop** |

`h_year = 1420`

**Step 5 — Month within year 1420 (not a leap year):**

| Month | Name | Days | Running rem |
|-------|------|------|-------------|
| 1 | Muharram | 30 | 290 |
| 2 | Safar | 29 | 261 |
| 3 | Rabi' al-Awwal | 30 | 231 |
| 4 | Rabi' al-Thani | 29 | 202 |
| 5 | Jumada al-Awwal | 30 | 172 |
| 6 | Jumada al-Thani | 29 | 143 |
| 7 | Rajab | 30 | 113 |
| 8 | Sha'ban | 29 | 84 |
| 9 | Ramadan | 30 | 54 |
| 10 | Shawwal | 29 | 25 |
| **11** | **Dhul Qa'dah** | **30** | **25 < 30 → stop** |

`h_month = 11, h_day = 25 + 1 = 26`

**Result: 26 Dhul Qa'dah 1420 AH** (tabular, Thursday epoch)

---

## Comparison with Other Systems

| System | Feb 29, 2000 | Notes |
|--------|-------------|-------|
| **Tabular (this script, Thursday epoch)** | 26 Dhul Qa'dah 1420 | Pure arithmetic |
| Tabular (Friday epoch, JDN 1,948,439) | 25 Dhul Qa'dah 1420 | 1-day shift |
| Umm al-Qura (Saudi official) | ~24 Dhul Qa'dah 1420 | Astronomical moonrise |
| Observed (moon sighting) | ~23–24 Dhul Qa'dah 1420 | Varies by country |

The tabular algorithm systematically runs **1–2 days ahead** of the Umm al-Qura
calendar. This is a known, expected property — not a bug.

---

## Why Tabular ≠ Observed

The true Islamic month begins at the **first sighting of the crescent moon**
(hilal) after the astronomical new moon. This depends on:

1. **Geographic location** of the observer
2. **Atmospheric conditions** (clouds, haze)
3. **Whether naked-eye or telescopic observation** is accepted
4. **National authority decisions** (Saudi Arabia, Iran, Malaysia, etc., can
   differ by 1 day from each other)

The astronomical new moon (conjunction) precedes the crescent by ~1–2 days.
The Umm al-Qura calendar uses a computational moonrise criterion over Mecca,
which approximates sighting but may still differ from actual sighting by ±1 day.

**Rule of thumb:** For historical research or rough date estimation, tabular is
fine. For any religious obligation (fasting start, Eid prayer), always use the
official announcement from the relevant national authority.

---

## References

- Dershowitz, N. & Reingold, E. M. (2008). *Calendrical Calculations* (3rd ed.). Cambridge University Press.
- King, D. A. (1987). "The Astronomy of the Mamluks." *Isis*, 74(4).
- Umm al-Qura calendar: [https://ummalqura.org.sa](https://ummalqura.org.sa)
- Islamic Calendar Wikipedia: [https://en.wikipedia.org/wiki/Islamic_calendar](https://en.wikipedia.org/wiki/Islamic_calendar)
