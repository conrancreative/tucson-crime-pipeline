"""
Load Tucson City Council ward boundaries into ref_wards (PostGIS).

Source: Pima County GIS open data "Wards - City of Tucson" (WGS84 polygons).
The data is static (6 wards), so run this once; re-run to refresh if the county
updates it. Requires sql/06_ref_wards.sql to have been applied first.

Usage:
    python pull_wards.py
"""

import os
import json
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

WARDS_URL = (
    "https://gisopendata.pima.gov/datasets/"
    "PimaMaps::wards-city-of-tucson.geojson"
)

UPSERT_SQL = """
    insert into ref_wards
        (ward, council_member, office_address, phone, url, city, zipcode, geom, pulled_at)
    values
        (%s, %s, %s, %s, %s, %s, %s,
         -- normalize to a valid MultiPolygon in WGS84 (source mixes Polygon/MultiPolygon)
         st_multi(st_collectionextract(
             st_makevalid(st_setsrid(st_geomfromgeojson(%s), 4326)), 3)),
         now())
    on conflict (ward) do update set
        council_member = excluded.council_member,
        office_address = excluded.office_address,
        phone          = excluded.phone,
        url            = excluded.url,
        city           = excluded.city,
        zipcode        = excluded.zipcode,
        geom           = excluded.geom,
        pulled_at      = now()
"""


def main():
    resp = requests.get(WARDS_URL, timeout=60)
    resp.raise_for_status()
    features = resp.json().get("features", [])

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    loaded = 0
    for feature in features:
        p = feature.get("properties", {})
        ward = str(p.get("WARD") or "").strip()
        if not ward or feature.get("geometry") is None:
            continue
        cur.execute(UPSERT_SQL, (
            ward,
            p.get("NAME"),
            p.get("ADDRESS"),
            p.get("PHONE"),
            p.get("URL"),
            p.get("City"),
            str(p.get("Zipcode") or "") or None,
            json.dumps(feature["geometry"]),
        ))
        loaded += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Loaded {loaded} wards into ref_wards")


if __name__ == "__main__":
    main()
