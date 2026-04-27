"""
Bear 100 Dashboard — Home page.

Minimal end-to-end prototype (Path B): everything inline, default styling.
We'll extract reusable charts and add the dark theme after the structure proves out.

Run with:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# Make data and analysis modules importable when running via `streamlit run`
sys.path.insert(0, str(Path(__file__).parent))
from data import load_all  # noqa: E402
from analysis import (  # noqa: E402
    aid_time_per_quintile_per_station,
    dnf_rate_per_year,
    hero_stats,
    overall_finish_average_per_year,
    podium_per_year,
    racer_history_per_year,
    top_n_average_per_group,
    top_n_average_per_year,
    total_aid_time_per_quintile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fmt_hms(seconds) -> str:
    """Convert seconds to 'HH:MM:SS' string. Returns em-dash for nulls."""
    if pd.isna(seconds):
        return "—"
    s = int(seconds)
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def fmt_hm(seconds) -> str:
    """Convert seconds to 'Xh MMm' string."""
    if pd.isna(seconds):
        return "—"
    s = int(seconds)
    return f"{s // 3600}h {(s % 3600) // 60:02d}m"


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Bear 100 Dashboard",
    page_icon="🐻",
    layout="wide",
)

st.title("The Bear 100")
st.caption("27 years of ultramarathon results from opensplittime.org")

# ---------------------------------------------------------------------------
# Load data (cached in data.py via lru_cache)
# ---------------------------------------------------------------------------

runners, splits = load_all()

# ---------------------------------------------------------------------------
# Sidebar: global gender filter
# ---------------------------------------------------------------------------

st.sidebar.header("Filters")
gender_choice = st.sidebar.radio(
    "Gender view",
    options=["Overall", "Male", "Female"],
    index=0,
    help="Filters all charts.",
)
gender_filter: str | None = None if gender_choice == "Overall" else gender_choice

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Active filter:** {gender_choice}")
st.sidebar.markdown(f"**Total runners loaded:** {len(runners):,}")
st.sidebar.markdown(f"**Total splits loaded:** {len(splits):,}")

# ---------------------------------------------------------------------------
# Hero stats
# ---------------------------------------------------------------------------

st.header("Overview")

stats = hero_stats(runners, gender=gender_filter)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Years", f"{stats['n_years']}")
c2.metric("Starters", f"{stats['n_starters']:,}")
c3.metric("Finishers", f"{stats['n_finishers']:,}")
c4.metric("Finish rate*", f"{stats['finish_rate']:.1%}")
c5.metric("DNF rate*", f"{stats['dnf_rate']:.1%}")

st.caption(
    "*Finish\DNF rate excludes years 1999-2007, 2011-2012 which only recorded finishers."
)

# ---------------------------------------------------------------------------
# Racer history (starters and finishers over time; gender filter applies)
# ---------------------------------------------------------------------------

st.header("Racer history")

history_df = racer_history_per_year(runners, gender=gender_filter)
dnf_df = dnf_rate_per_year(runners, gender=gender_filter)

fig = make_subplots(specs=[[{"secondary_y": True}]])

colors = px.colors.qualitative.Plotly
for i, metric in enumerate(["Finishers", "Starters"]):
    grp = history_df[history_df["metric"] == metric]
    fig.add_trace(
        go.Scatter(x=grp["year"], y=grp["count"], name=metric, mode="lines", line=dict(color=colors[i])),
        secondary_y=False,
    )

fig.add_trace(
    go.Scatter(
        x=dnf_df["year"],
        y=dnf_df["dnf_rate"],
        name="DNF Rate",
        mode="lines",
        line=dict(dash="dot", color=colors[2]),
    ),
    secondary_y=True,
)

fig.update_yaxes(title_text="Racers", secondary_y=False)
fig.update_yaxes(title_text="DNF Rate", tickformat=".0%", range=[0, 1], secondary_y=True)
fig.update_layout(xaxis_title="Year", legend_title_text="")
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Podium per year
# ---------------------------------------------------------------------------

st.header("Podium")

year_options = sorted(runners["year"].unique(), reverse=True)
_year_col, _ = st.columns([1, 4])
selected_year = _year_col.selectbox("Year", year_options, index=0, key="podium_year")


def _render_podium_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No finishers recorded for this gender/year.")
        return
    show = df.copy()
    show["time"] = show["finish_seconds"].apply(fmt_hms)
    show["place"] = show["gender_place"].astype(int)
    st.dataframe(
        show[["place", "name", "time"]],
        hide_index=True,
        use_container_width=True,
    )


if gender_filter is None:
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        st.subheader("Men")
        _render_podium_table(podium_per_year(runners, selected_year, "Male"))
    with pcol2:
        st.subheader("Women")
        _render_podium_table(podium_per_year(runners, selected_year, "Female"))
else:
    st.subheader(gender_filter)
    _render_podium_table(podium_per_year(runners, selected_year, gender_filter))


# ---------------------------------------------------------------------------
# Top 5 average finish time
# ---------------------------------------------------------------------------

st.header("Top 5 average finish time")
st.caption(
    "Per year and gender, the average of the top 5 finish times. Years with fewer than 5 finishers of that gender are skipped."
)

t5_year = top_n_average_per_year(runners, n=5, gender=gender_filter)
t5_year["avg_top_n_hours"] = t5_year["avg_top_n_seconds"] / 3600

fig = px.line(
    t5_year,
    x="year",
    y="avg_top_n_hours",
    color="gender" if gender_filter is None else None,
    markers=True,
    labels={"avg_top_n_hours": "Average top-5 finish (hours)", "year": "Year", "gender": "Gender"},
)
st.plotly_chart(fig, use_container_width=True)

# Per-group summary table
st.subheader("Top 5 average per group")
t5g = top_n_average_per_group(runners, n=5, gender=gender_filter)
t5g_show = t5g.copy()
t5g_show["avg_top_5"] = t5g_show["avg_top_n_seconds"].apply(fmt_hm)
st.dataframe(
    t5g_show[["group", "gender", "avg_top_5", "n_finishers_in_group"]].rename(
        columns={"n_finishers_in_group": "finishers in group"}
    ),
    hide_index=True,
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# Overall yearly average finish
# ---------------------------------------------------------------------------

st.header("Overall yearly average finish time")
st.caption("Average finish time across all finishers in each year.")

oy_df = overall_finish_average_per_year(runners, gender=gender_filter)
oy_df["avg_hours"] = oy_df["avg_finish_seconds"] / 3600

fig = px.line(
    oy_df,
    x="year",
    y="avg_hours",
    color="gender" if gender_filter is None else None,
    markers=True,
    labels={"avg_hours": "Average finish (hours)", "year": "Year", "gender": "Gender"},
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Aid station analysis
# ---------------------------------------------------------------------------

st.header("Aid station analysis")
st.caption(
    "Aid station data only exists for years with split timing (Group 2: 2008–2010, 2013–2015, 2017–2021; "
    "2016: out-and-back course; Group 3: 2022–2025). Group 1 years are excluded."
)

# Total time per quintile per group
st.subheader("Total time spent in aid stations, by finisher quintile")
st.caption(
    "Quintile 1 = fastest 20% of finishers in their year/gender. Only runners with complete valid splits are counted in totals."
)

tot_df = total_aid_time_per_quintile(runners, splits, gender=gender_filter)
tot_df["avg_total_minutes"] = tot_df["avg_total_aid_seconds"] / 60

fig = px.bar(
    tot_df,
    x="quintile",
    y="avg_total_minutes",
    color="group",
    barmode="group",
    labels={
        "avg_total_minutes": "Average total minutes in aid stations",
        "quintile": "Finisher quintile (1=fastest)",
        "group": "Era",
    },
)
st.plotly_chart(fig, use_container_width=True)

# Average time per station, through the race
st.subheader("Aid station time through the race")
st.caption(
    "Average aid station duration at each station, by quintile and era. X-axis is station mile so cross-era comparison is direct."
)

ats_df = aid_time_per_quintile_per_station(runners, splits, gender=gender_filter)
ats_df["avg_minutes"] = ats_df["avg_duration_seconds"] / 60
ats_df["quintile"] = ats_df["quintile"].astype(int)

fig = px.line(
    ats_df,
    x="station_mile",
    y="avg_minutes",
    color="quintile",
    facet_col="group",
    markers=True,
    labels={
        "avg_minutes": "Average minutes at station",
        "station_mile": "Station mile",
        "quintile": "Quintile",
        "group": "Era",
    },
    hover_data=["station_name"],
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    "Data source: opensplittime.org/organizations/the-bear-100. "
    "See `dashboard_planning.md` and `scrape_validation_report.md` for methodology and known data quirks."
)
