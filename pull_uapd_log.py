"""
Scrape the UAPD Daily Crime Log into raw_uapd_log.

Source: https://uapd.arizona.edu/public-information/uapd-daily-activity-log
A static, server-rendered HTML table paginated with ?page=N (20 rows/page,
~2008 pages back to Apr 2022). No coordinates -- street address only.

Modes:
  backfill  -> every page (0..last). Run once; ~15 min.
  refresh   -> newest pages, stopping once a whole page is already in our DB.
               Run daily to append new reports + refresh changed dispositions.

Upserts on case_number.

Usage:
    python pull_uapd_log.py backfill
    python pull_uapd_log.py refresh     # default if no arg
"""

import os
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

URL = "https://uapd.arizona.edu/public-information/uapd-daily-activity-log"
HEADERS = {"User-Agent": "tucson-bike-crime-map research scraper"}
DELAY = 0.4          # be polite to the .edu server
MAX_PAGES = 2200     # safety cap (last real page is ~2007)

UPSERT_SQL = """
    insert into raw_uapd_log
        (case_number, report_dt, offense_dt, nature, address, disposition)
    values %s
    on conflict (case_number) do update set
        report_dt   = excluded.report_dt,
        offense_dt  = excluded.offense_dt,
        nature      = excluded.nature,
        address     = excluded.address,
        disposition = excluded.disposition,
        scraped_at  = now()
"""


def parse_dt(s):
    """'08/30/2026 - 2:07pm' -> datetime (Arizona local). Tolerates blanks."""
    s = (s or "").strip()
    if not s:
        return None
    s = s.replace("am", "AM").replace("pm", "PM")
    for fmt in ("%m/%d/%Y - %I:%M%p", "%m/%d/%Y - %I%p", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def scrape_page(page):
    """Return list of row tuples for one page (empty list past the last page)."""
    resp = requests.get(URL, params={"page": page}, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    table = BeautifulSoup(resp.text, "html.parser").find("table")
    if not table:
        return []
    rows = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 6:
            continue
        c = [td.get_text(" ", strip=True) for td in tds]
        case = c[0].strip()
        if not case:
            continue
        rows.append((case, parse_dt(c[1]), parse_dt(c[2]),
                     c[3] or None, c[4] or None, c[5] or None))
    return rows


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "refresh"
    if mode not in ("backfill", "refresh"):
        sys.exit("usage: python pull_uapd_log.py [backfill|refresh]")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    known = set()
    if mode == "refresh":
        cur.execute("select case_number from raw_uapd_log")
        known = {r[0] for r in cur.fetchall()}

    page = 0
    total = 0
    while page < MAX_PAGES:
        rows = scrape_page(page)
        if not rows:
            break

        execute_values(cur, UPSERT_SQL, rows, page_size=100)
        conn.commit()
        total += len(rows)
        print(f"  page {page}: {len(rows)} rows (total {total})")

        if mode == "refresh":
            page_cases = {r[0] for r in rows}
            if page_cases <= known:      # whole page already known -> caught up
                print("  reached already-known data; stopping.")
                break

        page += 1
        time.sleep(DELAY)

    cur.close()
    conn.close()
    print(f"Done ({mode}). Rows processed: {total}")


if __name__ == "__main__":
    main()
