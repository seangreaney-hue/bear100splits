"""
Bear 100 Dashboard — Data Notes (entry page).

Documents the scrape, validation, and cleaning decisions that shape every
number on the rest of the dashboard, and provides live EDA over the loaded
data so the figures stay accurate when the source CSVs change.

Run with:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from data import GROUP_BY_YEAR, load_all  # noqa: E402

# ---------------------------------------------------------------------------
# Shared chart styling (mirrors pages/1_Home.py for visual consistency)
# ---------------------------------------------------------------------------

CHART_DEFAULTS = dict(
    template="plotly_dark",
    paper_bgcolor="#1a1f2e",
    plot_bgcolor="#1a1f2e",
    font=dict(family="Inter, system-ui, sans-serif", color="#e8e8e8"),
    margin=dict(l=20, r=20, t=30, b=30),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        orientation="h",
        yanchor="top",
        y=-0.15,
        xanchor="left",
        x=0,
    ),
)

CHART_CONFIG = {"displayModeBar": False}

ACCENT_COLORS = ["#f0a500", "#7eb8f7", "#e05c5c", "#6fce8a", "#b48eff"]

QUALITY_COLORS = {
    "ok": "#6fce8a",
    "incomplete": "#7eb8f7",
    "negative_duration": "#e05c5c",
    "phantom_duplicate": "#f0a500",
}
QUALITY_ORDER = ["ok", "incomplete", "negative_duration", "phantom_duplicate"]

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Bear 100 — Data Notes",
    page_icon="🐻",
    layout="wide",
)

st.title("Data Notes - Bear 100 race results")
st.caption(
    "Methodology, validation, and exploratory data analysis. "
    "The numbers below are computed live from the loaded CSVs."
)

runners, splits = load_all()

# Splits excluding the synthetic Finish row — the denominator for "split quality"
non_finish = splits[splits["station_name"] != "Finish"]

# ---------------------------------------------------------------------------
# 1. Headline numbers
# ---------------------------------------------------------------------------

st.header("At a glance")

n_years = runners["year"].nunique()
n_runners = len(runners)
n_splits = len(splits)
n_non_finish = len(non_finish)
flag_counts = non_finish["quality_flag"].value_counts()
n_invalid = int(flag_counts.drop(labels=["ok"], errors="ignore").sum())
invalid_pct = n_invalid / n_non_finish if n_non_finish else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Years", f"{n_years}")
c2.metric("Runner rows", f"{n_runners:,}")
c3.metric("Splits rows", f"{n_splits:,}")
c4.metric("Non-Finish splits", f"{n_non_finish:,}")
c5.metric("Invalid splits", f"{n_invalid:,}", delta=f"{invalid_pct:.1%} of non-finish", delta_color="off")

# ---------------------------------------------------------------------------
# 2. Scrape provenance
# ---------------------------------------------------------------------------

st.header("Scrape provenance")
st.markdown(
    """
- **Source:** [opensplittime.org/organizations/the-bear-100](https://www.opensplittime.org/organizations/the-bear-100)
- **Scraped:** 2026-04-22
- **Coverage:** 27 consecutive years, 1999–2025, all linked from the parent organization page.
- **2012 quirk:** The 2012 spread URL was non-standard (`/events/the-bear-2012/spread`
  rather than `/events/the-bear-100-2012/spread`) and was extracted directly from
  the HTML href.

**Validation results — all 27 years passed:**

- Row counts matched the entrant counts listed on the parent page (0 mismatches)
- Every row in every file has the same column count as the header row (0 mismatches)
- 15-row spot-checks against the live page passed for every year (0 discrepancies)

See [`scrape_validation_report.md`](scrape_validation_report.md) for the full table
of column counts and per-year row totals.
"""
)

# ---------------------------------------------------------------------------
# 3. Course eras / schemas
# ---------------------------------------------------------------------------

st.header("Course eras and column schemas")
st.markdown(
    "The 27 years split into four schemas. Group 1 has no aid-station splits at all "
    "(only finisher times). 2016 is its own group because of a last-minute reroute. "
    "2022 introduced a permanent course change that consolidated two stations into one."
)

# Build era summary table from the loaded data
era_rows = []
for group, sub in runners.groupby("group"):
    years = sorted(sub["year"].unique())
    n_runners_g = len(sub)
    # Count distinct non-finish stations within this group
    g_splits = non_finish[non_finish["year"].isin(years)]
    n_stations = g_splits["station_name"].nunique() if len(g_splits) else 0
    era_rows.append(
        {
            "Group": group,
            "Years": ", ".join(str(y) for y in years),
            "# years": len(years),
            "# runners": n_runners_g,
            "# aid stations": str(n_stations) if n_stations else "—",
        }
    )
era_df = pd.DataFrame(era_rows)
# Sort so Group 1, Group 2, 2016, Group 3 appear in chronological order
era_df["_sort"] = era_df["Group"].map({"Group 1": 0, "Group 2": 1, "2016": 2, "Group 3": 3})
era_df = era_df.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)
st.dataframe(era_df, hide_index=True, use_container_width=True)

with st.expander("Why 2016 stands alone"):
    st.markdown(
        """
The 2016 race was the result of two sequential last-minute reroutes:

1. **~2 weeks before the race** — a wildfire burned through part of the standard
   Logan→Fish Haven point-to-point route, forcing an alternate course announcement.
2. **~24 hours before the race** — a severe weather forecast (heavy snow at
   elevation) prompted a second reroute on top of the first.

The final course was an **out-and-back from Logan City Park to Tony's Grove**.
Race-day conditions deteriorated to a blinding overnight blizzard. The race
website notes: *"The alternate course used in 2016 isn't eligible. If that
course is used again due to weather, the CR bonus isn't enabled for that year."*
No times from 2016 count toward standard course records, but the splits are
present in the data and the in/out structure matches Group 2's schema (just
with different stations and an outbound/inbound naming convention).
"""
    )

with st.expander("Why the course changed in 2022"):
    st.markdown(
        """
Starting in 2022, the section between Leatham Hollow and Right Hand Fork was
rerouted: **Richards Hollow (mile ~22.5)** and **Cowley Canyon (mile ~30.0)**
were replaced by a single checkpoint, **Upper Richards Hollow (mile 28.0)**.
This dropped the total tracked aid stations from 13 to 12.

The specific reason has not been publicly documented — the bear100.com course
directions page still lists the old stations as of this writing. Most likely
explanation is a trail-access or land-permit change in the lower canyon section.
"""
    )

# ---------------------------------------------------------------------------
# 4. Per-year row-status breakdown
# ---------------------------------------------------------------------------

st.header("Per-year row counts")
st.caption(
    "Group 1 years (1999–2007, 2011–2012) recorded only finishers — no DNF or "
    "Not-Started rows exist for them. 2019 has a single 'In Progress' artefact."
)

status_pivot = (
    runners.pivot_table(
        index=["year", "group"],
        columns="status",
        values="runner_idx",
        aggfunc="count",
        fill_value=0,
    )
    .reset_index()
)
# Ensure all expected columns exist
for s in ["Finished", "Dropped", "Not Started", "In Progress"]:
    if s not in status_pivot.columns:
        status_pivot[s] = 0
status_pivot["Total"] = (
    status_pivot["Finished"]
    + status_pivot["Dropped"]
    + status_pivot["Not Started"]
    + status_pivot["In Progress"]
)
status_pivot["Starters"] = status_pivot["Total"] - status_pivot["Not Started"]
status_pivot = status_pivot[
    ["year", "group", "Total", "Starters", "Finished", "Dropped", "Not Started", "In Progress"]
]
status_pivot = status_pivot.rename(columns={"year": "Year", "group": "Group", "Dropped": "DNF"})
st.dataframe(status_pivot, hide_index=True, use_container_width=True)

# Status mix by group — small bar chart
st.subheader("Status mix by group")

group_status = (
    runners.groupby(["group", "status"]).size().reset_index(name="count")
)
group_status["_sort"] = group_status["group"].map(
    {"Group 1": 0, "Group 2": 1, "2016": 2, "Group 3": 3}
)
group_status = group_status.sort_values("_sort").drop(columns="_sort")
fig = px.bar(
    group_status,
    x="group",
    y="count",
    color="status",
    barmode="stack",
    category_orders={
        "group": ["Group 1", "Group 2", "2016", "Group 3"],
        "status": ["Finished", "Dropped", "Not Started", "In Progress"],
    },
    labels={"count": "Runner rows", "group": "Group"},
    color_discrete_sequence=ACCENT_COLORS,
)
fig.update_layout(**CHART_DEFAULTS)
st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

# ---------------------------------------------------------------------------
# 5. Splits validity breakdown — the centerpiece
# ---------------------------------------------------------------------------

st.header("Split-data quality")
st.caption(
    "Every aid-station cell is tagged with a `quality_flag` at load time. "
    "The Finish row is excluded below — it isn't an in/out split."
)

n_ok = int(flag_counts.get("ok", 0))
n_incomplete = int(flag_counts.get("incomplete", 0))
n_negative = int(flag_counts.get("negative_duration", 0))
n_phantom = int(flag_counts.get("phantom_duplicate", 0))


def _pct(n: int) -> str:
    return f"{(n / n_non_finish):.1%}" if n_non_finish else "—"


q1, q2, q3, q4 = st.columns(4)
q1.metric("OK", f"{n_ok:,}", delta=_pct(n_ok), delta_color="off")
q2.metric("Incomplete", f"{n_incomplete:,}", delta=_pct(n_incomplete), delta_color="off")
q3.metric("Negative duration", f"{n_negative:,}", delta=_pct(n_negative), delta_color="off")
q4.metric("Phantom duplicate", f"{n_phantom:,}", delta=_pct(n_phantom), delta_color="off")

st.markdown(
    f"""
**What each bucket means:**

- **OK** ({n_ok:,}). Both the in-time and out-time parsed cleanly, the duration
  is non-negative, and the out-time is not a duplicate of the next station's
  in-time. These splits feed every chart on the dashboard.
- **Incomplete** ({n_incomplete:,}). One or both halves of the `HH:MM / HH:MM`
  cell were missing or unparseable. The runner may not have reached the
  station, or the timing data was never captured. `is_valid_split` is `False`
  for these.
- **Negative duration** ({n_negative:,}, ~{n_negative / n_non_finish:.1%}). Both
  halves parsed but `out_seconds < in_seconds`, which is physically impossible.
  This is a source-data quirk; we keep `is_valid_split = True` (the runner did
  reach the station) but null `aid_duration_seconds` so downstream averages
  aren't poisoned.
- **Phantom duplicate** ({n_phantom:,}). Both halves parsed, but the out-time
  exactly equals the *next* station's in-time and differs from this station's
  in-time. This is a systematic opensplittime ingestion pattern (most prominent
  at Right Hand Fork in 2020): when an out-time isn't captured, the system
  appears to backfill it from the next station's in-time, producing a
  "duration" that actually spans the inter-station travel. Duration is nulled;
  zero-duration pass-throughs (in == out, runner didn't stop) are *not* nulled.
"""
)

# Per-year stacked bar of split-quality categories (excludes Group 1 — no splits)
st.subheader("Split quality over time")
st.caption(
    "Group 1 years (1999–2007, 2011–2012) have no aid-station splits and are omitted."
)

per_year_quality = (
    non_finish.groupby(["year", "quality_flag"]).size().reset_index(name="count")
)
fig = px.bar(
    per_year_quality,
    x="year",
    y="count",
    color="quality_flag",
    category_orders={"quality_flag": QUALITY_ORDER},
    color_discrete_map=QUALITY_COLORS,
    labels={"count": "Splits", "year": "Year", "quality_flag": "Quality"},
)
fig.update_layout(barmode="stack", **CHART_DEFAULTS)
st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

# Per-station validity table — which stations lose the most data
st.subheader("Per-station validity")
st.caption(
    "Validity rate = OK / total non-Finish splits at this station, across all years "
    "where the station appears."
)

station_stats = (
    non_finish.groupby("station_name")
    .agg(
        total=("quality_flag", "size"),
        ok=("quality_flag", lambda s: (s == "ok").sum()),
        incomplete=("quality_flag", lambda s: (s == "incomplete").sum()),
        negative=("quality_flag", lambda s: (s == "negative_duration").sum()),
        phantom=("quality_flag", lambda s: (s == "phantom_duplicate").sum()),
        first_mile=("station_mile", "min"),
    )
    .reset_index()
)
station_stats["validity_rate"] = station_stats["ok"] / station_stats["total"]
station_stats = station_stats.sort_values("first_mile").reset_index(drop=True)
station_stats["validity_rate"] = (station_stats["validity_rate"] * 100).round(1).astype(str) + "%"
station_stats = station_stats.rename(
    columns={
        "station_name": "Station",
        "first_mile": "Mile",
        "total": "Total",
        "ok": "OK",
        "incomplete": "Incomplete",
        "negative": "Negative",
        "phantom": "Phantom",
        "validity_rate": "Validity",
    }
)
st.dataframe(
    station_stats[["Station", "Mile", "Total", "OK", "Incomplete", "Negative", "Phantom", "Validity"]],
    hide_index=True,
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# 6. Cleaning + analytical decisions
# ---------------------------------------------------------------------------

st.header("Cleaning and analytical decisions")

st.markdown(
    """
The decisions below are applied during loading or during analysis. Each one is
a judgement call that affects downstream numbers; they're documented here so
the dashboard is auditable.

**1. Time parsing.** Both `HH:MM` and `HH:MM:SS` formats are accepted. Tokens
like `--:--`, `--:--:--`, `-`, and empty strings parse to `None`.

**2. Negative raw durations.** When `out_seconds < in_seconds`, the runner
clearly reached the station (both halves are real timestamps), but the duration
is unreliable. We keep `is_valid_split = True` and null `aid_duration_seconds`.
This affects ~0.2% of non-Finish splits.

**3. Phantom out-times.** When a station's out-time exactly matches the next
station's in-time, and differs from this station's in-time, we treat the
out-time as a backfill artefact and null the duration. A zero-duration
pass-through (in == out) where the next station's in-time also matches is *not*
nulled — that's legitimately a fast runner who didn't stop.

**4. Group assignment by year.** Group 1: 1999–2007, 2011, 2012 (no splits).
Group 2: 2008–2010, 2013–2015, 2017–2021. 2016: standalone (out-and-back
reroute). Group 3: 2022–2025 (Upper Richards Hollow consolidation).

**5. Starters and DNF rate.** Starters = total rows minus rows with
`Status = "Not Started"`. DNF rate = `Dropped / Starters`, computed *only* over
Group 2, 2016, and Group 3 years. Group 1 years recorded only finishers, so
including them would depress the global DNF rate to zero where it should be
NaN. The headline DNF rate metric and the per-year DNF chart both honour this.

**6. Quintile assignment.** Quintiles (1 = fastest 20%) are assigned within
`(year, gender)` so that a "Q1 woman" is fast among women in her year — not
fast against the entire 27-year male field. `pandas.qcut(rank, q=5)` is used,
with `rank(method="first")` to break finish-time ties deterministically.

**7. Total aid-station time uses a complete-data quintile assignment.** For
the *total* aid-station-time chart, quintiles are recomputed using only the
runners who have a valid duration at every non-Finish station in their year.
If we instead assigned quintiles from all finishers and *then* dropped
incomplete ones, slow runners (Q5) — who are more likely to have missing
splits — would be underrepresented, making Q5 look artificially fast. The
per-station chart keeps the all-finishers assignment because individual valid
splits there are not wasted.

**8. 2019 'In Progress' row.** A single 2019 entrant has `Status = "In Progress"`.
This is a stale data artefact from opensplittime; in practice it behaves as a
DNF. No special handling — it falls outside the "Finished" filter on every
analytical function.
"""
)

# ---------------------------------------------------------------------------
# 7. Demographic and finish-time distribution
# ---------------------------------------------------------------------------

st.header("Demographics and finish times")

# Gender share by group
st.subheader("Gender mix by group")
gender_mix = (
    runners[runners["gender"].notna()]
    .groupby(["group", "gender"])
    .size()
    .reset_index(name="count")
)
gender_mix["_sort"] = gender_mix["group"].map(
    {"Group 1": 0, "Group 2": 1, "2016": 2, "Group 3": 3}
)
gender_mix = gender_mix.sort_values("_sort").drop(columns="_sort")
fig = px.bar(
    gender_mix,
    x="group",
    y="count",
    color="gender",
    barmode="stack",
    category_orders={"group": ["Group 1", "Group 2", "2016", "Group 3"]},
    labels={"count": "Runners", "group": "Group", "gender": "Gender"},
    color_discrete_sequence=ACCENT_COLORS,
)
fig.update_layout(**CHART_DEFAULTS)
st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

# Finish time histogram, faceted by group (Group 1 included — finish times exist there)
st.subheader("Finish-time distribution by group")
st.caption(
    "Finishers only. 2016 sits well to the right of Group 2 / Group 3 — the "
    "out-and-back course in a blizzard was much harder."
)

finishers = runners[runners["status"] == "Finished"].copy()
finishers["finish_hours"] = finishers["finish_seconds"] / 3600
finishers["_sort"] = finishers["group"].map(
    {"Group 1": 0, "Group 2": 1, "2016": 2, "Group 3": 3}
)
finishers = finishers.sort_values("_sort")

fig = px.histogram(
    finishers,
    x="finish_hours",
    facet_col="group",
    category_orders={"group": ["Group 1", "Group 2", "2016", "Group 3"]},
    nbins=30,
    labels={"finish_hours": "Finish time (hours)"},
    color_discrete_sequence=[ACCENT_COLORS[0]],
)
fig.update_layout(**CHART_DEFAULTS)
fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

# Compact summary stats
fin_stats = (
    finishers.groupby("group")["finish_seconds"]
    .agg(["min", "median", "mean", "max", "count"])
    .reset_index()
)
fin_stats["_sort"] = fin_stats["group"].map(
    {"Group 1": 0, "Group 2": 1, "2016": 2, "Group 3": 3}
)
fin_stats = fin_stats.sort_values("_sort").drop(columns="_sort")


def _hms(seconds) -> str:
    s = int(seconds)
    return f"{s // 3600}h{(s % 3600) // 60:02d}m"


fin_stats["Fastest"] = fin_stats["min"].apply(_hms)
fin_stats["Median"] = fin_stats["median"].apply(_hms)
fin_stats["Mean"] = fin_stats["mean"].apply(_hms)
fin_stats["Slowest"] = fin_stats["max"].apply(_hms)
fin_stats = fin_stats.rename(columns={"group": "Group", "count": "# finishers"})
st.dataframe(
    fin_stats[["Group", "# finishers", "Fastest", "Median", "Mean", "Slowest"]],
    hide_index=True,
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    "Source files: "
    "[scrape_validation_report.md](scrape_validation_report.md) — schemas and validation; "
    "[dashboard_planning.md](dashboard_planning.md) — design rationale and analytical pushback; "
    "the per-year CSVs in the repo root. "
    "Use the sidebar to jump to the **Home** dashboard or to **Year Details**."
)
