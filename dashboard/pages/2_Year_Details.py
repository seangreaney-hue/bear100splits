"""
Year details page — prototype.

Shows the raw CSV data for a selected year. Future iterations will add per-year analytics.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make sibling modules importable
sys.path.insert(0, str(Path(__file__).parent.parent))
from data import load_all  # noqa: E402
from nav import render_nav  # noqa: E402

st.set_page_config(page_title="Year details — Bear 100", layout="wide")

render_nav()

st.title("Year details")
st.caption("Raw CSV view (per-year analytics coming in a later iteration).")

runners, _ = load_all()

year_options = sorted(runners["year"].unique(), reverse=True)
_year_col, _ = st.columns([1, 4])
selected_year = _year_col.selectbox("Select year", year_options, index=0)

# Repo root is two levels up from this file: dashboard/pages/ → dashboard/ → repo
repo_root = Path(__file__).parent.parent.parent
csv_path = repo_root / f"{selected_year}.csv"

if not csv_path.exists():
    st.error(f"CSV not found at {csv_path}")
    st.stop()

raw = pd.read_csv(csv_path)

# Quick summary
year_runners = runners[runners["year"] == selected_year]
n_starters = int((year_runners["status"] != "Not Started").sum())
n_finishers = int((year_runners["status"] == "Finished").sum())
n_dropped = int((year_runners["status"] == "Dropped").sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total entrants", f"{len(raw):,}")
c2.metric("Starters", f"{n_starters:,}")
c3.metric("Finishers", f"{n_finishers:,}")
c4.metric("DNFs", f"{n_dropped:,}" if n_dropped > 0 else "—")

st.subheader(f"{selected_year} — full results")
st.dataframe(raw, use_container_width=True, hide_index=True)
