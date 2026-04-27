"""
Analytical metric functions for the Bear 100 dashboard.

Every function takes the already-loaded (runners, splits) DataFrames from data.py
plus optional filters, and returns a tidy DataFrame ready for chart rendering.

Gender filter semantics:
    gender=None      -> Overall (all runners)
    gender="Male"    -> Male only
    gender="Female"  -> Female only

Run this module directly to execute spot-checks against the raw data.
"""

from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _filter_gender(df: pd.DataFrame, gender: str | None) -> pd.DataFrame:
    """Filter a runners (or splits-joined-with-runners) df by gender, or pass through."""
    if gender is None:
        return df
    if gender not in {"Male", "Female"}:
        raise ValueError(f"gender must be 'Male', 'Female', or None; got {gender!r}")
    return df[df["gender"] == gender]


# ---------------------------------------------------------------------------
# Hero stats
# ---------------------------------------------------------------------------


def hero_stats(runners: pd.DataFrame, gender: str | None = None) -> dict:
    """Aggregate headline numbers for the top of the Home page.

    Starters = total rows minus 'Not Started' (per user spec).
    DNF rate = Dropped / Starters, but only computed over years that actually record DNFs
    (Group 1 years only recorded finishers, so including them would depress the rate).
    """
    df = _filter_gender(runners, gender)
    n_years = df["year"].nunique()
    n_entrants_raw = len(df)
    n_starters = int((df["status"] != "Not Started").sum())
    n_finishers = int((df["status"] == "Finished").sum())
    n_dnf = int((df["status"] == "Dropped").sum())

    # DNF rate is only meaningful for years that recorded DNFs.
    # Group 1 years (1999-2007, 2011, 2012) only have Finished entries.
    df_with_dnf_data = df[df["group"] != "Group 1"]
    starters_with_dnf_data = int((df_with_dnf_data["status"] != "Not Started").sum())
    dnf_rate = (n_dnf / starters_with_dnf_data) if starters_with_dnf_data > 0 else 0.0

    finish_rate = 1-dnf_rate if n_starters > 0 else 0.0

    return {
        "n_years": int(n_years),
        "n_entrants_raw": n_entrants_raw,
        "n_starters": n_starters,
        "n_finishers": n_finishers,
        "n_dnf": n_dnf,
        "finish_rate": finish_rate,
        "dnf_rate": dnf_rate,
    }


# ---------------------------------------------------------------------------
# Podium per year
# ---------------------------------------------------------------------------


def podium_per_year(runners: pd.DataFrame, year: int, gender: str) -> pd.DataFrame:
    """Top 3 finishers for a given year + gender. Returns (place, name, finish_seconds).
    Ties (same gender_place) are preserved; fewer than 3 is allowed for small-field years."""
    if gender not in {"Male", "Female"}:
        raise ValueError(f"podium requires explicit gender; got {gender!r}")
    df = runners[
        (runners["year"] == year)
        & (runners["gender"] == gender)
        & (runners["status"] == "Finished")
    ].copy()
    df = df.sort_values("finish_seconds").head(3)
    return df[["gender_place", "name", "finish_seconds"]].reset_index(drop=True)


def all_podiums(runners: pd.DataFrame) -> pd.DataFrame:
    """Compact long-form podium table for every year, both genders.
    Columns: year, gender, podium_place (1-3), name, finish_seconds."""
    rows = []
    for year in sorted(runners["year"].unique()):
        for gender in ("Male", "Female"):
            pod = podium_per_year(runners, year, gender)
            for i, r in pod.iterrows():
                rows.append(
                    {
                        "year": year,
                        "gender": gender,
                        "podium_place": i + 1,
                        "name": r["name"],
                        "finish_seconds": r["finish_seconds"],
                    }
                )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Racer history (starters and finishers over time; gender filter applies)
# ---------------------------------------------------------------------------


def racer_history_per_year(runners: pd.DataFrame, gender: str | None = None) -> pd.DataFrame:
    """Starters and finishers per year for the Racer history chart.

    Starters are omitted for Group 1 years (1999-2007, 2011, 2012) because
    those years only recorded finishers, making starters == finishers there.
    This produces a natural gap in the starters line for 2011-2012.
    Columns: year, count, metric ('Starters' | 'Finishers').
    """
    df = _filter_gender(runners, gender)

    finishers = (
        df[df["status"] == "Finished"]
        .groupby("year")
        .size()
        .reset_index(name="count")
    )
    finishers["metric"] = "Finishers"

    starters = (
        df[(df["status"] != "Not Started") & (df["group"] != "Group 1")]
        .groupby("year")
        .size()
        .reset_index(name="count")
    )
    starters["metric"] = "Starters"

    # Insert NaN sentinels for 2011 and 2012 so Plotly renders a hard break
    # rather than connecting 2010 to 2013 across the gap.
    gap_rows = pd.DataFrame({"year": [2011, 2012], "count": [float("nan"), float("nan")], "metric": "Starters"})
    starters = pd.concat([starters, gap_rows], ignore_index=True)

    out = pd.concat([finishers, starters], ignore_index=True)
    return out.sort_values(["metric", "year"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# DNF rate per year
# ---------------------------------------------------------------------------


def dnf_rate_per_year(runners: pd.DataFrame, gender: str | None = None) -> pd.DataFrame:
    """DNF rate per year. For Group 1 years (no DNF recording), returns NaN rather than 0.
    Columns: year, group, starters, dnf, dnf_rate (float 0..1 or NaN)."""
    df = _filter_gender(runners, gender)
    starters = df[df["status"] != "Not Started"]
    dnfs = df[df["status"] == "Dropped"]

    s_counts = starters.groupby("year").size().rename("starters")
    d_counts = dnfs.groupby("year").size().rename("dnf")
    group_map = df.drop_duplicates("year").set_index("year")["group"]

    out = pd.concat([s_counts, d_counts, group_map], axis=1).reset_index()
    out["dnf"] = out["dnf"].fillna(0).astype(int)
    out["starters"] = out["starters"].fillna(0).astype(int)
    out["dnf_rate"] = out["dnf"] / out["starters"].replace(0, pd.NA)

    # Group 1 years didn't record DNFs — flag NaN rather than report 0%
    group1_mask = out["group"] == "Group 1"
    out.loc[group1_mask, "dnf_rate"] = pd.NA
    out.loc[group1_mask, "dnf"] = pd.NA  # we don't actually know DNF count

    return out.sort_values("year").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Top N finish time analyses
# ---------------------------------------------------------------------------


def top_n_per_year(
    runners: pd.DataFrame, n: int = 5, gender: str | None = None
) -> pd.DataFrame:
    """For each (year, gender) combo, top N finish times.
    Columns: year, group, gender, rank (1..n), finish_seconds, name."""
    df = runners[runners["status"] == "Finished"].copy()
    df = _filter_gender(df, gender)

    rows = []
    genders = [gender] if gender else ["Male", "Female"]
    for year in sorted(df["year"].unique()):
        for g in genders:
            sub = df[(df["year"] == year) & (df["gender"] == g)].sort_values("finish_seconds").head(n)
            if sub.empty:
                continue
            group = sub.iloc[0]["group"]
            for rank, (_, r) in enumerate(sub.iterrows(), start=1):
                rows.append(
                    {
                        "year": year,
                        "group": group,
                        "gender": g,
                        "rank": rank,
                        "finish_seconds": r["finish_seconds"],
                        "name": r["name"],
                    }
                )
    return pd.DataFrame(rows)


def top_n_average_per_year(
    runners: pd.DataFrame, n: int = 5, gender: str | None = None
) -> pd.DataFrame:
    """Average of top N finish times per (year, gender). Years with < n finishers of that
    gender are skipped (not averaged on partial data).
    Columns: year, group, gender, avg_top_n_seconds, n_finishers_in_year."""
    df = runners[runners["status"] == "Finished"].copy()
    df = _filter_gender(df, gender)

    rows = []
    genders = [gender] if gender else ["Male", "Female"]
    for year in sorted(df["year"].unique()):
        for g in genders:
            sub = df[(df["year"] == year) & (df["gender"] == g)]
            n_finishers = len(sub)
            if n_finishers < n:
                continue
            top = sub.nsmallest(n, "finish_seconds")
            rows.append(
                {
                    "year": year,
                    "group": top.iloc[0]["group"],
                    "gender": g,
                    "avg_top_n_seconds": top["finish_seconds"].mean(),
                    "n_finishers_in_year": n_finishers,
                }
            )
    return pd.DataFrame(rows)


def top_n_average_per_group(
    runners: pd.DataFrame, n: int = 5, gender: str | None = None
) -> pd.DataFrame:
    """Per (group, gender), the average of the top N finish times across the ENTIRE group's
    years. This is the "elite depth per era" summary.
    Columns: group, gender, avg_top_n_seconds, n_finishers_in_group."""
    df = runners[runners["status"] == "Finished"].copy()
    df = _filter_gender(df, gender)

    rows = []
    genders = [gender] if gender else ["Male", "Female"]
    for group in sorted(df["group"].unique()):
        for g in genders:
            sub = df[(df["group"] == group) & (df["gender"] == g)]
            n_fin = len(sub)
            if n_fin < n:
                continue
            top = sub.nsmallest(n, "finish_seconds")
            rows.append(
                {
                    "group": group,
                    "gender": g,
                    "avg_top_n_seconds": top["finish_seconds"].mean(),
                    "n_finishers_in_group": n_fin,
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Overall yearly averages (all finishers, not just top N)
# ---------------------------------------------------------------------------


def overall_finish_average_per_year(
    runners: pd.DataFrame, gender: str | None = None
) -> pd.DataFrame:
    """Average finish time across all finishers for each (year, gender).
    Columns: year, group, gender, avg_finish_seconds, n_finishers."""
    df = runners[runners["status"] == "Finished"].copy()
    df = _filter_gender(df, gender)

    grouped = (
        df.groupby(["year", "group", "gender"], dropna=False)
        .agg(avg_finish_seconds=("finish_seconds", "mean"), n_finishers=("finish_seconds", "size"))
        .reset_index()
    )
    return grouped.sort_values(["year", "gender"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Quintile assignment (per year, per gender)
# ---------------------------------------------------------------------------


def assign_finisher_quintiles(runners: pd.DataFrame) -> pd.DataFrame:
    """Assign a quintile (1=fastest 20%, 5=slowest 20%) to each finisher, computed within
    each (year, gender) group. Quintile boundaries use pandas qcut with 5 bins.
    Returns a DataFrame with an added 'quintile' column (int 1-5). Non-finishers get NaN."""
    df = runners.copy()
    df["quintile"] = pd.NA

    for (year, gender), grp in df[df["status"] == "Finished"].groupby(["year", "gender"]):
        if len(grp) < 5:
            # Can't form quintiles with fewer than 5 — skip, leave NaN
            continue
        # Rank first so that finish-time ties don't produce duplicate qcut bin edges.
        # method='first' breaks ties deterministically by row order within the group
        # (which is already sorted by place on opensplittime, so the higher-placed
        # runner of a tied pair gets the better quintile).
        ranks = grp["finish_seconds"].rank(method="first")
        labels = pd.qcut(ranks, q=5, labels=[1, 2, 3, 4, 5])
        df.loc[grp.index, "quintile"] = labels.astype(int)

    return df


# ---------------------------------------------------------------------------
# Aid station analyses
# ---------------------------------------------------------------------------


def aid_time_per_quintile_per_station(
    runners: pd.DataFrame, splits: pd.DataFrame, gender: str | None = None
) -> pd.DataFrame:
    """Average aid station duration per (group, quintile, station). This is the data for
    'how long does each quintile spend at each station, across the race'.
    Columns: group, quintile, station_name, station_mile, station_order,
             avg_duration_seconds, n_valid_splits."""
    runners_q = assign_finisher_quintiles(runners)
    runners_q = _filter_gender(runners_q, gender)
    runners_q = runners_q[runners_q["quintile"].notna()]

    # Join splits with runner info (gender, quintile, group). Exclude the Finish row —
    # aid-station analysis is about non-finish stations.
    split_data = splits.merge(
        runners_q[["year", "runner_idx", "group", "gender", "quintile"]],
        on=["year", "runner_idx"],
        how="inner",
    )
    valid = split_data[
        (split_data["station_name"] != "Finish")
        & (split_data["aid_duration_seconds"].notna())
    ]

    grouped = (
        valid.groupby(["group", "quintile", "station_name", "station_mile", "station_order"])
        .agg(
            avg_duration_seconds=("aid_duration_seconds", "mean"),
            n_valid_splits=("aid_duration_seconds", "size"),
        )
        .reset_index()
    )
    return grouped.sort_values(["group", "quintile", "station_mile"]).reset_index(drop=True)


def total_aid_time_per_quintile(
    runners: pd.DataFrame, splits: pd.DataFrame, gender: str | None = None
) -> pd.DataFrame:
    """Average TOTAL time spent in aid stations per (group, quintile).

    Quintiles are assigned only among finishers who have a valid duration at every
    non-Finish station in their year. This prevents selection bias: if we assigned
    quintiles from all finishers first and then dropped incomplete ones, slower runners
    (Q5) — who are more likely to have missing splits — would be underrepresented,
    making Q5 look artificially fast.

    The per-station chart (aid_time_per_quintile_per_station) uses a separate quintile
    assignment that includes all finishers, so individual valid splits are not wasted.

    Columns: group, quintile, avg_total_aid_seconds, n_runners, stations_in_group.
    """
    non_finish_splits = splits[splits["station_name"] != "Finish"]

    # Count expected stations per year
    year_station_count = (
        non_finish_splits.groupby("year")["station_name"]
        .nunique()
        .to_dict()
    )

    # Identify runners with a valid duration at every station in their year
    per_runner_valid = (
        non_finish_splits.groupby(["year", "runner_idx"])
        .agg(valid_count=("aid_duration_seconds", lambda x: x.notna().sum()))
        .reset_index()
    )
    per_runner_valid["expected"] = per_runner_valid["year"].map(year_station_count)
    complete_idx = per_runner_valid[
        per_runner_valid["valid_count"] == per_runner_valid["expected"]
    ][["year", "runner_idx"]]

    # Assign quintiles only among finishers who have complete split data
    runners_complete = runners.merge(complete_idx, on=["year", "runner_idx"], how="inner")
    runners_q = assign_finisher_quintiles(runners_complete)
    runners_q = _filter_gender(runners_q, gender)
    runners_q = runners_q[runners_q["quintile"].notna()]

    # Sum aid time per runner — all splits are valid for these runners
    per_runner = (
        non_finish_splits.merge(
            runners_q[["year", "runner_idx", "group", "gender", "quintile"]],
            on=["year", "runner_idx"],
            how="inner",
        )
        .groupby(["year", "runner_idx", "group", "gender", "quintile"])
        .agg(total_aid_seconds=("aid_duration_seconds", "sum"))
        .reset_index()
    )

    result = (
        per_runner.groupby(["group", "quintile"])
        .agg(
            avg_total_aid_seconds=("total_aid_seconds", "mean"),
            n_runners=("total_aid_seconds", "size"),
        )
        .reset_index()
    )

    group_stations = {
        group: non_finish_splits[
            non_finish_splits["year"].isin(per_runner[per_runner["group"] == group]["year"].unique())
        ]["station_name"].nunique()
        for group in result["group"].unique()
    }
    result["stations_in_group"] = result["group"].map(group_stations)

    return result.sort_values(["group", "quintile"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _spot_check() -> None:
    """Run each function, print outputs, and do targeted sanity checks."""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from data import load_all  # type: ignore

    runners, splits = load_all()

    print("=" * 60)
    print("HERO STATS (Overall)")
    print("=" * 60)
    stats = hero_stats(runners)
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.3f}")
        else:
            print(f"  {k}: {v:,}")

    print()
    print("=" * 60)
    print("PODIUM SAMPLE: 2024 Men")
    print("=" * 60)
    print(podium_per_year(runners, 2024, "Male").to_string(index=False))

    print()
    print("=" * 60)
    print("RACER HISTORY PER YEAR (first and last 6 rows)")
    print("=" * 60)
    spy = racer_history_per_year(runners)
    print(pd.concat([spy.head(6), spy.tail(6)]).to_string(index=False))

    print()
    print("=" * 60)
    print("DNF RATE PER YEAR (Overall, showing first 6 / last 6)")
    print("=" * 60)
    dnf = dnf_rate_per_year(runners)
    print(pd.concat([dnf.head(6), dnf.tail(6)]).to_string(index=False))

    print()
    print("=" * 60)
    print("TOP 5 AVG FINISH TIMES PER GROUP (both genders)")
    print("=" * 60)
    t5g = top_n_average_per_group(runners, n=5)
    t5g["avg_top_n_hms"] = t5g["avg_top_n_seconds"].apply(
        lambda s: f"{int(s // 3600)}h{int((s % 3600) // 60):02d}m"
    )
    print(t5g.to_string(index=False))

    print()
    print("=" * 60)
    print("TOP 5 AVG PER YEAR (showing Male only, sample)")
    print("=" * 60)
    t5y = top_n_average_per_year(runners, n=5, gender="Male")
    t5y["avg_top_n_hms"] = t5y["avg_top_n_seconds"].apply(
        lambda s: f"{int(s // 3600)}h{int((s % 3600) // 60):02d}m"
    )
    print(pd.concat([t5y.head(4), t5y.tail(4)]).to_string(index=False))

    print()
    print("=" * 60)
    print("OVERALL YEARLY AVG FINISH (first 6, last 6)")
    print("=" * 60)
    oy = overall_finish_average_per_year(runners)
    oy["avg_hms"] = oy["avg_finish_seconds"].apply(
        lambda s: f"{int(s // 3600)}h{int((s % 3600) // 60):02d}m"
    )
    print(pd.concat([oy.head(6), oy.tail(6)]).to_string(index=False))

    print()
    print("=" * 60)
    print("QUINTILE CHECK: 2024 Male finishers distribution across quintiles")
    print("=" * 60)
    rq = assign_finisher_quintiles(runners)
    sub = rq[(rq["year"] == 2024) & (rq["gender"] == "Male") & (rq["status"] == "Finished")]
    print(f"  Total Male 2024 finishers: {len(sub)}")
    print(f"  Quintile distribution: {sub['quintile'].value_counts().sort_index().to_dict()}")
    per_q = sub.groupby("quintile")["finish_seconds"].agg(["min", "max", "mean"]).reset_index()
    per_q["min_hms"] = per_q["min"].apply(lambda s: f"{int(s//3600)}h{int((s%3600)//60):02d}m")
    per_q["max_hms"] = per_q["max"].apply(lambda s: f"{int(s//3600)}h{int((s%3600)//60):02d}m")
    per_q["mean_hms"] = per_q["mean"].apply(lambda s: f"{int(s//3600)}h{int((s%3600)//60):02d}m")
    print(per_q[["quintile", "min_hms", "mean_hms", "max_hms"]].to_string(index=False))

    print()
    print("=" * 60)
    print("AID STATION TIME PER QUINTILE PER STATION (Group 2 sample, Male)")
    print("=" * 60)
    ats = aid_time_per_quintile_per_station(runners, splits, gender="Male")
    g2_sample = ats[ats["group"] == "Group 2"].sort_values(["quintile", "station_mile"])
    # Show only first 3 stations for each quintile to keep compact
    compact = g2_sample.groupby("quintile").head(3)
    compact["avg_hms"] = compact["avg_duration_seconds"].apply(
        lambda s: f"{int(s // 60)}m{int(s % 60):02d}s"
    )
    print(compact[["quintile", "station_name", "station_mile", "avg_hms", "n_valid_splits"]].to_string(index=False))

    print()
    print("=" * 60)
    print("TOTAL AID STATION TIME PER QUINTILE BY GROUP")
    print("=" * 60)
    tot = total_aid_time_per_quintile(runners, splits)
    tot["avg_total_hms"] = tot["avg_total_aid_seconds"].apply(
        lambda s: f"{int(s // 3600)}h{int((s % 3600) // 60):02d}m{int(s % 60):02d}s"
    )
    print(tot.to_string(index=False))

    # Sanity check: Q1 (fastest) should have less total aid time than Q5 (slowest) within same group
    print()
    print("=" * 60)
    print("SANITY CHECK: Q1 total < Q5 total within each group?")
    print("=" * 60)
    for group in tot["group"].unique():
        g = tot[tot["group"] == group]
        q1 = g[g["quintile"] == 1]["avg_total_aid_seconds"].mean() if not g[g["quintile"] == 1].empty else None
        q5 = g[g["quintile"] == 5]["avg_total_aid_seconds"].mean() if not g[g["quintile"] == 5].empty else None
        if q1 is not None and q5 is not None:
            direction = "YES (hypothesis holds)" if q1 < q5 else "NO (surprising)"
            delta = q5 - q1
            print(f"  {group}: Q1={int(q1)}s, Q5={int(q5)}s, delta={int(delta)}s -> {direction}")


if __name__ == "__main__":
    _spot_check()
