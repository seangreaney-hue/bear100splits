# Bear 100 Dashboard — Planning Notes

Pre-implementation dialogue between user and Claude. Captures platform recommendation, design direction, analytical pushback, and open questions.

## Platform recommendation: Streamlit + Plotly

Given the requirements (interactive gender toggle, multi-page navigation later, CSV-backed, local-first, design-conscious, prototype speed), **Streamlit** with Plotly for charts and a custom theme is the best fit.

Reasoning:

- Python-native, so pandas does the heavy analytical lifting directly
- Built-in widgets (toggles, radio, dropdowns) handle the "Overall / Male / Female" filter cleanly
- Native multi-page support via the `pages/` directory — solves the future "navigate to a year" requirement
- Runs locally with `streamlit run`, easy to deploy later if desired
- Fast iteration: refresh on save

**Caveat:** out of the box, Streamlit looks like every other Streamlit dashboard. To get something that *feels* designed, we'd lean on a custom theme (`.streamlit/config.toml`), careful typography, and Plotly chart styling. If the goal is something that looks like a Pudding article or Observable HQ out of the gate, Streamlit isn't that — **Observable Framework** is the right tool for design-first, but it's a steeper ramp (JavaScript, build step, more setup).

**Recommendation:** Streamlit for the prototype. If the analytics prove valuable and the design investment is worth it later, port the final version to Observable or a Next.js app.

### Alternatives evaluated

- **Dash (Plotly)** — more design control than Streamlit but more boilerplate; marginal gain for this use case
- **Evidence.dev** — gorgeous, SQL-based, but forces a DB layer that's overkill for 27 CSVs
- **Quarto** — beautiful, but static; kills the interactivity requirement
- **Next.js + React + D3/Recharts** — maximum flexibility, but overkill for a prototype

## Design direction

Modern dashboard trends that would suit race data well:

- **Dark neutral background** with one or two accent colors (e.g., deep slate with amber accents for a "long overnight ultra" vibe). Not required, but fits thematically.
- **Large number + small label** hero stats ("27 years · 7,018 entrants · 61% finish rate")
- **Small multiples over stacked single charts** — for the top-5/group visualization, a row of faceted mini-charts (one per group) beats one chart with disconnected lines
- **Direct labeling on line charts** instead of legends (Bloomberg/FT style)
- **Muted gridlines**, generous whitespace, sans-serif system fonts
- **Annotated events on time series** (2016 callout, 2022 course change) — this data *needs* annotations to make sense

### Solving the "disconnected lines" problem

For time-series data that spans multiple course-config eras, the cleanest solutions are:

- **(a)** Small multiples per group (3 mini-charts)
- **(b)** A single chart with gaps preserved but shaded background bands labeling each era

**Lean toward (b)** — it keeps the temporal continuity visible and turns the course changes into part of the story, not an inconvenience.

## Analytical pushback / things to flag

### 1. 2016 is not comparable

2016 was a completely different course (out-and-back from Logan to Tony's Grove), different distance effectively, and the race directors themselves declared those times ineligible for records. Recommendation: **exclude 2016 from finishing-time and aid-station analyses** but include it in entrant/DNF charts.

### 2. DNS rates probably can't be calculated

"Entrants" on OpenSplitTime likely means people with *any* recorded timing — i.e., starters. If someone registered and never showed up, they may not appear in the CSV at all. Need to verify what the Status column contains. **We may only be able to calculate DNF rate**, not DNS.

### 3. "Average of top 5" is defensible but fragile for small fields

It's a common "elite depth" signal, but for small fields (1999: 14 entrants total, maybe 1–2 female finishers), top-5 is meaningless or impossible. Options:

- Start top-5 analysis from a year with enough finishers
- Degrade gracefully (top-N where N = min(5, available))

### 4. Finisher quintile basis: within-gender

Quintiles should be computed **within gender**, since the question is really "do fast men differ from slow men at aid stations." Computing them overall would mostly separate the genders rather than the behavior.

### 5. Total aid-station time is misleading with missing data

If a runner has 9/14 valid aid station splits, their "total" undercounts. For total-time analysis, restrict to runners with complete splits. For average-time analysis, valid splits only are fine.

### 6. Group numbering clarification needed

The markdown validation file names them Groups 1/2/3 + Unique (2016). The user referenced "Group 3 to Group 4 transition" in the aid station section — likely meant **Group 2 → Group 3 transition** (the 14→13 aid station drop in 2022). Needs confirmation.

### 7. Aid station analysis only covers ~15 years

The 7-column years (1999–2007, 2011, 2012) have no split data. Aid station analysis applies to Group 2 (2008–2010, 2013–2015, 2017–2021), 2016 (own group, in/out times confirmed present), and Group 3 (2022–2025). This cuts the aid-station dataset roughly in half — still plenty of data, but worth knowing.

**Correction (Apr 2026):** Original note incorrectly excluded 2016. Decision #4 confirmed 2016 has valid in/out split data with 13 aid stations. Station counts throughout exclude the Finish row: Group 2 = 13 aid stations, 2016 = 13 aid stations, Group 3 = 12 aid stations.

## Decisions

1. **Platform:** Streamlit + Plotly.
2. **Theme:** Dark, with a "long overnight ultra" vibe (deep slate background, amber/warm accent).
3. **Gender toggle:** Global filter at the top of the Home page (Overall / Male / Female). Simpler and more coherent than per-chart toggles.
4. **2016 handling:** **Keep 2016 in all analyses.** Treat it as its own group in any group-based chart (separate from Group 1 / Group 2 / Group 3 as defined in the validation md). Aid station analysis still applies — 2016 had 14 stations with in/out times. The course was different, so 2016 standing alone in group-based visuals is honest.
5. **Group numbering:** Use the naming from `scrape_validation_report.md` (Group 1 = 7 cols, Group 2 = 20 cols, Group 3 = 19 cols, plus 2016 as its own fourth group for grouping analyses).
6. **Location:** Same repo, `dashboard/` subfolder. Reasoning: single-repo keeps data scraper + CSVs + dashboard together with coherent git history, no cross-repo coordination, trivial relative imports. Can split into a separate repo later if the dashboard grows.

### DNS / starter count (revised from flag #2)

"Not Started" does appear in some years' Status column (e.g., 2024 has two "Not Started" entrants at the end). It's not consistent across all years, so DNS rate is dropped as a metric.

- **Starters = total rows − rows with Status = "Not Started"**
- **DNF rate = DNFs / Starters**
- Headline "entrants" numbers displayed in the dashboard use **starters**, not raw row counts.

### Total aid-station time (revised from flag #5)

- **Total-time analysis:** drop runners who have any missing aid station splits.
- **Per-station average analysis:** runners with missing data elsewhere can still contribute to stations where they have valid in/out times.

**Further revision (Apr 2026):** Original approach assigned quintiles from all finishers, then dropped incomplete runners — this introduced selection bias, as Q5 (slowest) runners are more likely to have missing splits, making Q5 look artificially fast. Fix: quintile boundaries are now computed *within the complete-data population only* for the total-time chart. The per-station chart retains the original approach (all finishers, valid splits where present) since it uses individual splits not totals.

## Proposed folder structure

```
bear100splits/
├── *.csv                          # existing data
├── scrape_bear100.py              # existing
├── scrape_validation_report.md    # existing
├── dashboard_planning.md          # this file
├── requirements.txt               # new (pandas, streamlit, plotly)
└── dashboard/
    ├── .streamlit/
    │   └── config.toml            # dark theme config
    ├── app.py                     # Home page entry
    ├── pages/
    │   └── 1_Year_Details.py      # year deep-dive (prototype: raw data only)
    ├── data.py                    # CSV loading + preprocessing
    ├── analysis.py                # quintiles, aid station logic, DNF rates, etc.
    └── charts.py                  # reusable Plotly chart builders
```

Separation of concerns: `data.py` loads and cleans, `analysis.py` computes, `charts.py` renders, `app.py` / `pages/` compose the UI.

## Scope summary (as requested)

### Home page

- Hero stats (total years, entrants, finishers, etc. — from validation md)
- Men's and women's podium finishers per year
- Time series: # of male and female entrants over time (two labeled lines)
- Top 5 finishing times + average per gender per group, plus a visualization of how these averages change by time and by group
- Same exercise for overall averages per year by gender
- DNF and DNS rates per year
- Aid station analysis:
  - Average aid station time per gender by finisher quintile (hypothesis: top finishers spend less time)
  - Total time in aid stations, with attention to the 14→13 station transition
  - How average aid-station time per runner increases throughout the race
- Interactive Overall/Male/Female toggle for gender-specific views

### Year pages (prototype scope)

- Navigation from Home to a specific year's detailed view
- For the prototype: just display the raw CSV data for that year
- Full per-year analytics deferred to a future iteration

---

## Implementation status (as of Apr 2026)

### What's been built

- `data.py` — CSV loading, group assignment, derived columns (`is_starter`, etc.)
- `analysis.py` — all analytical functions: `hero_stats`, `racer_history_per_year`, `dnf_rate_per_year`, `podium_per_year`, `top_n_average_per_year`, `top_n_average_per_group`, `overall_finish_average_per_year`, `assign_finisher_quintiles`, `total_aid_time_per_quintile`, `aid_time_per_quintile_per_station`
- `app.py` — Home page with all planned sections
- `pages/1_Year_Details.py` — year detail page (raw CSV + summary metrics)

### Changes from original scope

- **"Starters over time" → "Racer history"**: chart now shows Starters and Finishers as two lines (not Male/Female), with gender filter applied. Starters line gaps at Group 1 years (1999–2007, 2011–2012) where only finisher records exist.
- **DNF rate merged into Racer history**: instead of a standalone DNF/DNS section, DNF rate is a dashed secondary-axis line on the Racer history chart.
- **Course event annotations**: vertical reference lines at 2016 and 2022 on all three time-series line charts; contextual banner on Podium when 2016 is selected.
- **Aid station charts redesigned**: total time and avg per-stop charts now use `x=era, color=quintile` (instead of `x=quintile, color=era`). Added a new bar chart of per-station times with an era dropdown, alongside the existing faceted line chart.

---

## Deviations from plan guidelines (not yet resolved)

These are noted for awareness — no code changes made.

1. **`charts.py` was never created.** The planned folder structure calls for a `charts.py` with reusable Plotly chart builders. All chart code is currently inline in `app.py`. This violates the separation-of-concerns principle stated in the folder structure section. Should be extracted when the chart set stabilises.

2. **Dark theme not configured.** Decision #2 specifies a dark "long overnight ultra" vibe with deep slate background and amber/warm accents, implemented via `.streamlit/config.toml`. No `config.toml` exists. Charts are rendered with Plotly defaults on the default Streamlit theme.

3. **No direct labeling on line charts.** Design direction calls for Bloomberg/FT-style direct labels instead of legends. All charts use Plotly legends.

4. **Background bands not used for era separation.** Design direction section "lean toward (b)" recommends shaded background bands on time-series to mark eras. We used vertical event lines instead, which is thinner but doesn't communicate era *spans*.

5. **Gender toggle on Racer history.** Original scope said "# of male and female entrants over time (two labeled lines)" — implying the two lines should be Male and Female, not Starters and Finishers. The implementation changed this intentionally, but it diverges from the written spec.
