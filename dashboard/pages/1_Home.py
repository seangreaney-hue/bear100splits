"""
Bear 100 Dashboard — Home page.

Reached via the sidebar from the Data Notes entry page.
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
sys.path.insert(0, str(Path(__file__).parent.parent))
from data import load_all  # noqa: E402
from nav import render_nav  # noqa: E402
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
from streamlit_utils.chart_config import ACCENT_COLORS, CHART_CONFIG, CHART_DEFAULTS  # noqa: E402


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

render_nav()

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
    {"year": 2016, "label": "2016", "color": "#f0a500", "dash": "dash", "annotation_position": "bottom left"},
    {"year": 2022, "label": "2022", "color": "#7eb8f7", "dash": "dot", "annotation_position": "bottom right"},
]


def _add_course_event_lines(fig) -> None:
    for ev in COURSE_EVENTS:
        fig.add_vline(
            x=ev["year"],
            line_dash=ev["dash"],
            line_color=ev["color"],
            line_width=1.5,
            annotation_text=ev["label"],
            annotation_position=ev["annotation_position"],
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
    "*Finish/DNF rate excludes years 1999-2007, 2011-2012 which only recorded finishers."
)

# ---------------------------------------------------------------------------
# Racer history (starters and finishers over time; gender filter applies)
# ---------------------------------------------------------------------------

st.header("Race history")
st.caption("1999-2007, 2011-2012 data contains finishers only.")
history_df = racer_history_per_year(runners, gender=gender_filter)
dnf_df = dnf_rate_per_year(runners, gender=gender_filter)

fig = make_subplots(specs=[[{"secondary_y": True}]])

for i, metric in enumerate(["Finishers", "Starters"]):
    grp = history_df[history_df["metric"] == metric]
    fig.add_trace(
        go.Scatter(x=grp["year"], y=grp["count"], name=metric, mode="lines", line=dict(color=ACCENT_COLORS[i])),
        secondary_y=False,
    )

fig.add_trace(
    go.Scatter(
        x=dnf_df["year"],
        y=dnf_df["dnf_rate"],
        name="DNF Rate",
        mode="lines",
        line=dict(dash="dot", color=ACCENT_COLORS[2]),
    ),
    secondary_y=True,
)

fig.update_yaxes(title_text="Racers", automargin=True, secondary_y=False)
fig.update_yaxes(title_text="DNF Rate", tickformat=".0%", range=[0, 1], automargin=True, secondary_y=True)
fig.update_layout(xaxis_title="Year", legend_title_text="", **CHART_DEFAULTS)
_add_course_event_lines(fig)
st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)
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
        width="stretch",
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
    color_discrete_sequence=ACCENT_COLORS,
)
fig.update_layout(**CHART_DEFAULTS)
_add_course_event_lines(fig)
st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)
st.caption(
    "2016: one-off fire reroute. "
    "2022: permanent course change; one aid station moved, one dropped."
)
# ---------------------------------------------------------------------------
# Aid station analysis
# ---------------------------------------------------------------------------

st.header("Aid station analysis")
st.caption(
    "No split timing data available for years 1999-2007, 2011-2012. "
    "2016 - out-and-back reroute, 13 aid stations. "
    "2022–2025 - permanent course change; 12 aid stations. "
)

# Shared era config for aid station charts. Labels are kept short so they don't
# rotate on narrow viewports (which would collide with the bottom legend);
# aid-station counts are already documented in the section caption above.
_ERA_LABELS = {
    "Group 2": "Pre-2022",
    "2016": "2016 reroute",
    "Group 3": "2022+",
}
_ERA_ORDER = ["Pre-2022", "2016 reroute", "2022+"]

# Pre-compute per-station data (shared by all aid station charts below)
ats_df = aid_time_per_quintile_per_station(runners, splits, gender=gender_filter)
ats_df["avg_minutes"] = ats_df["avg_duration_seconds"] / 60
ats_df["quintile"] = ats_df["quintile"].astype(int)
ats_df["Quintile"] = ats_df["quintile"].astype(str)
ats_df["era"] = ats_df["group"].map(_ERA_LABELS)

tot_df = total_aid_time_per_quintile(runners, splits, gender=gender_filter)
tot_df["avg_total_minutes"] = tot_df["avg_total_aid_seconds"] / 60
tot_df["era"] = tot_df["group"].map(_ERA_LABELS)
tot_df["Quintile"] = tot_df["quintile"].astype(str)

# Era filter — shared by all aid-station charts below
_era_options = ["All eras"] + _ERA_ORDER
_era_col, _ = st.columns([1, 3])
selected_era = _era_col.selectbox("Era", options=_era_options, index=0, key="aid_era")

ats_plot = ats_df if selected_era == "All eras" else ats_df[ats_df["era"] == selected_era]
tot_plot_base = tot_df if selected_era == "All eras" else tot_df[tot_df["era"] == selected_era]

# Total time per quintile
st.subheader("Total time spent in aid stations, by finisher quintile")
st.caption(
    "Quintile 1 = fastest 20% of finishers. Only runners with a valid split at every station are counted. "
    "Quintiles are assigned within this complete-data population."
)

tot_agg = tot_plot_base.groupby("Quintile", sort=False)["avg_total_minutes"].mean().reset_index()
fig = px.bar(
    tot_agg,
    x="Quintile",
    y="avg_total_minutes",
    color="Quintile",
    category_orders={"Quintile": ["1", "2", "3", "4", "5"]},
    labels={"avg_total_minutes": "Avg total minutes in aid stations", "Quintile": "Quintile"},
    color_discrete_sequence=ACCENT_COLORS,
)
fig.update_layout(**CHART_DEFAULTS)
st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)

# Average time per aid station stop
st.subheader("Average time per aid station stop, by quintile")
st.caption("Average duration per individual station stop, averaged across all stations in the selection.")

avg_by_quintile = ats_plot.groupby("Quintile", sort=False)["avg_minutes"].mean().reset_index()
fig = px.bar(
    avg_by_quintile,
    x="Quintile",
    y="avg_minutes",
    color="Quintile",
    category_orders={"Quintile": ["1", "2", "3", "4", "5"]},
    labels={"avg_minutes": "Avg minutes per station stop", "Quintile": "Quintile"},
    color_discrete_sequence=ACCENT_COLORS,
)
fig.update_layout(**CHART_DEFAULTS)
st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)

# Average stop time by station — horizontal bar (per-station avg, optional quintile filter)
st.subheader("Average stop time by station")
st.caption("Average stop time at each aid station. Defaults to all runners; use the dropdown to filter by quintile.")
st.markdown(
    "Station numbers are the sequence within each era. "
    "See the **Aid station legend** at the bottom of this page for the name and mileage of each numbered station."
)

_quintile_options = [
    "All runners",
    "Quintile 1 (fastest)",
    "Quintile 2",
    "Quintile 3",
    "Quintile 4",
    "Quintile 5 (slowest)",
]
_q_col, _ = st.columns([1, 3])
selected_quintile = _q_col.selectbox(
    "Quintile",
    options=_quintile_options,
    index=0,
    key="aid_station_quintile",
)

if selected_quintile == "All runners":
    src = ats_plot
else:
    q_int = int(selected_quintile.split()[1])
    src = ats_plot[ats_plot["quintile"] == q_int]

agg = (
    src.assign(_w=src["avg_minutes"] * src["n_valid_splits"])
    .groupby("station_order", as_index=False)
    .agg(_w_sum=("_w", "sum"), _n=("n_valid_splits", "sum"))
)
agg["avg_minutes"] = agg["_w_sum"] / agg["_n"]
agg = agg.sort_values("station_order")
agg["Station"] = agg["station_order"].astype(str)
station_order_labels = agg["Station"].tolist()

fig = px.bar(
    agg,
    x="avg_minutes",
    y="Station",
    orientation="h",
    category_orders={"Station": station_order_labels},
    labels={"avg_minutes": "Avg minutes at station", "Station": "Aid station #"},
    color_discrete_sequence=ACCENT_COLORS,
)
fig.update_layout(**CHART_DEFAULTS, height=480)
st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)

# ---------------------------------------------------------------------------
# Aid station legend
# ---------------------------------------------------------------------------

st.header("Aid station legend")
st.caption(
    "Each era has its own sequence of aid stations. The tables below decode the "
    "station numbers used in the 'Average stop time by station' chart above."
)

legend = (
    ats_df.drop_duplicates(["era", "station_order"])
    [["era", "station_order", "station_name", "station_mile"]]
    .sort_values(["era", "station_order"])
    .rename(columns={"station_order": "#", "station_name": "Station", "station_mile": "Mile"})
)

_lcols = st.columns(3)
for col, era_name in zip(_lcols, _ERA_ORDER):
    with col:
        st.subheader(era_name)
        era_legend = legend[legend["era"] == era_name][["#", "Station", "Mile"]]
        st.dataframe(era_legend, hide_index=True, width="stretch")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    "Data source: opensplittime.org/organizations/the-bear-100. "
    "See `dashboard_planning.md` and `scrape_validation_report.md` for methodology and known data quirks."
)
