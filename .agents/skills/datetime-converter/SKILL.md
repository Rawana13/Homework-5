---
name: datetime-converter
description: >
  Use this skill whenever a task involves time zone conversion, cross-city
  meeting scheduling (especially with Middle Eastern cities like Riyadh,
  Dubai, Abu Dhabi, Doha, Kuwait City, Manama, or Muscat), finding
  business-day overlaps between Gulf workweeks (Sunday–Thursday) and Western
  workweeks (Monday–Friday), or converting dates between Gregorian and
  Hijri/Islamic calendar formats. Trigger on phrases like "best meeting time",
  "find overlap", "what time is it in Riyadh", "convert to Hijri", "Islamic
  calendar date", "when is Ramadan", "Gulf timezone", "Saudi working hours",
  "schedule across time zones", or any scheduling/date-conversion request
  touching the Middle East. Always use this skill — do not attempt Hijri
  math or Gulf business-day logic manually; the tabular algorithm and DST
  handling require the bundled script.
---

# datetime-converter

Deterministic time zone conversion, Gulf-aware meeting scheduling, and
Gregorian ↔ Hijri calendar conversion using the tabular 30-year cycle
algorithm. Always invoke the bundled script for computations — LLM prose
arithmetic is unreliable for Hijri math and DST-aware overlaps.

## When to use

- Converting a Gregorian date to Hijri (Islamic) calendar, or vice versa
- Finding the best meeting window for teams that include Gulf cities
- Any scheduling question involving Saudi Arabia, UAE, Qatar, Kuwait, Bahrain, or Oman
- Checking whether a specific date is a business day under Gulf vs. Western rules
- Questions about Ramadan scheduling, Saudi/UAE public holidays, or Gulf weekend structure
- "What time is it in Riyadh when it's 9 AM in DC?"
- Any date arithmetic that crosses the Gregorian/Hijri boundary

## When NOT to use

- Pure Gregorian arithmetic with only Western cities — Python's `datetime` handles that.
- Scheduling questions involving *no* Gulf or Islamic calendar component.
- Requests requiring religious authority (exact Ramadan start by moon sighting) — refer users to official announcements.

---

## Expected inputs and outputs

### Hijri conversion (`--mode hijri`)

**Input:** A Gregorian date (`--date YYYY-MM-DD`).

**Output:**
```
Gregorian date : 2000-02-29 (Tuesday)
Hijri date     : 26 Dhul Qa'dah 1420 AH  (tabular, Thursday epoch)
Gregorian leap : Yes — February 29 is valid
Hijri leap yr  : No  (1420 is not a Hijri leap year)
⚠ Caveat       : Tabular result may differ ±1–2 days from the official
                 Umm al-Qura calendar (Saudi Arabia) or observed lunar calendar.
```

### Meeting finder (`--mode meeting`)

**Input:** `--cities "City1,City2"`, `--start YYYY-MM-DD`, `--end YYYY-MM-DD`.

**Output (per day with overlap):**
```
2026-04-27 (Monday)
  UTC window  : 13:00–14:00 UTC  (60 min)
  Washington DC : 09:00–10:00 EDT
  Riyadh        : 16:00–17:00 +03
```

**Output (no overlap):**
```
2000-02-29 (Tuesday)  ← work day for all cities
  ✗ No feasible overlap
    Riyadh workday ends 14:00 UTC; Washington DC workday starts 14:00 UTC.
    Recommend: async or one party adjusts core hours by 1h.
```

---

## Step-by-step agent instructions

### Step 1 — Parse the request

Identify:
1. **Mode**: Hijri conversion, meeting finder, or both (e.g., "convert Feb 29 2000 and find overlap").
2. **Cities** (for meeting mode) — the script handles name→timezone mapping for common cities. For unlisted cities, use the IANA timezone name directly.
3. **Date range** — default to the current Mon–Fri week if unspecified.
4. **Cultural context**: Does the period overlap with Ramadan or a Gulf public holiday?

### Step 2 — Apply Gulf-specific checks before running

**Ramadan check:**
If the user requests meetings during a Ramadan window (see table below):
- Add a prominent warning explaining that Gulf work hours are shortened (09:00–14:00 or 09:00–15:00 during Ramadan vs. 09:00–17:00 normally).
- Note that 2 PM Riyadh time during Ramadan falls at the very end of the shortened workday — people are fasting and energy is typically lowest.
- The script will automatically apply Ramadan hours (09:00–14:00) for Gulf cities when dates fall in these windows.

**"Daily recurring meetings for a month during Ramadan" — caution flag:**
If the user asks to schedule a recurring daily meeting throughout Ramadan:
1. **Do not schedule silently.** Explain the cultural and practical constraints.
2. State clearly: fasting employees work shorter hours, meetings late in the day (especially 2 PM) are at peak fatigue before Iftar.
3. Offer alternatives: early-morning slots (09:00–11:00 Riyadh), or post-Iftar evening (20:00–22:00 Riyadh, 13:00–15:00 EDT) which is outside Western business hours but may suit async or voluntary participants.
4. Ask for explicit confirmation before generating any schedule. If the user confirms they understand the constraints, then run the script and output the windows with the Ramadan warning attached to every entry.

**Saudi/UAE public holiday check:**
Read `references/gulf-holidays.md` for the full list. Exclude public holidays from meeting suggestions and note them in the output.

### Step 3 — Run the script

```bash
# Hijri conversion
python .agents/skills/datetime-converter/scripts/datetime_convert.py \
  --mode hijri --date YYYY-MM-DD

# Meeting finder
python .agents/skills/datetime-converter/scripts/datetime_convert.py \
  --mode meeting \
  --cities "City1,City2,City3" \
  --start YYYY-MM-DD \
  --end YYYY-MM-DD

# Combined (Hijri + meeting on the same date)
python .agents/skills/datetime-converter/scripts/datetime_convert.py \
  --mode both \
  --date YYYY-MM-DD \
  --cities "City1,City2,City3"
```

### Step 4 — Interpret and present results

**Hijri results:**
- Always include the ±1–2 day caveat (tabular vs. Umm al-Qura).
- For any official Islamic observance (Eid, Ramadan start), direct the user to [ummalqura.org.sa](https://ummalqura.org.sa) or a national authority announcement.

**Meeting results:**
- Lead with the best window(s) — highest overlap minutes first.
- If overlap < 30 minutes, flag it as "tight" and suggest adjusting one party's core hours.
- If no overlap exists: explain the exact cause (timezone gap, conflicting weekends, Ramadan hours) and suggest a practical fix.

---

## Gulf-specific rules

### Weekend & workweek structure

| Region | Weekend | Workweek |
|--------|---------|----------|
| Saudi Arabia, Kuwait, Bahrain, Qatar | Fri + Sat | Sun–Thu |
| UAE government / public sector | Fri + Sat | Sun–Thu |
| UAE private sector (since Jan 2022) | Sat + Sun | Mon–Fri |
| Western (US, UK, EU) | Sat + Sun | Mon–Fri |

> **UAE private sector exception (2022):** The UAE officially adopted a Mon–Fri
> workweek for government in January 2022, but practice varies by employer.
> When UAE is in scope, clarify if needed; default to Mon–Fri with a note.

### Ramadan working hours (Gulf)

During Ramadan, Gulf government offices and most businesses shorten the workday:
- **Government offices:** 09:00–14:00 (5-hour day)
- **Private sector:** typically 09:00–15:00, varies by company
- The script applies **09:00–14:00** for Gulf cities during Ramadan windows.
- 2 PM Riyadh during Ramadan = last hour before shortened day ends, coincides with peak fasting fatigue and proximity to Asr prayer.
- Post-Iftar (after ~18:30–19:30 Gulf time, seasonal) is culturally acceptable for calls.

### Approximate Ramadan windows (tabular)

| Hijri year | Approximate Gregorian start | Approximate end |
|------------|----------------------------|-----------------|
| 1447 AH    | ~1 March 2026              | ~29 March 2026  |
| 1448 AH    | ~18 February 2027          | ~18 March 2027  |
| 1449 AH    | ~7 February 2028           | ~7 March 2028   |

> True start depends on moon sighting; may differ by ±1 day from the table.

### Saudi public holidays — key recurring dates

See `references/gulf-holidays.md` for full 2024–2027 list.

| Holiday | Date |
|---------|------|
| Founding Day | 22 February |
| Eid al-Fitr (1–3 days) | 1 Shawwal (variable) |
| Eid al-Adha (4–5 days) | 10 Dhul Hijjah (variable) |
| Saudi National Day | 23 September |

---

## Hijri calendar caveat

The script uses the **tabular 30-year cycle** (Thursday/civil epoch):

- **Epoch:** 1 Muharram 1 AH = JDN 1,948,438 (≈ Thursday, July 15, 622 CE Julian)
- **Cycle length:** 10,631 days per 30 Hijri years
- **Leap years in cycle:** {2, 5, 7, 10, 13, 15, 18, 21, 24, 26, 29} → 11 leap years
- **Leap year rule:** Dhul Hijjah (month 12) has 30 days instead of 29
- **Month lengths:** Odd months = 30 days; even months = 29 days (except month 12 in leap years)

**Difference from other systems:**
| Calendar system | Description | Typical delta from tabular |
|-----------------|-------------|---------------------------|
| Tabular (this script) | Pure arithmetic, 30-year rule | 0 (reference) |
| Umm al-Qura | Saudi official, astronomical moonrise | ±1–2 days |
| Observed | Actual moon sighting, varies by country | ±1–3 days |

For more detail, see `references/hijri-algorithm.md`.
