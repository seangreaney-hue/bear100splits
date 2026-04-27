"""Screenshot dashboard pages at mobile + desktop viewports for visual validation.

One-time setup:
    pip install playwright
    playwright install chromium

Typical use (Streamlit must already be running):
    streamlit run dashboard/app.py --server.port 8502 --server.headless true
    python scripts/screenshot_charts.py

Output goes to scripts/screenshots/ as PNGs the agent (or human) can inspect.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


VIEWPORTS = {
    # Heights are intentionally tall: Streamlit's stMain section has internal
    # scroll, so shrinking height clips the screenshot. Width is what we care
    # about for responsive testing.
    "mobile": {"width": 390, "height": 6500},   # iPhone 13/14 width
    "desktop": {"width": 1440, "height": 6500},
}

DEFAULT_PAGES = {
    "data-notes": "/",
    "home": "/Home",
}


def screenshot(base_url: str, page_path: str, viewport_name: str, out_dir: Path) -> Path:
    viewport = VIEWPORTS[viewport_name]
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = page_path.strip("/").replace("/", "_") or "root"
    out_path = out_dir / f"{safe_name}__{viewport_name}.png"

    full_url = base_url.rstrip("/") + page_path

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=viewport, device_scale_factor=2)
        page = context.new_page()
        page.goto(full_url, wait_until="domcontentloaded", timeout=60_000)

        # Wait for at least one Plotly chart to render. Streamlit + Plotly are async.
        try:
            page.wait_for_selector("div.js-plotly-plot", timeout=30_000)
        except Exception:
            print(f"[warn] no Plotly chart detected at {full_url}", file=sys.stderr)

        # Streamlit content lives inside section[data-testid="stMain"] which
        # has its own scrollHeight. Scroll inside that container to mount all
        # charts, then screenshot the section element directly.
        page.evaluate(
            """
            async () => {
                const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
                const main = document.querySelector('section[data-testid="stMain"]');
                if (!main) return;
                let last = -1;
                while (true) {
                    main.scrollTo(0, main.scrollHeight);
                    await sleep(800);
                    if (main.scrollHeight === last) break;
                    last = main.scrollHeight;
                }
                main.scrollTo(0, 0);
                await sleep(500);
            }
            """
        )
        time.sleep(3)
        page.screenshot(path=str(out_path), full_page=True)
        browser.close()

    return out_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8502")
    parser.add_argument("--out", default="scripts/screenshots")
    parser.add_argument(
        "--pages",
        nargs="+",
        default=list(DEFAULT_PAGES),
        choices=list(DEFAULT_PAGES),
        help="Which pages to screenshot.",
    )
    parser.add_argument(
        "--viewports",
        nargs="+",
        default=list(VIEWPORTS),
        choices=list(VIEWPORTS),
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    for page_name in args.pages:
        page_path = DEFAULT_PAGES[page_name]
        for vp in args.viewports:
            path = screenshot(args.base_url, page_path, vp, out_dir)
            print(f"[ok] {page_name:11s} {vp:7s} -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
