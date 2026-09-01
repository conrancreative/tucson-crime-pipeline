"""
Pull geo-enabled bicycle-theft incidents from Tucson PD's spatial ArcGIS layers.

Why this exists: the dashboard table (FeatureServer/8) that pull_tpd_crime.py
uses has NO geometry. These TPD_INCIDENTS_PUBLIC_* layers are the SAME incidents
(same INCI_ID / OFFENSE coding) but WITH point geometry + address + neighborhood.

Two modes:
  * backfill  -> loops the per-year history layers (2018-2025) + current.  Run once.
  * refresh   -> pulls only the 45-day layer.  Run on a schedule (e.g. daily).
Both upsert on INCI_ID into raw_tpd_incidents, so history keeps accumulating.

Usage:
    python pull_tpd_incidents.py backfill
    python pull_tpd_incidents.py refresh     # default if no arg
"""

import os
import sys
import json
import time
import math
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

BASE = (
    "https://gis.tucsonaz.gov/arcgis/rest/services/"
    "PublicMaps/OpenData_PublicSafety/MapServer"
)

# ArcGIS layer ids (verified from the service metadata)
HISTORY_LAYERS = {
    "2018": 40, "2019": 48, "2020": 54, "2021": 69,
    "2022": 71, "2023": 78, "2024": 80, "2025": 81,
}
LAST45_LAYER = 42    # TUCSON_INCIDENTS_PUBLIC_45D (rich schema: DATETIME_OCCU, parcel, census)

# NOTE: layer 24 (TPD_INCIDENTS_PUBLIC "current") is deliberately EXCLUDED.
# It lacks DATETIME_OCCU + parcel/census fields, and being pulled last it would
# overwrite the richer last45/year-layer payloads on INCI_ID conflict. last45
# already covers the freshest ~45 days with the full schema.

# What counts as "bike". Widen here to add categories (kept server-side = tiny pulls).
WHERE = "OFFENSE='0606'"          # 0606 == 'Larceny - Bicycles'

PAGE_SIZE = 2000                  # == layer maxRecordCount


def clean_geometry(feature):
    """ArcGIS emits literal NaN for un-geocoded points, which is invalid JSON for
    Postgres jsonb. Null it out so the row still loads (lat/lon just come back NULL)."""
    geom = feature.get("geometry")
    if geom:
        try:
            x = float(geom.get("x"))
            y = float(geom.get("y"))
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError
            feature["geometry"] = {"x": x, "y": y}
        except (TypeError, ValueError):
            feature["geometry"] = None
    return feature


def fetch_page(layer, offset):
    params = {
        "where": WHERE,
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": 4326,                 # WGS84 lon/lat, ready for Leaflet
        "f": "json",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "orderByFields": "OBJECTID ASC",
    }
    resp = requests.get(f"{BASE}/{layer}/query", params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ArcGIS error on layer {layer}: {data['error']}")
    return data.get("features", []), data.get("exceededTransferLimit", False)


UPSERT_SQL = """
    INSERT INTO raw_tpd_incidents (inci_id, source_layer, payload)
    VALUES %s
    ON CONFLICT (inci_id) DO UPDATE SET
        source_layer = EXCLUDED.source_layer,
        payload      = EXCLUDED.payload,
        pulled_at    = now()
"""


def load_layer(cur, conn, layer, label):
    offset = 0
    loaded = 0
    while True:
        features, more = fetch_page(layer, offset)
        if not features:
            break

        # Build the whole page, then upsert it in ONE round-trip (execute_values).
        # Per-row inserts are fine locally but crawl over a remote pooler.
        # Dedupe by inci_id within the page (some layers repeat an id) -- a single
        # ON CONFLICT statement can't update the same row twice; keep the last.
        page = {}
        for feature in features:
            inci_id = feature["attributes"].get("INCI_ID")
            if not inci_id:
                continue
            feature = clean_geometry(feature)
            page[str(inci_id)] = (str(inci_id), label, json.dumps(feature))

        if page:
            execute_values(cur, UPSERT_SQL, list(page.values()),
                           template="(%s, %s, %s::jsonb)", page_size=1000)
            conn.commit()

        loaded += len(features)
        offset += PAGE_SIZE
        print(f"  [{label}] loaded {loaded}")

        if not more and len(features) < PAGE_SIZE:
            break
        time.sleep(0.2)

    return loaded


def refresh_marts(conn):
    """Re-bake the public materialized views so new data becomes visible.
    Tries CONCURRENTLY (no read lock); falls back to a plain refresh. Skips
    silently if the marts don't exist yet (e.g. before 04_reporting.sql is run)."""
    for mv in ("mart_bike_crimes", "mart_bike_stats"):
        cur = conn.cursor()
        try:
            cur.execute(f"refresh materialized view concurrently {mv}")
            conn.commit()
            print(f"  refreshed {mv} (concurrently)")
        except psycopg2.Error:
            conn.rollback()
            try:
                cur.execute(f"refresh materialized view {mv}")
                conn.commit()
                print(f"  refreshed {mv}")
            except psycopg2.Error as e:
                conn.rollback()
                print(f"  skipped {mv}: {str(e).strip()}")
        finally:
            cur.close()


def source_freshness():
    """Newest crime of ANY type in the 45-day layer (a denser freshness signal
    than sparse bike thefts) + how many crimes it currently holds.
    Returns (occurred_ms, reported_ms, count)."""
    params = {
        "where": "1=1",
        "outStatistics": json.dumps([
            {"statisticType": "max", "onStatisticField": "DATETIME_OCCU", "outStatisticFieldName": "occ"},
            {"statisticType": "max", "onStatisticField": "DATETIME_REPT", "outStatisticFieldName": "rep"},
            {"statisticType": "count", "onStatisticField": "OBJECTID", "outStatisticFieldName": "n"},
        ]),
        "f": "json",
    }
    resp = requests.get(f"{BASE}/{LAST45_LAYER}/query", params=params, timeout=60)
    resp.raise_for_status()
    a = resp.json()["features"][0]["attributes"]
    return a.get("occ"), a.get("rep"), a.get("n")


def log_run(conn, mode, bikes_processed):
    """Record this run's freshness into ingest_runs. Best-effort — never fail the
    pull over logging (e.g. if 07_ingest_log.sql hasn't been applied yet)."""
    try:
        occ, rep, n = source_freshness()
        cur = conn.cursor()
        cur.execute(
            """
            insert into ingest_runs
                (mode, bikes_processed, source_45d_count,
                 source_latest_occurred, source_latest_reported, our_latest_bike)
            values (%s, %s, %s, to_timestamp(%s), to_timestamp(%s),
                to_timestamp((select max((payload->'attributes'->>'DATETIME_OCCU')::bigint / 1000.0)
                   from raw_tpd_incidents)))
            """,
            (mode, bikes_processed, n,
             occ / 1000.0 if occ else None, rep / 1000.0 if rep else None),
        )
        conn.commit()
        cur.close()
        print(f"Freshness logged (45-day layer holds {n} crimes of all types).")
    except Exception as e:
        conn.rollback()
        print(f"  (freshness log skipped: {e})")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "refresh"

    if mode == "backfill":
        targets = [(lid, f"y{yr}") for yr, lid in HISTORY_LAYERS.items()]
        targets.append((LAST45_LAYER, "last45"))
    elif mode == "refresh":
        targets = [(LAST45_LAYER, "last45")]
    else:
        sys.exit("usage: python pull_tpd_incidents.py [backfill|refresh]")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    total = 0
    for layer, label in targets:
        print(f"Pulling layer {layer} ({label}) ...")
        total += load_layer(cur, conn, layer, label)
    cur.close()

    print("Refreshing marts ...")
    refresh_marts(conn)

    log_run(conn, mode, total)

    conn.close()
    print(f"Done ({mode}). Rows processed: {total}")


if __name__ == "__main__":
    main()
