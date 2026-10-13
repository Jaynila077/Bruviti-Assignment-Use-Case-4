# DATA.md

This document explains what I found while exploring the `data/` folder, why each thing matters for the metrics in the brief, and how the code handles it. The underlying checks are in `data/eda_data.ipynb` (done with AI-assisted EDA, I directed the checks and verified every output against the real CSVs before relying on it).


## 1. Not everyone in `seats.csv` / `activity_events.csv` is a real employee

`people.csv` is the authoritative list of who counts, current Helix Labs staff. But `seats.csv` and `activity_events.csv` come from the tool vendors' own systems, which have no idea who's still employed. In this sample, `activity_events.csv` had a handful of `user_id`s that don't appear in `people.csv` at all (looked like leftover test accounts).

**Handling:** scope is built from `people.csv` first. Every seat row and every event row is checked against that scope, and anything referencing a `user_id` outside it is silently dropped before any metric is computed, not treated as an error, just excluded.

## 2. Usage logged for a tool the person never held a seat for

`activity_events.csv` can say someone used a tool on a given day even though `seats.csv` shows they never had a seat for it. In this sample there were well over a hundred such `(user_id, tool)` pairs. The brief is explicit that usage only counts as "engagement" if the person held a paid seat for that tool on that exact day, so this isn't an error case, it's just noise to filter out.

**Handling:** an event only counts if the user held an active seat for that specific tool on that specific date. If no seat ever existed for that pair, it's excluded — no special-case code needed, this falls straight out of the seat-holding check everything else already does.

## 3. Price is keyed on (tool, tier), not tool alone

`price_list.csv` isn't one row per tool, some tools have multiple rows, one per tier, at different prices (e.g. a `standard` tier and a `pro`/`enterprise` tier for the same tool, priced differently). A lookup keyed on tool name alone would be ambiguous or just wrong.

**Handling:** every price lookup uses the `(tool, tier)` pair together, never tool by itself.

## 4. One tool has no listed price

One tool's row in `price_list.csv` has a blank `monthly_price_usd`, presumably still unpriced on the vendor side. Treating that blank as `$0` would be actively misleading (it implies "free," not "unknown"), and crashing on it isn't acceptable either.

**Handling:** an unpriced tool is treated as a distinct state. For that tool, `spend`, `idle_spend`, and `cost_per_active` are reported as `null`, not `0`. Its seats are also excluded from any company-wide spend total, so they don't quietly contribute zero and skew an average.

## 5. A blank `revoked_on` means "still held," not "missing data"

The majority of rows in `seats.csv` have a blank `revoked_on`, far too many to be a data-entry gap. The brief's semantics make this clear: no revoke date means the seat is still active today, with no end date yet.

**Handling:** on load, a blank `revoked_on` is treated as "no end date" (open-ended), not an error and not excluded. Any day on or after `granted_on` counts as held, with nothing capping it.

## 6. The same person can have more than one seat row for the same tool

The brief describes "at most one seat per (user, tool)" as the normal case, but nothing in the file format enforces that, it's a description of this sample, not a guarantee about the grading data. In this sample no (user, tool) pair had duplicate rows, but the logic can't assume that holds for the swapped folder.

**Handling:** seat rows are never treated as independent per-row facts. All rows for the same `(user_id, tool)` are merged into one combined set of held days before anything is counted, so two overlapping or back-to-back rows for the same pair are collapsed into one day-range, not double-counted.

## 7. Spend has to be computed off the same merged day-set as everything else

This is the one actual bug caught during review: licensed/active user counts were already using the merged, deduplicated day-set from #6, but spend was still being computed row-by-row, adding up each row's days independently. If two rows for the same (user, tool) ever overlapped, the user counts would correctly avoid double-counting while spend would still double-bill for the overlapping days, an internal inconsistency between two numbers that are supposed to describe the same reality.

**Handling:** spend is now computed off the exact same merged day-set used for licensed/active users, so the two can never disagree. That leaves one judgment call the brief doesn't define: if two overlapping rows for the same pair have different prices (e.g. a tier change), which price applies to the shared days? I chose to charge the higher of the two for those days, a conservative, revenue-leaning assumption, documented here rather than left implicit in the code.

## 8. The CSVs are CRLF-terminated

All five files use Windows-style `\r\n` line endings. This is invisible if you use a real CSV parser, but a naive `line.split(',')` approach would leave a stray `\r` stuck to the last column of each row. That's dangerous here specifically because the last column in `seats.csv` is `revoked_on` — a genuinely blank value would no longer look blank, which would break the "blank means still active" rule in #5 (and similarly risks masking the blank price in #4).

**Handling:** nothing hand-parses CSV text. Loading goes through `csv.DictReader` / pandas, which handle line-ending differences correctly, so this never becomes a live bug.

---

**How these were found:** by direct inspection of the CSVs (null counts, group-bys, set differences between files, raw byte inspection for line endings), not by guessing from the brief alone, see `notebooks/eda_data.ipynb` for the checks and their actual output against this sample.