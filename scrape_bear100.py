#!/usr/bin/env python3
"""Scrape Bear 100 race results from opensplittime.org and save as CSV files."""

import csv
import random
import re
import sys
import time
import urllib.request
from bs4 import BeautifulSoup

BASE_URL = "https://www.opensplittime.org"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# From org page (extracted via curl): year -> (event_group_href, entrant_count)
ORG_DATA = {
    2025: ("/event_groups/the-bear-100-2025", 335),
    2024: ("/event_groups/the-bear-100-2024", 350),
    2023: ("/event_groups/the-bear-100-2023", 363),
    2022: ("/event_groups/the-bear-100-2022", 346),
    2021: ("/event_groups/the-bear-100-2021", 306),
    2020: ("/event_groups/the-bear-100-2020", 305),
    2019: ("/event_groups/the-bear-100-2019", 306),
    2018: ("/event_groups/the-bear-100-2018", 317),
    2017: ("/event_groups/the-bear-100-2017", 338),
    2016: ("/event_groups/the-bear-100-2016", 332),
    2015: ("/event_groups/the-bear-100-2015", 309),
    2014: ("/event_groups/the-bear-100-2014", 278),
    2013: ("/event_groups/the-bear-100-2013", 263),
    2012: ("/event_groups/the-bear-100-2012", 258),
    2011: ("/event_groups/the-bear-100-2011", 268),
    2010: ("/event_groups/the-bear-100-2010", 164),
    2009: ("/event_groups/the-bear-100-2009", 132),
    2008: ("/event_groups/the-bear-100-2008", 74),
    2007: ("/event_groups/the-bear-100-2007", 62),
    2006: ("/event_groups/the-bear-100-2006", 36),
    2005: ("/event_groups/the-bear-100-2005", 36),
    2004: ("/event_groups/the-bear-100-2004", 41),
    2003: ("/event_groups/the-bear-100-2003", 42),
    2002: ("/event_groups/the-bear-100-2002", 32),
    2001: ("/event_groups/the-bear-100-2001", 17),
    2000: ("/event_groups/the-bear-100-2000", 9),
    1999: ("/event_groups/the-bear-100-1999", 14),
}


def fetch_url(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def get_spread_url(event_group_href):
    """Fetch event group page and extract the 'Full' spread href."""
    html = fetch_url(BASE_URL + event_group_href)
    soup = BeautifulSoup(html, "html.parser")
    # Look for the dropdown item with text "Full" that points to /events/.../spread
    for a in soup.find_all("a", class_="dropdown-item"):
        href = a.get("href", "")
        if href.endswith("/spread") and "/events/" in href:
            return href
    return None


def parse_th_text(th):
    """Extract visible text from a <th> element, collapsing whitespace."""
    # Replace <br> with space, then get text
    for br in th.find_all("br"):
        br.replace_with(" ")
    text = th.get_text(separator=" ", strip=True)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_td_text(td):
    """Extract visible text from a <td> element, preserving time values exactly."""
    # For name cells, get the anchor text
    # For time cells, get the span text
    # In all cases, just get the stripped text content
    text = td.get_text(separator="", strip=True)
    return text


def parse_spread_page(html):
    """Parse the spread table and return (headers, rows)."""
    soup = BeautifulSoup(html, "html.parser")

    # Find the main results table
    table = soup.find("table")
    if not table:
        return None, None

    # Parse headers
    thead = table.find("thead")
    if not thead:
        return None, None
    header_row = thead.find("tr")
    headers = [parse_th_text(th) for th in header_row.find_all("th")]

    # Parse data rows
    tbody = table.find("tbody")
    if not tbody:
        return headers, []

    rows = []
    for tr in tbody.find_all("tr"):
        cells = tr.find_all("td")
        row = [parse_td_text(td) for td in cells]
        rows.append(row)

    return headers, rows


def validate_and_save(year, headers, rows, expected_entrants, output_path):
    """Validate results and save to CSV. Returns True if all checks pass."""
    ok = True

    # Validation 1: row count vs expected entrant count
    if len(rows) != expected_entrants:
        print(f"  [MISMATCH] Row count {len(rows)} != expected entrant count {expected_entrants}")
        ok = False
    else:
        print(f"  [OK] Row count {len(rows)} matches expected {expected_entrants} entrants")

    # Validation 2: every row has the same number of columns as header
    num_header_cols = len(headers)
    bad_rows = [(i + 1, len(r)) for i, r in enumerate(rows) if len(r) != num_header_cols]
    if bad_rows:
        print(f"  [MISMATCH] {len(bad_rows)} rows with wrong column count (expected {num_header_cols}):")
        for row_num, col_count in bad_rows[:5]:
            print(f"    Row {row_num}: {col_count} columns")
        ok = False
    else:
        print(f"  [OK] All rows have {num_header_cols} columns")

    # Save CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"  Saved {output_path}")

    return ok, bad_rows


def spot_check(year, headers, rows, html):
    """Spot-check 15 random rows against source HTML."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    tbody = table.find("tbody") if table else None
    if not tbody:
        print("  [SKIP] Cannot spot-check: no tbody found")
        return

    source_rows = tbody.find_all("tr")
    sample_indices = random.sample(range(len(rows)), min(15, len(rows)))
    discrepancies = []

    for idx in sample_indices:
        csv_row = rows[idx]
        src_tr = source_rows[idx]
        src_cells = src_tr.find_all("td")
        src_row = [parse_td_text(td) for td in src_cells]

        for col_idx, (csv_val, src_val) in enumerate(zip(csv_row, src_row)):
            if csv_val != src_val:
                discrepancies.append(
                    f"    Row {idx+1}, col '{headers[col_idx]}': CSV='{csv_val}' vs HTML='{src_val}'"
                )

    if discrepancies:
        print(f"  [SPOT-CHECK FAIL] {len(discrepancies)} discrepancies:")
        for d in discrepancies:
            print(d)
    else:
        print(f"  [OK] Spot-check passed for {min(15, len(rows))} random rows")


def main():
    years = sorted(ORG_DATA.keys())
    results_summary = {}

    for year in years:
        event_group_href, expected_entrants = ORG_DATA[year]
        print(f"\n{'='*60}")
        print(f"Processing {year} (expected {expected_entrants} entrants)")
        print(f"  Event group: {BASE_URL + event_group_href}")

        # Step 1: Get spread URL from event group page
        try:
            spread_href = get_spread_url(event_group_href)
        except Exception as e:
            print(f"  [ERROR] Failed to fetch event group page: {e}")
            results_summary[year] = {"error": str(e)}
            time.sleep(1)
            continue

        if not spread_href:
            print(f"  [ERROR] No spread URL found on event group page")
            results_summary[year] = {"error": "No spread URL found"}
            time.sleep(1)
            continue

        spread_url = BASE_URL + spread_href
        print(f"  Spread URL: {spread_url}")

        # Step 2: Fetch spread page
        try:
            html = fetch_url(spread_url)
        except Exception as e:
            print(f"  [ERROR] Failed to fetch spread page: {e}")
            results_summary[year] = {"error": str(e)}
            time.sleep(1)
            continue

        # Step 3: Parse table
        headers, rows = parse_spread_page(html)
        if headers is None:
            print(f"  [ERROR] Could not parse table")
            results_summary[year] = {"error": "Could not parse table"}
            time.sleep(1)
            continue

        print(f"  Headers ({len(headers)} columns): {headers[:3]}...{headers[-1:]}")
        print(f"  Parsed {len(rows)} data rows")

        # Step 4: Validate and save
        output_path = f"c:/Users/seang/git_projects/bear100splits/{year}.csv"
        ok, bad_rows = validate_and_save(year, headers, rows, expected_entrants, output_path)

        # Step 5: Spot-check
        if rows:
            spot_check(year, headers, rows, html)

        results_summary[year] = {
            "headers": headers,
            "num_cols": len(headers),
            "row_count": len(rows),
            "expected": expected_entrants,
            "row_count_ok": len(rows) == expected_entrants,
            "col_count_ok": len(bad_rows) == 0,
        }

        # Be polite to the server
        time.sleep(0.5)

    # Final report
    print(f"\n{'='*60}")
    print("FINAL REPORT")
    print(f"{'='*60}")
    print(f"Years found: {sorted(results_summary.keys())}")
    print()

    successful = {y: v for y, v in results_summary.items() if "error" not in v}
    failed = {y: v for y, v in results_summary.items() if "error" in v}

    if failed:
        print("FAILED YEARS:")
        for y, v in sorted(failed.items()):
            print(f"  {y}: {v['error']}")
        print()

    print("COLUMN COUNTS BY YEAR:")
    for y in sorted(successful.keys()):
        v = successful[y]
        print(f"  {y}: {v['num_cols']} columns")

    # Find years with identical headers
    print()
    print("YEARS WITH IDENTICAL COLUMN HEADERS:")
    header_groups = {}
    for y, v in successful.items():
        key = tuple(v["headers"])
        header_groups.setdefault(key, []).append(y)

    for i, (key, yrs) in enumerate(sorted(header_groups.items(), key=lambda x: -len(x[1]))):
        if len(yrs) > 1:
            print(f"  Group {i+1} ({len(yrs)} years, {len(key)} cols): {sorted(yrs)}")
            print(f"    Headers: {list(key)[:4]}...{list(key)[-1:]}")
        else:
            print(f"  Unique ({len(key)} cols): {yrs}")


if __name__ == "__main__":
    random.seed(42)
    main()
