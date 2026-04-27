"""
Data loading and preprocessing for the Bear 100 dashboard.

Produces two normalized pandas DataFrames from the CSV files in the repo root:

- runners:  one row per entrant per year
- splits:   one row per entrant per aid station (long-form)

Times are parsed into integer seconds. Missing / malformed values become None.
Run this module directly to execute validation and print summary statistics.
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Year → group mapping (from scrape_validation_report.md)
# ---------------------------------------------------------------------------

GROUP_BY_YEAR: dict[int, str] = {
    **{y: "Group 1" for y in list(range(1999, 2008)) + [2011, 2012]},
    **{y: "Group 2" for y in [2008, 2009, 2010, 2013, 2014, 2015, 2017, 2018, 2019, 2020, 2021]},
    2016: "2016",
    **{y: "Group 3" for y in [2022, 2023, 2024, 2025]},
}

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

_TIME_RE = re.compile(r"^(\d{1,3}):(\d{2})(?::(\d{2}))?$")
_STATION_RE = re.compile(r"^(.+?)\s+In / Out\s+\(Mile (\d+\.?\d*)\)$")
_FINISH_RE = re.compile(r"^Finish\s+\(Mile (\d+\.?\d*)\)$")
_MISSING_TIME_TOKENS = frozenset({"", "--:--", "--:--:--", "-"})


def parse_time_to_seconds(value: str | None) -> int | None:
    """Parse 'HH:MM' or 'HH:MM:SS' into total seconds. Return None if missing/malformed."""
    if value is None:
        return None
    value = value.strip()
    if value in _MISSING_TIME_TOKENS:
        return None
    m = _TIME_RE.match(value)
    if not m:
        return None
    h = int(m.group(1))
    mm = int(m.group(2))
    ss = int(m.group(3) or 0)
    return h * 3600 + mm * 60 + ss


def parse_category(cat: str | None) -> tuple[str | None, int | None]:
    """Parse 'Male, 45' or 'Male' → (gender, age). Unknown shapes yield (None, None)."""
    if not cat:
        return (None, None)
    cat = cat.strip()
    if "," in cat:
        left, right = [p.strip() for p in cat.split(",", 1)]
        gender = left if left in {"Male", "Female"} else None
        age = int(right) if right.isdigit() else None
        return (gender, age)
    if cat in {"Male", "Female"}:
        return (cat, None)
    return (None, None)


def parse_station_header(header: str) -> tuple[str, float] | None:
    """Parse '<Name> In / Out (Mile X)' or 'Finish (Mile X)' → (name, mile). Else None."""
    m = _STATION_RE.match(header)
    if m:
        return (m.group(1).strip(), float(m.group(2)))
    m = _FINISH_RE.match(header)
    if m:
        return ("Finish", float(m.group(1)))
    return None


def parse_og_place(og: str | None, status: str) -> tuple[int | None, int | None]:
    """Only populate overall/gender place for Finished runners; DNF ranks on opensplittime are
    distance-based, not finishing-based, and would be misleading if treated as places."""
    if status != "Finished":
        return (None, None)
    if not og or "/" not in og:
        return (None, None)
    left, right = [p.strip() for p in og.split("/", 1)]
    try:
        return (int(left), int(right))
    except ValueError:
        return (None, None)


def parse_split_cell(cell: str) -> tuple[int | None, int | None, bool]:
    """Parse an aid-station 'HH:MM / HH:MM' cell. Returns (in_seconds, out_seconds, is_valid).
    is_valid == True only when BOTH halves parse to real times."""
    if "/" not in cell:
        return (None, None, False)
    left, right = [p.strip() for p in cell.split("/", 1)]
    in_sec = parse_time_to_seconds(left)
    out_sec = parse_time_to_seconds(right)
    valid = in_sec is not None and out_sec is not None
    return (in_sec, out_sec, valid)


# ---------------------------------------------------------------------------
# Per-year CSV loader
# ---------------------------------------------------------------------------


def load_year_csv(year: int, csv_path: Path) -> tuple[list[dict], list[dict]]:
    """Load one CSV. Returns (runners_rows, splits_rows) as lists of dicts."""
    runners_rows: list[dict] = []
    splits_rows: list[dict] = []

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Collect station columns in header order (which matches race order by mile).
        station_cols: list[tuple[str, str, float]] = []  # (raw_header, name, mile)
        for h in headers:
            parsed = parse_station_header(h)
            if parsed is not None:
                station_cols.append((h, parsed[0], parsed[1]))

        for runner_idx, row in enumerate(reader):
            status = row.get("Status", "").strip()
            gender, age = parse_category(row.get("Category"))
            overall_place, gender_place = parse_og_place(row.get("O/G Place"), status)

            # Find the Finish column; its value is a single time (not "in / out")
            finish_seconds: int | None = None
            for raw_h, name, _mile in station_cols:
                if name == "Finish":
                    finish_seconds = parse_time_to_seconds(row.get(raw_h, ""))
                    break

            runners_rows.append(
                {
                    "year": year,
                    "group": GROUP_BY_YEAR.get(year, "Unknown"),
                    "runner_idx": runner_idx,
                    "bib": (row.get("Bib") or "").strip() or None,
                    "name": (row.get("Name") or "").strip(),
                    "gender": gender,
                    "age": age,
                    "from_location": (row.get("From") or "").strip() or None,
                    "status": status,
                    "overall_place": overall_place,
                    "gender_place": gender_place,
                    "finish_seconds": finish_seconds,
                }
            )

            # Emit one splits row per station column
            for station_order, (raw_h, name, mile) in enumerate(station_cols, start=1):
                cell = (row.get(raw_h) or "").strip()
                if name == "Finish":
                    t = parse_time_to_seconds(cell)
                    in_sec, out_sec = t, t
                    valid = t is not None
                    duration: int | None = 0 if valid else None
                else:
                    in_sec, out_sec, valid = parse_split_cell(cell)
                    # Compute duration only if valid AND non-negative. Negative durations exist
                    # in the source data (out-time before in-time) — ~0.2% of splits. Treat
                    # those as "runner reached station, but duration is unreliable".
                    if valid and out_sec is not None and in_sec is not None:
                        raw_duration = out_sec - in_sec
                        duration = raw_duration if raw_duration >= 0 else None
                    else:
                        duration = None

                splits_rows.append(
                    {
                        "year": year,
                        "runner_idx": runner_idx,
                        "station_name": name,
                        "station_mile": mile,
                        "station_order": station_order,
                        "in_seconds": in_sec,
                        "out_seconds": out_sec,
                        "aid_duration_seconds": duration,
                        "is_valid_split": valid,
                    }
                )

    return runners_rows, splits_rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _clean_phantom_out_times(splits_df: pd.DataFrame) -> pd.DataFrame:
    """Null out aid_duration_seconds when a station's out-time equals the next station's
    in-time for the same runner. This is a systematic opensplittime ingestion pattern
    (seen prominently in 2020 Richards Hollow): when an out-time isn't captured at a
    station, the system appears to backfill it from the next station's in-time,
    producing physically-impossible "durations" that span the inter-station travel.
    The runner did reach the station (is_valid_split stays True), but the duration
    math is unusable, so we null it."""
    df = splits_df.sort_values(["year", "runner_idx", "station_order"]).reset_index(drop=True)
    # Compute next station's in_seconds within each (year, runner) group
    df["next_in_seconds"] = df.groupby(["year", "runner_idx"])["in_seconds"].shift(-1)

    phantom_mask = (
        df["is_valid_split"]
        & (df["station_name"] != "Finish")
        & df["aid_duration_seconds"].notna()
        & df["out_seconds"].notna()
        & df["next_in_seconds"].notna()
        & (df["out_seconds"] == df["next_in_seconds"])
        # Only flag when the out-time is NOT the in-time (i.e., a real gap that matches next station).
        # A zero-duration pass-through (in==out) where the next in also matches is legitimately a
        # fast runner who didn't stop — don't null those.
        & (df["in_seconds"] != df["out_seconds"])
    )
    df.loc[phantom_mask, "aid_duration_seconds"] = None
    df = df.drop(columns=["next_in_seconds"])
    return df


@lru_cache(maxsize=1)
def load_all() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load all years. Returns (runners_df, splits_df). Cached for app reuse."""
    all_runners: list[dict] = []
    all_splits: list[dict] = []

    csv_paths = sorted(REPO_ROOT.glob("[12][0-9][0-9][0-9].csv"))
    for csv_path in csv_paths:
        year = int(csv_path.stem)
        runners, splits = load_year_csv(year, csv_path)
        all_runners.extend(runners)
        all_splits.extend(splits)

    runners_df = pd.DataFrame(all_runners)
    splits_df = pd.DataFrame(all_splits)

    # Post-load cleaning: null phantom aid durations caused by upstream ingestion quirks.
    splits_df = _clean_phantom_out_times(splits_df)

    # Derived column: starter count is used so often we may as well attach it
    runners_df["is_starter"] = runners_df["status"] != "Not Started"

    return runners_df, splits_df


# ---------------------------------------------------------------------------
# Validation (runs when invoked as `python data.py`)
# ---------------------------------------------------------------------------


def _validate() -> None:
    """Self-check the loader against known truths from the scrape validation report."""
    import sys

    # Expected row counts from scrape_validation_report.md
    EXPECTED_TOTAL_ROWS = {
        1999: 14, 2000: 9, 2001: 17, 2002: 32, 2003: 42, 2004: 41, 2005: 36, 2006: 36,
        2007: 62, 2008: 74, 2009: 132, 2010: 164, 2011: 268, 2012: 258, 2013: 263,
        2014: 278, 2015: 309, 2016: 332, 2017: 338, 2018: 317, 2019: 306, 2020: 305,
        2021: 306, 2022: 346, 2023: 363, 2024: 350, 2025: 335,
    }

    runners, splits = load_all()
    problems: list[str] = []

    # --- Row counts per year match expectations ---
    for year, expected in EXPECTED_TOTAL_ROWS.items():
        actual = (runners["year"] == year).sum()
        if actual != expected:
            problems.append(f"Year {year}: expected {expected} runners, got {actual}")

    # --- Every runner has a gender (core field) ---
    null_gender = runners["gender"].isna().sum()
    if null_gender > 0:
        sample = runners[runners["gender"].isna()][["year", "name"]].head(5).to_dict("records")
        problems.append(f"{null_gender} runners have null gender. Sample: {sample}")

    # --- Status values are exactly the 4 expected ---
    statuses = set(runners["status"].unique())
    expected_statuses = {"Finished", "Dropped", "Not Started", "In Progress"}
    unexpected = statuses - expected_statuses
    if unexpected:
        problems.append(f"Unexpected status values: {unexpected}")

    # --- Every Finished runner has finish_seconds AND overall_place AND gender_place ---
    finished = runners[runners["status"] == "Finished"]
    missing_finish = finished["finish_seconds"].isna().sum()
    if missing_finish > 0:
        problems.append(f"{missing_finish} Finished runners have null finish_seconds")
    missing_overall = finished["overall_place"].isna().sum()
    if missing_overall > 0:
        problems.append(f"{missing_overall} Finished runners have null overall_place")
    missing_gplace = finished["gender_place"].isna().sum()
    if missing_gplace > 0:
        problems.append(f"{missing_gplace} Finished runners have null gender_place")

    # --- No non-Finished runner has finish_seconds ---
    non_fin = runners[runners["status"] != "Finished"]
    has_finish = non_fin["finish_seconds"].notna().sum()
    if has_finish > 0:
        problems.append(f"{has_finish} non-Finished runners have non-null finish_seconds (bug)")

    # --- Finish time sanity: 10h to 40h for Bear 100 ---
    if finished["finish_seconds"].min() < 10 * 3600:
        fast = finished[finished["finish_seconds"] < 10 * 3600][["year", "name", "finish_seconds"]].head(3)
        problems.append(f"Finish time < 10 hours found (suspicious): {fast.to_dict('records')}")
    if finished["finish_seconds"].max() > 40 * 3600:
        slow = finished[finished["finish_seconds"] > 40 * 3600][["year", "name", "finish_seconds"]].head(3)
        problems.append(f"Finish time > 40 hours found (suspicious): {slow.to_dict('records')}")

    # --- Split integrity: aid_duration_seconds is never negative (nulled if raw was negative) ---
    valid_splits = splits[splits["is_valid_split"] & (splits["station_name"] != "Finish")]
    populated_durations = valid_splits[valid_splits["aid_duration_seconds"].notna()]
    bad_duration = (populated_durations["aid_duration_seconds"] < 0).sum()
    if bad_duration > 0:
        problems.append(f"{bad_duration} valid non-Finish splits have negative aid_duration_seconds (should have been nulled)")

    # --- Informational: how many splits had out-time < in-time in the source ---
    null_dur_from_bad = valid_splits["aid_duration_seconds"].isna().sum()
    if null_dur_from_bad > 0:
        # Not a failure — report for transparency.
        print(f"[INFO] {null_dur_from_bad} valid splits had negative raw duration (source data quality); duration nulled.")

    # --- Splits per year: Group 1 has 1 (Finish only); Group 2/2016 have 14; Group 3 has 13 ---
    for year, expected_stations in [
        (1999, 1), (2005, 1), (2011, 1), (2012, 1),  # Group 1 samples
        (2008, 14), (2015, 14), (2020, 14),           # Group 2 samples
        (2016, 14),                                    # 2016
        (2022, 13), (2024, 13), (2025, 13),           # Group 3 samples
    ]:
        year_splits = splits[splits["year"] == year]
        n_runners = (runners["year"] == year).sum()
        expected_total = n_runners * expected_stations
        if len(year_splits) != expected_total:
            problems.append(
                f"Year {year}: expected {expected_total} splits rows ({n_runners} runners × {expected_stations} stations), got {len(year_splits)}"
            )

    # --- Group assignment ---
    unknown_groups = (runners["group"] == "Unknown").sum()
    if unknown_groups > 0:
        problems.append(f"{unknown_groups} runners have group='Unknown'")

    # ---- Summary output ----
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    if problems:
        print(f"\n[FAIL] {len(problems)} problems found:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    else:
        print(f"\n[OK] All checks passed.")

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total runners across all years: {len(runners):,}")
    print(f"Total splits rows:              {len(splits):,}")
    print()
    print("Status counts:")
    for status, count in runners["status"].value_counts().items():
        print(f"  {status:15s} {count:,}")
    print()
    print("Group counts:")
    for group, count in runners["group"].value_counts().sort_index().items():
        n_years = runners[runners["group"] == group]["year"].nunique()
        print(f"  {group:10s} {count:,} runners across {n_years} years")
    print()
    print("Gender split (overall):")
    for gender, count in runners["gender"].value_counts(dropna=False).items():
        pct = 100 * count / len(runners)
        print(f"  {str(gender):10s} {count:,} ({pct:.1f}%)")
    print()
    print("Finish time stats (Finished runners only):")
    fin = runners[runners["status"] == "Finished"]["finish_seconds"]
    fastest, slowest, median = int(fin.min()), int(fin.max()), int(fin.median())
    print(f"  fastest:  {fastest // 3600}h{(fastest % 3600) // 60:02d}m")
    print(f"  slowest:  {slowest // 3600}h{(slowest % 3600) // 60:02d}m")
    print(f"  median:   {median // 3600}h{(median % 3600) // 60:02d}m")
    print()
    print("Split validity rate (non-Finish splits):")
    non_finish_splits = splits[splits["station_name"] != "Finish"]
    valid = non_finish_splits["is_valid_split"].sum()
    total = len(non_finish_splits)
    print(f"  {valid:,} / {total:,} valid  ({100 * valid / total:.1f}%)")
    print()
    print("Sample runners (first 3):")
    print(runners.head(3).to_string(index=False))
    print()
    print("Sample splits (2024 winner, first 5 stations):")
    first_2024 = runners[runners["year"] == 2024].iloc[0]
    winner_splits = splits[(splits["year"] == 2024) & (splits["runner_idx"] == first_2024["runner_idx"])].head(5)
    print(winner_splits.to_string(index=False))


if __name__ == "__main__":
    _validate()
