# Bear 100 Scrape Validation Report

**Source:** https://www.opensplittime.org/organizations/the-bear-100  
**Scraped:** 2026-04-22

## Years Found

27 consecutive years: 1999–2025, all with results pages linked from the organization page.

> **Note:** The 2012 spread URL was non-standard — `/events/the-bear-2012/spread` rather than `/events/the-bear-100-2012/spread` — and was extracted directly from the HTML href.

## Validation Results

All checks passed for all 27 years:

- Row counts matched the entrant counts listed on the parent page (0 mismatches)
- All rows in every file have the same column count as the header row (0 column-count mismatches)
- All 15-row spot-checks passed for every year (0 data discrepancies)

## Column Counts by Year

| Year | Entrants | Columns |
|------|----------|---------|
| 1999 | 14       | 7       |
| 2000 | 9        | 7       |
| 2001 | 17       | 7       |
| 2002 | 32       | 7       |
| 2003 | 42       | 7       |
| 2004 | 41       | 7       |
| 2005 | 36       | 7       |
| 2006 | 36       | 7       |
| 2007 | 62       | 7       |
| 2008 | 74       | 20      |
| 2009 | 132      | 20      |
| 2010 | 164      | 20      |
| 2011 | 268      | 7       |
| 2012 | 258      | 7       |
| 2013 | 263      | 20      |
| 2014 | 278      | 20      |
| 2015 | 309      | 20      |
| 2016 | 332      | 20      |
| 2017 | 338      | 20      |
| 2018 | 317      | 20      |
| 2019 | 306      | 20      |
| 2020 | 305      | 20      |
| 2021 | 306      | 20      |
| 2022 | 346      | 19      |
| 2023 | 363      | 19      |
| 2024 | 350      | 19      |
| 2025 | 335      | 19      |

## Identical Header Groups

### Group 1 — 7 columns (11 years: 1999–2007, 2011–2012)

No aid station splits — only basic fields.

```
O/G Place | Bib | Name | Category | From | Status | Finish (Mile 100.0)
```

### Group 2 — 20 columns (11 years: 2008–2010, 2013–2015, 2017–2021)

14 checkpoint columns:

```
O/G Place | Bib | Name | Category | From | Status
Logan Peak In / Out (Mile 10.5)
Leatham Hollow In / Out (Mile 19.5)
Richards Hollow In / Out (Mile 22.5)
Cowley Canyon In / Out (Mile 30.0)
Right Hand Fork In / Out (Mile 37.0)
Temple Fork In / Out (Mile 45.0)
Tony Grove In / Out (Mile 51.0)
Franklin Basin In / Out (Mile 61.0)
Logan River In / Out (Mile 69.0)
Beaver Lodge In / Out (Mile 75.1)
Gibson Basin In / Out (Mile 80.5)
Beaver Creek In / Out (Mile 84.7)
Ranger Dip In / Out (Mile 91.8)
Finish (Mile 100.0)
```

### Group 3 — 19 columns (4 years: 2022–2025)

Starting in 2022, the course was rerouted in the Richards Hollow / Cowley Canyon section. The two separate aid stations that existed on the older course — Richards Hollow (~mile 22.5) and Cowley Canyon (~mile 30.0) — were replaced by a single checkpoint called **Upper Richards Hollow at mile 28.0**. This reduced the total tracked aid stations from 14 to 13 (hence 19 columns instead of 20). A 2023 race report confirms runners pass "Upper Richards Hollow" with no mention of either prior station.

The specific reason for this reroute has not been publicly documented. The bear100.com course directions page still lists Richards Hollow and Cowley Canyon as of this writing, suggesting the page has not been updated to reflect the current routing. The most likely explanations are a trail access or land permit change in the lower canyon section. The race directors (bear100info@gmail.com) would be the authoritative source.

Similar to Group 2 but with Upper Richards Hollow replacing both Richards Hollow and Cowley Canyon:

```
O/G Place | Bib | Name | Category | From | Status
Logan Peak In / Out (Mile 10.5)
Leatham Hollow In / Out (Mile 19.5)
Upper Richards Hollow In / Out (Mile 28.0)
Right Hand Fork In / Out (Mile 37.0)
Temple Fork In / Out (Mile 45.0)
Tony Grove In / Out (Mile 51.0)
Franklin Basin In / Out (Mile 61.0)
Logan River In / Out (Mile 69.0)
Beaver Lodge In / Out (Mile 75.1)
Gibson Basin In / Out (Mile 80.5)
Beaver Creek In / Out (Mile 84.7)
Ranger Dip In / Out (Mile 91.8)
Finish (Mile 100.0)
```

### Unique — 20 columns (2016 only)

The 2016 course was the result of two sequential last-minute reroutes:

1. **~2 weeks before the race:** A wildfire burned through part of the standard Logan→Fish Haven point-to-point route, forcing an alternate course announcement.
2. **~24 hours before the race:** A severe weather forecast (heavy snow at elevation) prompted a second reroute on top of the first.

The final course was an **out-and-back from Logan City Park to Tony's Grove**, with a Bonneville Shoreline Trail extension at the start to make up distance. Race-day conditions were severe: rain and mud at the start, deteriorating to snow and a blinding blizzard overnight. This is why aid stations appear as both Outbound and Inbound legs in the data.

The race website notes: *"The alternate course used in 2016 isn't eligible. If that course is used again due to weather, the CR bonus isn't enabled for that year."* No times from 2016 count toward standard course records.

The 2016 schema is entirely different from all other years:

```
O/G Place | Bib | Name | Category | From | Status
Logan Peak Outbound In / Out (Mile 10.5)
Leatham Hollow Outbound In / Out (Mile 19.7)
Richards Hollow Outbound In / Out (Mile 22.5)
Cowley Canyon Outbound In / Out (Mile 30.0)
Right Hand Fork Outbound In / Out (Mile 36.9)
Temple Fork Outbound In / Out (Mile 45.2)
Tony Grove In / Out (Mile 51.8)
Temple Fork Inbound In / Out (Mile 58.4)
Right Hand Fork Inbound In / Out (Mile 66.7)
Cowley Canyon Inbound In / Out (Mile 73.6)
Richards Hollow Inbound In / Out (Mile 81.1)
Leatham Hollow Inbound In / Out (Mile 83.9)
Logan Peak Inbound In / Out (Mile 93.1)
Finish (Mile 100.0)
```
