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
# Course event annotations (shared across all time-series charts)
# ---------------------------------------------------------------------------

COURSE_EVENTS = [
    {"year": 2016, "label": "2016 reroute", "color": "#f0a500", "dash": "dash"},
    {"year": 2022, "label": "2022 course change", "color": "#7eb8f7", "dash": "dot"},
]


def _add_course_event_lines(fig) -> None:
    for ev in COURSE_EVENTS:
        fig.add_vline(
            x=ev["year"],
            line_dash=ev["dash"],
            line_color=ev["color"],
            line_width=1.5,
            annotation_text=ev["label"],
            annotation_position="top right",
            annotation_font_size=11,
            annotation_font_color=ev["color"],
        )


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

st.header("Race history")
st.caption("1999-2007, 2011-2012 data contains finishers only.")
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
_add_course_event_lines(fig)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "2016: one-off fire reroute. "
    "2022: permanent course change; one aid station moved, one dropped."
)
# ---------------------------------------------------------------------------
# Podium per year
# ---------------------------------------------------------------------------

st.header("Podium")
st.caption("Top 3 finishers per gender.")
year_options = sorted(runners["year"].unique(), reverse=True)
_year_col, _ = st.columns([1, 4])
selected_year = _year_col.selectbox("Year", year_options, index=0, key="podium_year")

if selected_year == 2016:
    st.info(
        "**2016 used a different course** — an out-and-back from Logan to Tony's Grove. "
        "Race directors declared these times ineligible for course records. "
        "This year also had the highest DNF rate in race history."
    )


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


pcol1, pcol2 = st.columns(2)
with pcol1:
    st.subheader("Men")
    _render_podium_table(podium_per_year(runners, selected_year, "Male"))
with pcol2:
    st.subheader("Women")
    _render_podium_table(podium_per_year(runners, selected_year, "Female"))

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
_add_course_event_lines(fig)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "2016: one-off fire reroute. "
    "2022: permanent course change; one aid station moved, one dropped."
)
# ---------------------------------------------------------------------------
# Aid station analysis
# ---------------------------------------------------------------------------

st.header("Aid station analysis")
st.caption(
    "Aid station data only exists for years with split timing. "
    "Groups: 2008–2010, 2013–2015, 2017–2021 (Group 2, 14 stations); "
    "2016 (out-and-back reroute, separate era); "
    "2022–2025 (Group 3, permanent course change — 13 stations). "
    "Group 1 years (1999–2007, 2011–2012) are excluded."
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
