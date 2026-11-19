"""Import complete PAG traffic-stress and Tucson road-context snapshots.

Apply sql/20_roadway_context.sql first. Uses DATABASE_URL from .env.
All six layers are fetched and validated before the local snapshot is replaced.
"""

import json
import os
import sys
from contextlib import closing
from datetime import datetime, timezone

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values

from pull_pag_bikemap_layers import arcgis_get, fetch_layer

load_dotenv()

PAG_STRESS = "https://maps.pagregion.com/server/rest/services/RATP/Level_of_Traffic_Stress/MapServer"
CITY_SERVICES = "https://services3.arcgis.com/9coHY2fvuFjG9HQX/arcgis/rest/services/"
SOURCES = [
    ("pag_bicycle_lts", PAG_STRESS, (7, 8, 9, 10)),
    ("tucson_speed_limits", CITY_SERVICES + "Speed_Limits/FeatureServer", (9,)),
    (
        "move_tucson_classification",
        CITY_SERVICES + "Move_Tucson_Street_Types_with_Federal_Functional_Classification/FeatureServer",
        (0,),
    ),
]


def fetch_all(session):
    rows = []
    snapshots = []
    for source_key, base_url, layer_ids in SOURCES:
        for layer_id in layer_ids:
            url = f"{base_url}/{layer_id}"
            metadata = arcgis_get(session, url, {"f": "json"})
            features = fetch_layer(session, source_key, base_url, layer_id)
            if not features:
                raise RuntimeError(f"Refusing an empty roadway layer: {url}")
            for row in features:
                geometry = json.loads(row[5]) if row[5] else None
                if not geometry or geometry.get("type") not in ("LineString", "MultiLineString"):
                    raise RuntimeError(f"Feature {row[3]} has no usable road geometry in {url}")
            rows.extend(features)
            # Layer metadata records upstream edit times separately from our pull.
            snapshots.append((
                source_key, layer_id, metadata["name"], url, len(features),
                json.dumps(metadata),
            ))
    return rows, snapshots


def replace_snapshot(connection, rows, snapshots, started_at):
    with connection:
        with connection.cursor() as cursor:
            # Serialize replacements so concurrent imports cannot interleave rows.
            cursor.execute("select pg_advisory_xact_lock(hashtext('raw_roadway_features'))")
            cursor.execute("select max(pulled_at) from roadway_source_snapshots")
            last_pull = cursor.fetchone()[0]
            if last_pull and last_pull > started_at:
                raise RuntimeError("A newer roadway import already completed; keeping its snapshot.")
            cursor.execute("delete from raw_roadway_features")
            execute_values(cursor, """
                insert into raw_roadway_features
                    (source_key, layer_id, layer_name, object_id, payload, geom)
                values %s
            """, rows, template=(
                "(%s, %s, %s, %s, %s::jsonb, "
                "case when %s is null then null else st_setsrid(st_geomfromgeojson(%s), 4326) end)"
            ), page_size=500)
            cursor.execute("delete from roadway_source_snapshots")
            execute_values(cursor, """
                insert into roadway_source_snapshots
                    (source_key, layer_id, layer_name, source_url, feature_count, metadata)
                values %s
            """, snapshots, template="(%s, %s, %s, %s, %s, %s::jsonb)")


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL is required")
    started_at = datetime.now(timezone.utc)
    with requests.Session() as session:
        session.headers.update({"User-Agent": "Tucson bike infrastructure data pipeline"})
        rows, snapshots = fetch_all(session)
    with closing(psycopg2.connect(database_url)) as connection:
        replace_snapshot(connection, rows, snapshots, started_at)
    print(f"Done. Imported {len(rows)} roadway features across {len(snapshots)} layers.")


if __name__ == "__main__":
    main()
