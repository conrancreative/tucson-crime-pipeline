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


def load_layer(cur, conn, layer, label):
    offset = 0
    loaded = 0
    while True:
        features, more = fetch_page(layer, offset)
        if not features:
            break

        for feature in features:
            attrs = feature["attributes"]
            inci_id = attrs.get("INCI_ID")
            if not inci_id:
                continue
            feature = clean_geometry(feature)
            cur.execute(
                """
                INSERT INTO raw_tpd_incidents (inci_id, source_layer, payload)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (inci_id)
                DO UPDATE SET
                    source_layer = EXCLUDED.source_layer,
                    payload      = EXCLUDED.payload,
                    pulled_at    = now()
                """,
                (str(inci_id), label, json.dumps(feature)),
            )

        conn.commit()
        loaded += len(features)
        offset += PAGE_SIZE
        print(f"  [{label}] loaded {loaded}")

        if not more and len(features) < PAGE_SIZE:
            break
        time.sleep(0.2)

    return loaded


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
    conn.close()
    print(f"Done ({mode}). Rows processed: {total}")


if __name__ == "__main__":
    main()
