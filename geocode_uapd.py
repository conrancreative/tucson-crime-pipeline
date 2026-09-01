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
import re
import time
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
DELAY = 0.15   # polite pacing for the free service

_ORD = {"1": "1ST", "2": "2ND", "3": "3RD"}
_SUFFIX = {"AVENUE": "AVE", "AV": "AVE", "BOULEVARD": "BLVD", "BL": "BLVD",
           "STREET": "ST", "DRIVE": "DR", "ROAD": "RD", "PLACE": "PL",
           "LANE": "LN", "WY": "WAY"}


def normalize(address):
    """Canonicalize an address (mirrors SQL uapd_norm_addr): drop punctuation,
    standardize suffixes, add ordinal street suffixes. Boosts Census hit rate."""
    s = re.sub(r"\s+", " ", re.sub(r"[.,]", "", address.upper())).strip()
    s = " ".join(_SUFFIX.get(w, w) for w in s.split())
    # ordinal street names before a suffix: "6 ST" -> "6TH ST"
    def ordn(m):
        n = m.group(1)
        return f"{_ORD.get(n, n + 'TH')} {m.group(2)}"
    return re.sub(r"\b(\d{1,2}) (ST|AVE)\b", ordn, s)


def geocode(address):
    """Return (lat, lon, matched_address) or (None, None, None). Tries the raw
    address, then a normalized form if that misses."""
    candidates = [address]
    norm = normalize(address)
    if norm != address:
        candidates.append(norm)
    for q in candidates:
        try:
            resp = requests.get(CENSUS_URL, params={
                "address": f"{q}, Tucson, AZ",
                "benchmark": "Public_AR_Current", "format": "json"}, timeout=30)
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
