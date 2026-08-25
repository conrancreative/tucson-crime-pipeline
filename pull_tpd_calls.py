import os
import json
import time
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

FEATURE_URL = (
    "https://gis.tucsonaz.gov/arcgis/rest/services/"
    "PublicMaps/OpenData_PublicSafety/MapServer/41/query"
)

PAGE_SIZE = 2000


def fetch_page(offset):
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "f": "json",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "orderByFields": "OBJECTID ASC",
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
            objectid = attrs["OBJECTID"]

            cur.execute(
                """
                INSERT INTO raw_tpd_calls_last_45_days
                    (objectid, payload)
                VALUES
                    (%s, %s::jsonb)
                ON CONFLICT (objectid)
                DO UPDATE SET
                    payload = EXCLUDED.payload,
                    pulled_at = now()
                """,
                (objectid, json.dumps(feature)),
            )

        conn.commit()

        total_loaded += len(features)
        offset += PAGE_SIZE

        print(f"Loaded {total_loaded} calls...")
        time.sleep(0.2)

    cur.close()
    conn.close()

    print("Finished loading calls for service")


if __name__ == "__main__":
    main()