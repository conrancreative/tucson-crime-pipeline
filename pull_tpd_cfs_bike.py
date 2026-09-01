"""
Pull bike-related Calls-For-Service into raw_tpd_cfs_bike.

Source: TUCSON_CFS_PUBLIC_45D (layer 41) on Tucson's OpenData_PublicSafety
MapServer -- near-real-time dispatch events (~2-day lag), rolling 45 days.
Filtered to bike-related nature codes (theft calls, bike traffic, injury crashes).

CFS has no year-split history layers, so there's no deep backfill: we pull the
current 45-day window and upsert on call_id, accumulating history over time.
Requires sql/08_cfs_bike.sql applied first.

Usage:
    python pull_tpd_cfs_bike.py
"""

import os
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
CFS_LAYER = 41

# All bike-related nature codes come through this one filter.
WHERE = "UPPER(NatureCodeDesc) LIKE '%BICY%' OR UPPER(NatureCodeDesc) LIKE '%BIKE%'"

PAGE_SIZE = 2000

UPSERT_SQL = """
    insert into raw_tpd_cfs_bike (call_id, nature_code, payload)
    values %s
    on conflict (call_id) do update set
        nature_code = excluded.nature_code,
        payload     = excluded.payload,
        pulled_at   = now()
"""


def clean_geometry(feature):
    geom = feature.get("geometry")
    if geom:
        try:
            x, y = float(geom.get("x")), float(geom.get("y"))
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError
            feature["geometry"] = {"x": x, "y": y}
        except (TypeError, ValueError):
            feature["geometry"] = None
    return feature


def fetch_page(offset):
    params = {
        "where": WHERE,
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": 4326,
        "f": "json",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "orderByFields": "OBJECTID ASC",
    }
    resp = requests.get(f"{BASE}/{CFS_LAYER}/query", params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ArcGIS error: {data['error']}")
    return data.get("features", []), data.get("exceededTransferLimit", False)


def refresh_marts(conn):
    for mv in ("mart_bike_theft_calls", "mart_bike_traffic", "mart_bike_crashes"):
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


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    offset = 0
    loaded = 0
    while True:
        features, more = fetch_page(offset)
        if not features:
            break

        # dedupe by call_id within the page (a single ON CONFLICT can't touch a row twice)
        page = {}
        for feature in features:
            call_id = feature["attributes"].get("call_id")
            if not call_id:
                continue
            nature = feature["attributes"].get("NatureCodeDesc")
            feature = clean_geometry(feature)
            page[str(call_id)] = (str(call_id), nature, json.dumps(feature))

        if page:
            execute_values(cur, UPSERT_SQL, list(page.values()),
                           template="(%s, %s, %s::jsonb)", page_size=1000)
            conn.commit()

        loaded += len(features)
        offset += PAGE_SIZE
        print(f"  loaded {loaded}")
        if not more and len(features) < PAGE_SIZE:
            break
        time.sleep(0.2)

    cur.close()
    print("Refreshing CFS marts ...")
    refresh_marts(conn)
    conn.close()
    print(f"Done. CFS bike rows processed: {loaded}")


if __name__ == "__main__":
    main()
