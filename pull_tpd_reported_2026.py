"""
Pull 2026 reported bicycle thefts from TPD's ReportedCrimes2026 open-data layer.

Source: services3.arcgis.com/.../TPDOpenDataReportedCrimes2026/FeatureServer/0 --
the complete + fresh 2026 reported-crimes layer (geometry, ward, neighborhood,
block address). Replaces the incomplete 45-day incidents layer as the 2026 source
(the 45-day layer is kept only as a stored backup).

The source has one row per person/role, so we key on IncidentNumber to store one
row per incident. Offense 0606 == 'Larceny - Bicycles'. Run daily.

Usage:
    python pull_tpd_reported_2026.py
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

SVC = ("https://services3.arcgis.com/9coHY2fvuFjG9HQX/arcgis/rest/services/"
       "TPDOpenDataReportedCrimes2026/FeatureServer/0")
WHERE = "Offense='0606'"          # 0606 == Larceny - Bicycles
PAGE_SIZE = 2000

UPSERT_SQL = """
    insert into raw_tpd_reported_2026 (incident_number, payload)
    values %s
    on conflict (incident_number) do update set
        payload   = excluded.payload,
        pulled_at = now()
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
        "where": WHERE, "outFields": "*", "returnGeometry": "true", "outSR": 4326,
        "f": "json", "resultOffset": offset, "resultRecordCount": PAGE_SIZE,
        "orderByFields": "OBJECTID ASC",
    }
    resp = requests.get(f"{SVC}/query", params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ArcGIS error: {data['error']}")
    return data.get("features", []), data.get("exceededTransferLimit", False)


def refresh_marts(conn):
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


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    offset = 0
    loaded = 0
    while True:
        features, more = fetch_page(offset)
        if not features:
            break
        # one row per person/role in the source -> dedupe to one per incident
        page = {}
        for feature in features:
            num = feature["attributes"].get("IncidentNumber")
            if not num:
                continue
            feature = clean_geometry(feature)
            page[str(num)] = (str(num), json.dumps(feature))
        if page:
            execute_values(cur, UPSERT_SQL, list(page.values()),
                           template="(%s, %s::jsonb)", page_size=1000)
            conn.commit()
        loaded += len(features)
        offset += PAGE_SIZE
        print(f"  loaded {loaded} rows")
        if not more and len(features) < PAGE_SIZE:
            break
        time.sleep(0.2)

    cur.close()
    print("Refreshing marts ...")
    refresh_marts(conn)
    conn.close()
    print(f"Done. Rows processed: {loaded}")


if __name__ == "__main__":
    main()
