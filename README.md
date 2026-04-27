# datetime-converter — Week 5 Skill Submission

**Course:** Agents & AI Systems | Week 5: Build a Reusable AI Skill
**Student:** Rawan Alsuwaidi
**Skill location:** `.agents/skills/datetime-converter/`

**Video demo:** [link TBD]

---

## What this skill does

`datetime-converter` gives Claude three deterministic capabilities that it
cannot reliably perform from prose alone:

| Capability | What it solves |
|------------|---------------|
| **Gregorian → Hijri conversion** | it is challenging to sync to Hijri dates
| **Cross-timezone meeting finder** | DST-aware UTC intersection across Gulf (Sun–Thu) and Western (Mon–Fri) workweeks |
| **Gulf business-rules awareness** | Ramadan shortened hours, Saudi/UAE public holidays, UAE weekend reform (2022) |

The skill bundles a Python script (`scripts/datetime_convert.py`) so the agent
runs actual code rather than estimating — and two reference documents covering
the Hijri algorithm and Gulf holiday calendar in detail.

---

## Why I chose this skill

I'm from Saudi Arabia and noticed that general-purpose scheduling tools
(Google Calendar, Calendly, World Time Buddy) all assume a Monday–Friday
workweek. They give wrong answers for Gulf business-day questions: they treat
Friday as a workday for Riyadh and Saturday as a holiday when it's actually
a regular working day in the Gulf.

The Hijri calendar is also genuinely hard for LLMs: the 30-year tabular cycle
involves modular arithmetic over multi-thousand-year epochs, and getting it
wrong by even one day can matter for religious observances, legal documents,
and public contracts in Saudi Arabia and the UAE.

This skill captures domain knowledge that is:
1. **Deterministic** — same inputs always produce the same output
2. **Non-obvious** — requires the tabular algorithm, not intuition
3. **Culturally specific** — Gulf rules that Western tools consistently miss
4. **Reusable** — any agent working with Gulf clients or Islamic dates needs it

---

## How to use the skill

Place the `.agents/` folder at the root of your project. Claude Code will
automatically detect and load skills from `.agents/skills/`.

### Triggering the skill

Say anything that involves Gulf scheduling or Hijri dates:

```
"Find the best meeting time this week for DC and Riyadh"
"Convert March 15, 2025 to the Hijri calendar"
"When does Eid al-Fitr fall in 2026?"
"Is April 30 a business day in Saudi Arabia?"
"Schedule a call with our Dubai team — what hours work?"
```

### Running the script directly

```bash
# Hijri conversion
python .agents/skills/datetime-converter/scripts/datetime_convert.py \
  --mode hijri --date 2000-02-29

# Meeting finder
python .agents/skills/datetime-converter/scripts/datetime_convert.py \
  --mode meeting \
  --cities "Washington DC,Riyadh" \
  --start 2026-04-27 --end 2026-04-30

# Combined: convert AND find overlap
python .agents/skills/datetime-converter/scripts/datetime_convert.py \
  --mode both \
  --date 2000-02-29 \
  --cities "Washington DC,London,Riyadh"

# Ramadan advisory (warns before scheduling)
python .agents/skills/datetime-converter/scripts/datetime_convert.py \
  --mode ramadan-advisory \
  --cities "Riyadh,Washington DC" \
  --start 2026-03-01 --end 2026-03-29 \
  --meeting-hour 14
```

**Python requirement:** 3.9+ (uses `zoneinfo` from the standard library).

---

## What the script does (technical)

### Gregorian → Hijri (tabular 30-year cycle)

1. Convert the Gregorian date to a **Julian Day Number (JDN)** using the
   standard proleptic Gregorian formula (verified against Python's `date.toordinal()`).
2. Compute days elapsed since the **Islamic epoch** (JDN 1,948,438 — Thursday,
   ~July 15, 622 CE Julian calendar).
3. Divide by 10,631 (days per 30-year cycle) to get complete cycles and
   a remainder.
4. Walk year-by-year within the cycle, subtracting each year's length (354 or
   355 days) until the remainder fits.
5. Walk month-by-month within the year (odd months = 30 days, even = 29,
   month 12 = 30 in leap years) until the remainder fits.
6. The final remainder + 1 is the Hijri day.

Leap years are those where `year % 30 ∈ {2, 5, 7, 10, 13, 15, 18, 21, 24, 26, 29}`.

### Meeting window finder

1. For each city, look up its **IANA timezone** (e.g., `America/New_York`,
   `Asia/Riyadh`).
2. Determine whether each city follows the **Gulf workweek** (Sun–Thu) or
   **Western workweek** (Mon–Fri) and filter out non-business days.
3. If the date falls in a **Ramadan window**, apply shortened Gulf hours
   (09:00–14:00 local) instead of standard (09:00–17:00).
4. Convert each city's work-hour range to **UTC** using Python's `zoneinfo`
   module, which handles DST transitions automatically.
5. Compute the **intersection** (latest start time, earliest end time) of all
   UTC ranges.
6. If the intersection is > 0 minutes, report it. Otherwise, diagnose which
   city pair is causing the conflict.

---

## Test results

### Test 1 — Normal: DC + Riyadh, week of Apr 27–30, 2026

**Input:** `--mode meeting --cities "Washington DC,Riyadh" --start 2026-04-27 --end 2026-04-30`

All four days (Mon–Thu) show a **1-hour overlap window**:
- UTC: 13:00–14:00
- DC: 09:00–10:00 EDT
- Riyadh: 16:00–17:00 +03

The window is tight (1 hour) because Riyadh's 17:00 end maps to 14:00 UTC,
which is exactly when DC's 09:00 EDT begins. The skill correctly flags this
as a "tight window" and notes that Friday is excluded (Gulf weekend).

### Test 2 — Edge case: Feb 29, 2000 → Hijri + DC/London/Riyadh overlap

**Hijri result:** 26 Dhul Qa'dah 1420 AH (tabular, Thursday epoch)
- Feb 29, 2000 is valid (2000 is a Gregorian leap year) ✓
- 1420 AH is not a Hijri leap year (1420 % 30 = 20, not in leap set) ✓
- Caveat shown: may differ ±1–2 days from Umm al-Qura ✓

**Meeting overlap:** Zero minutes — no feasible overlap exists.
- London (GMT, Feb 2000): 09:00–18:00 UTC
- DC (EST, Feb 2000): 14:00–23:00 UTC (EDT hasn't started yet in February)
- Riyadh (AST, UTC+3): 06:00–14:00 UTC

The overlap window would be max(14:00, 09:00, 06:00)=14:00 to min(23:00, 18:00, 14:00)=14:00 — the same instant, zero duration. This is a genuine three-city scheduling impossibility that the script correctly identifies and explains.

### Test 3 — Cautious/decline: Ramadan daily at 2pm Riyadh for a month

**Input:** `--mode ramadan-advisory --cities "Riyadh,Washington DC" --start 2026-03-01 --end 2026-03-29 --meeting-hour 14`

The skill does **not silently schedule**. Instead it:
1. Identifies the Ramadan window (~Mar 1–29, 2026)
2. Explains that 14:00 Riyadh during Ramadan is past the shortened workday end (14:00 is the last minute of work hours) and coincides with peak fasting fatigue
3. Flags prayer-time conflicts
4. Proposes two concrete alternatives with UTC times and DC equivalents
5. Asks for confirmation before generating any schedule
6. Provides a `--force-schedule` override flag if the user confirms

---

## What worked well

- **The tabular algorithm is genuinely correct.** By tracing through the 30-year
  cycle step by step, the script produces consistent results that differ from the
  Umm al-Qura calendar by only 1–2 days — which is the expected, documented
  difference, not an error.
- **`zoneinfo` handles DST automatically.** The Feb 2000 test case correctly
  applies EST (UTC-5) rather than EDT because February is before daylight saving
  starts. No manual DST table needed.
- **The three-city zero-overlap case is a good illustration.** DC+London+Riyadh
  have literally zero shared working minutes in winter (Feb 2000), which many
  people don't realize until they try to book a meeting and fail. The skill
  diagnoses the exact cause.
- **Gulf weekend exclusion works correctly.** Thursday is included as a Gulf
  business day (often missed by Western tools), and Friday is excluded.
- **Cultural awareness is built in, not bolted on.** The Ramadan advisory is part
  of the skill's instructions, not an afterthought. The agent declines the
  problematic schedule by default and explains why.

---

## Limitations

### Hijri calendar
- **Tabular ≠ observed.** The script gives the tabular approximation (±1–2 days
  from Umm al-Qura, ±1–3 days from observed moon sighting). For official Saudi
  Islamic dates, always consult the official announcement.
- **Umm al-Qura not implemented.** The official Saudi calendar uses
  astronomical moonrise calculations requiring an ephemeris library (e.g.,
  `ephem` or `astropy`). The tabular algorithm was chosen because it has no
  external dependencies and is deterministic.
- **No reverse (Hijri → Gregorian) conversion** in the current version.
  The inverse function is straightforward to add but was not required for this assignment.

### Meeting finder
- **UAE ambiguity.** Since the 2022 UAE workweek reform, different UAE companies
  follow different schedules. The script defaults to Mon–Fri (new standard) with
  a note; it cannot know the specific company's policy.
- **Holiday exclusions are approximate.** The script detects Ramadan windows
  from a hardcoded table but does not implement a full Saudi/UAE holiday
  exclusion. The `references/gulf-holidays.md` file documents the holidays; a
  future version could parse this into the meeting finder.
- **No half-hour timezone handling** for cities like India (+5:30), Iran (+3:30),
  or Nepal (+5:45). The city lookup table covers major hubs; uncommon cities
  require the user to pass a raw IANA timezone name.
- **Ramadan dates are approximate ±1 day.** The script hardcodes tabular
  Ramadan windows. The true start depends on moon sighting; a false positive
  (applying Ramadan hours one day early/late) is possible.

---

## File structure

```
hw5-rawan/
├── .agents/
│   └── skills/
│       └── datetime-converter/
│           ├── SKILL.md                  ← Agent instructions, Gulf rules, Hijri caveat
│           ├── scripts/
│           │   └── datetime_convert.py  ← Tabular algorithm + meeting finder
│           └── references/
│               ├── hijri-algorithm.md   ← Full algorithm documentation + worked example
│               └── gulf-holidays.md     ← Saudi/UAE holidays, Ramadan hours, weekend rules
└── README.md                            ← This file
```
