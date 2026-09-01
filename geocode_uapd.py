"""
Geocode UAPD log addresses -> lat/lon, cached in geocode_cache.

Uses the U.S. Census geocoder (free, no API key; handles street addresses AND
intersections). Geocodes every DISTINCT address in raw_uapd_log that isn't
cached yet -- all of them, for broad coverage, not just bike-related. Each
address is geocoded once; the daily run only handles new ones.

Requires sql/09_uapd.sql and sql/10_geocode.sql applied first.

Usage:
    python geocode_uapd.py
"""

import os
import time
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
DELAY = 0.15   # polite pacing for the free service


def geocode(address):
    """Return (lat, lon, matched_address) or (None, None, None)."""
    params = {
        "address": f"{address}, Tucson, AZ",
        "benchmark": "Public_AR_Current",
        "format": "json",
    }
    try:
        resp = requests.get(CENSUS_URL, params=params, timeout=30)
        resp.raise_for_status()
        matches = resp.json()["result"]["addressMatches"]
        if matches:
            c = matches[0]["coordinates"]
            return c["y"], c["x"], matches[0]["matchedAddress"]
    except Exception:
        pass
    return None, None, None


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        select distinct address
        from raw_uapd_log
        where address is not null and address <> ''
          and address not in (select address from geocode_cache)
    """)
    todo = [r[0] for r in cur.fetchall()]
    print(f"{len(todo)} new addresses to geocode")

    for i, addr in enumerate(todo, 1):
        lat, lon, matched = geocode(addr)
        cur.execute("""
            insert into geocode_cache (address, lat, lon, matched_address)
            values (%s, %s, %s, %s)
            on conflict (address) do nothing
        """, (addr, lat, lon, matched))
        conn.commit()
        if i % 100 == 0:
            print(f"  geocoded {i}/{len(todo)}")
        time.sleep(DELAY)

    cur.execute("select count(*) filter (where lat is not null), count(*) from geocode_cache")
    hit, tot = cur.fetchone()
    print(f"Done. Cache now holds {tot} addresses; {hit} matched to coordinates.")

    # rebuild the UA bike mart now that new addresses have coordinates
    try:
        cur.execute("refresh materialized view concurrently mart_uapd_bike")
        conn.commit()
        print("Refreshed mart_uapd_bike.")
    except psycopg2.Error:
        conn.rollback()
        try:
            cur.execute("refresh materialized view mart_uapd_bike")
            conn.commit()
            print("Refreshed mart_uapd_bike.")
        except psycopg2.Error as e:
            conn.rollback()
            print(f"  (mart_uapd_bike refresh skipped: {e})")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
