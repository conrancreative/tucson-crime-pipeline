"""Mirror PAG's Tucson Metro Bike Map bikeway network into raw_pag_bikeways.

Source: TucsonMetroBikeMapVecLive FeatureServer, layer 4 (Bikeways).
Loads the full GeoJSON features, including WGS84 line geometry, then replaces
the dedicated snapshot table in one transaction. The preview views are defined
in sql/18_pag_bikeways.sql and are not used by the public-facing site.

Usage:
    python pull_pag_bikeways.py
"""

import json
import os
import sys
import time

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
LAYER_URL = (
    "https://maps.pagregion.com/server/rest/services/"
    "TucsonMetroBikeMapVecLive/FeatureServer/4"
)
PAGE_SIZE = 2000  # ArcGIS layer maxRecordCount


def arcgis_get(session, url, params):
    """GET a public ArcGIS REST resource with a few retries for transient errors."""
    last_error = None
    for attempt in range(3):
        try:
            response = session.get(url, params=params, timeout=90)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise RuntimeError(f"ArcGIS error: {data['error']}")
            return data
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"ArcGIS request failed after retries: {last_error}")


def fetch_features(session):
    """Fetch the complete source snapshot in deterministic OBJECTID order."""
    count_data = arcgis_get(session, f"{LAYER_URL}/query", {
        "where": "1=1",
        "returnCountOnly": "true",
        "f": "json",
    })
    expected = int(count_data["count"])
    features = []
    for offset in range(0, expected, PAGE_SIZE):
        data = arcgis_get(session, f"{LAYER_URL}/query", {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": 4326,
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "orderByFields": "OBJECTID ASC",
            "f": "geojson",
        })
        page = data.get("features", [])
        if not page:
            raise RuntimeError(f"Empty ArcGIS page at offset {offset} of {expected}")
        features.extend(page)
        print(f"  fetched {len(features)}/{expected} features")

    ids = [feature.get("properties", {}).get("OBJECTID") for feature in features]
    if len(features) != expected or None in ids or len(set(ids)) != expected:
        raise RuntimeError(
            f"Incomplete or duplicate source result: expected {expected}, got {len(features)}"
        )
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry or geometry.get("type") not in ("LineString", "MultiLineString"):
            raise RuntimeError(
                f"Feature {feature['properties']['OBJECTID']} has no usable line geometry"
            )
    return features


def replace_snapshot(conn, features):
    """Atomically replace only our dedicated staging table with the full snapshot."""
    rows = [(
        int(feature["properties"]["OBJECTID"]),
        json.dumps(feature),
        json.dumps(feature["geometry"]),
    ) for feature in features]
    cur = conn.cursor()
    try:
        # The surrounding transaction makes the delete+reload atomic. Any insert
        # or geometry error rolls back and keeps the previous snapshot intact.
        cur.execute("delete from raw_pag_bikeways")
        execute_values(cur, """
            insert into raw_pag_bikeways (objectid, payload, geom)
            values %s
        """, rows, template=(
            "(%s, %s::jsonb, "
            "st_multi(st_setsrid(st_geomfromgeojson(%s), 4326)))"
        ), page_size=500)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def main():
    if not DATABASE_URL:
        sys.exit("DATABASE_URL is required")

    session = requests.Session()
    session.headers.update({"User-Agent": "Tucson bike crime data pipeline"})
    print("Fetching PAG bikeways (FeatureServer layer 4) ...")
    features = fetch_features(session)

    conn = psycopg2.connect(DATABASE_URL)
    try:
        replace_snapshot(conn, features)
    finally:
        conn.close()
        session.close()
    print(f"Done. Replaced raw_pag_bikeways with {len(features)} features.")


if __name__ == "__main__":
    main()
