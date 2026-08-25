import os
import json
import time
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

FEATURE_URL = (
    "https://services3.arcgis.com/9coHY2fvuFjG9HQX/"
    "ArcGIS/rest/services/Tucson_Police_Reported_Crimes/"
    "FeatureServer/8/query"
)

PAGE_SIZE = 2000


def fetch_page(offset):
    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "json",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "orderByFields": "ESRI_OID ASC",
    }

    response = requests.get(FEATURE_URL, params=params, timeout=60)
    response.raise_for_status()

    return response.json().get("features", [])


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    offset = 0
    total_loaded = 0

    while True:
        features = fetch_page(offset)

        if not features:
            break

        for feature in features:
            attrs = feature["attributes"]
            esri_oid = attrs["ESRI_OID"]

            cur.execute(
                """
                INSERT INTO raw_tpd_reported_crimes
                (esri_oid, payload)
                VALUES (%s, %s::jsonb)

                ON CONFLICT (esri_oid)
                DO UPDATE SET
                    payload = EXCLUDED.payload,
                    pulled_at = now()
                """,
                (esri_oid, json.dumps(feature)),
            )

        conn.commit()

        total_loaded += len(features)
        offset += PAGE_SIZE

        print(f"Loaded {total_loaded} records")

        time.sleep(0.2)

    cur.close()
    conn.close()

    print("Finished loading data")


if __name__ == "__main__":
    main()