"""Import every PAG Tucson Metro Bike Map layer except Bikeways (layer 4).

Layer 4 is loaded by pull_pag_bikeways.py. This script loads the remaining
PAG layers plus the legacy Tugo station layer that accompanies the map. Each
complete source GeoJSON feature is retained in raw_pag_bikemap_features.
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
PAG_URL = (
    "https://maps.pagregion.com/server/rest/services/"
    "TucsonMetroBikeMapVecLive/FeatureServer"
)
TUGO_MAP_LAYER_URL = (
    "https://services1.arcgis.com/Ezk9fcjSUkeadg6u/ArcGIS/rest/services/"
    "Transportation_in_Tucson_WFL1/FeatureServer"
)
PAGE_SIZE = 2000


def arcgis_get(session, url, params):
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


def fetch_layer(session, source_key, base_url, layer_id):
    metadata = arcgis_get(session, f"{base_url}/{layer_id}", {"f": "json"})
    layer_name = metadata["name"]
    oid_field = metadata.get("objectIdField") or metadata.get("objectIdFieldName")
    if not oid_field:
        oid_field = next(
            (f["name"] for f in metadata.get("fields", []) if f.get("type") == "esriFieldTypeOID"),
            None,
        )
    if not oid_field:
        raise RuntimeError(f"No object id field for {source_key}/{layer_id}")

    query_url = f"{base_url}/{layer_id}/query"
    count_data = arcgis_get(session, query_url, {
        "where": "1=1", "returnCountOnly": "true", "f": "json",
    })
    expected = int(count_data["count"])
    features = []
    for offset in range(0, expected, PAGE_SIZE):
        data = arcgis_get(session, query_url, {
            "where": "1=1", "outFields": "*", "returnGeometry": "true",
            "outSR": 4326, "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "orderByFields": f"{oid_field} ASC", "f": "geojson",
        })
        page = data.get("features", [])
        if not page:
            raise RuntimeError(f"Empty page for {layer_name} at offset {offset}")
        features.extend(page)
        print(f"  {source_key}/{layer_id} {layer_name}: {len(features)}/{expected}")

    ids = [f.get("properties", {}).get(oid_field) for f in features]
    if len(features) != expected or None in ids or len(set(map(str, ids))) != expected:
        raise RuntimeError(
            f"Incomplete or duplicate {source_key}/{layer_id}: expected {expected}, got {len(features)}"
        )

    return [(
        source_key,
        int(layer_id),
        layer_name,
        str(feature["properties"][oid_field]),
        json.dumps(feature),
        json.dumps(feature["geometry"]) if feature.get("geometry") else None,
        json.dumps(feature["geometry"]) if feature.get("geometry") else None,
    ) for feature in features]


def fetch_all(session):
    rows = []
    sources = [
        ("pag_tucson_bikemap", PAG_URL, (0, 1, 2, 3, 5, 6)),
        ("tugo_arcgis_legacy", TUGO_MAP_LAYER_URL, (2,)),
    ]
    for source_key, base_url, layer_ids in sources:
        for layer_id in layer_ids:
            rows.extend(fetch_layer(session, source_key, base_url, layer_id))
    return rows


def replace_snapshot(conn, rows):
    cur = conn.cursor()
    try:
        cur.execute("delete from raw_pag_bikemap_features")
        execute_values(cur, """
            insert into raw_pag_bikemap_features
                (source_key, layer_id, layer_name, object_id, payload, geom)
            values %s
        """, rows, template=(
            "(%s, %s, %s, %s, %s::jsonb, "
            "case when %s is null then null else st_setsrid(st_geomfromgeojson(%s), 4326) end)"
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
    session.headers.update({"User-Agent": "Tucson bike infrastructure data pipeline"})
    print("Fetching PAG ancillary layers and Tugo's map station layer ...")
    rows = fetch_all(session)
    conn = psycopg2.connect(DATABASE_URL)
    try:
        replace_snapshot(conn, rows)
    finally:
        conn.close()
        session.close()
    print(f"Done. Replaced raw_pag_bikemap_features with {len(rows)} features.")


if __name__ == "__main__":
    main()
