"""
Load Tucson neighborhood polygons into ref_neighborhoods (PostGIS).

Source: City of Tucson GIS "NEIGHBORHOODS_ALL" (registered neighborhood
associations + named unaffiliated areas), requested as WGS84 GeoJSON. Used to
fill the police-team codes / blanks in historical neighborhood labels (see
sql/17_ref_neighborhoods.sql). Boundaries change rarely, so run this once;
re-run to refresh. Requires sql/17_ref_neighborhoods.sql applied first.

Only NAME, WARD and CITY_NHA are loaded. The layer also carries association
officers' names, phones and emails, which are deliberately NOT stored.

Usage:
    python pull_neighborhoods.py
"""

import os
import json
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

NEIGHBORHOODS_URL = (
    "https://gis.tucsonaz.gov/arcgis/rest/services/"
    "PublicMaps/NeighborhoodsPlans/MapServer/11/query"
)
PARAMS = {
    "where": "1=1",
    "outFields": "OBJECTID,NAME,WARD,CITY_NHA",  # no officer contact fields
    "outSR": 4326,
    "f": "geojson",
}

UPSERT_SQL = """
    insert into ref_neighborhoods
        (objectid, name, ward, is_registered_nha, geom, pulled_at)
    values
        (%s, %s, %s, %s,
         -- normalize to a valid MultiPolygon in WGS84
         st_multi(st_collectionextract(
             st_makevalid(st_setsrid(st_geomfromgeojson(%s), 4326)), 3)),
         now())
    on conflict (objectid) do update set
        name              = excluded.name,
        ward              = excluded.ward,
        is_registered_nha = excluded.is_registered_nha,
        geom              = excluded.geom,
        pulled_at         = now()
"""


def main():
    resp = requests.get(NEIGHBORHOODS_URL, params=PARAMS, timeout=120)
    resp.raise_for_status()
    features = resp.json().get("features", [])
    if not features:
        raise SystemExit("No features returned; leaving ref_neighborhoods untouched")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    loaded, ids = 0, []
    for feature in features:
        p = feature.get("properties", {})
        # source names can carry stray whitespace ("Palo Verde ")
        name = (p.get("NAME") or "").strip()
        if not name or feature.get("geometry") is None:
            continue
        cur.execute(UPSERT_SQL, (
            p["OBJECTID"],
            name,
            str(p.get("WARD") or "").strip() or None,
            (p.get("CITY_NHA") or "").strip().lower() == "yes",
            json.dumps(feature["geometry"]),
        ))
        ids.append(p["OBJECTID"])
        loaded += 1

    # drop polygons the source no longer publishes
    cur.execute("delete from ref_neighborhoods where objectid <> all(%s)", (ids,))
    removed = cur.rowcount
    conn.commit()

    # the bike mart reads these polygons, so refresh it (skip if not built yet)
    try:
        cur.execute("refresh materialized view mart_bike_crimes")
        conn.commit()
        print("  refreshed mart_bike_crimes")
    except psycopg2.Error:
        conn.rollback()

    cur.close()
    conn.close()
    print(f"Loaded {loaded} neighborhoods into ref_neighborhoods ({removed} removed)")


if __name__ == "__main__":
    main()
