"""Import a prepared OSM extract into private local source tables.

Run sql/21_osm_network.sql first. Reads DATABASE_URL from the root .env and
refuses databases other than the local tucson_bikes_local development database.
This preserves source data, without deciding bicycle access or calculating routes.
"""

import argparse
import hashlib
import json
import os
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import osmium
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from shapely.geometry import mapping, shape
from shapely.ops import unary_union


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_provenance(source, extract, area_file):
    area = unary_union([
        shape(feature["geometry"])
        for feature in json.loads(area_file.read_text())["features"]
    ])
    if area.is_empty or not area.is_valid or area.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError("Study area must contain valid WGS84 polygon geometry.")
    reader = osmium.io.Reader(str(source))
    try:
        timestamp = reader.header().get("osmosis_replication_timestamp")
    finally:
        reader.close()
    if not timestamp:
        raise ValueError("Original source is missing its snapshot timestamp.")
    return {
        "source_timestamp": timestamp,
        "source_sha256": sha256_file(source),
        "extract_sha256": sha256_file(extract),
        "area": json.dumps(mapping(area)),
        "metadata": {
            "source_file": source.name,
            "extract_file": extract.name,
            "area_sha256": sha256_file(area_file),
            "attribution": "OpenStreetMap contributors",
            "license": "ODbL-1.0",
            "access_rules_applied": False,
        },
    }


def verify_local(cursor):
    cursor.execute("select current_database(), inet_server_addr()::text")
    database, address = cursor.fetchone()
    if database != "tucson_bikes_local" or address not in (None, "127.0.0.1", "::1"):
        raise ValueError("DATABASE_URL must point to local tucson_bikes_local.")
    print(f"Target: {database} (local)", flush=True)


def validate_references(cursor, scope):
    cursor.execute("""
        select w.osm_id
        from raw_osm_ways w
        cross join lateral unnest(w.node_ids) as reference(node_id)
        left join raw_osm_nodes n
          on n.scope_key = w.scope_key and n.osm_id = reference.node_id
        where w.scope_key = %s and n.osm_id is null
        limit 1
    """, (scope,))
    if cursor.fetchone():
        raise ValueError("A retained way references a missing node.")

    cursor.execute("""
        select r.osm_id
        from raw_osm_restrictions r
        cross join lateral jsonb_array_elements(r.members) as m(member)
        left join raw_osm_nodes n
          on m.member->>'type' = 'n' and n.scope_key = r.scope_key
          and n.osm_id = (m.member->>'ref')::bigint
        left join raw_osm_ways w
          on m.member->>'type' = 'w' and w.scope_key = r.scope_key
          and w.osm_id = (m.member->>'ref')::bigint
        where r.scope_key = %s and (
          m.member->>'type' not in ('n', 'w')
          or (m.member->>'type' = 'n' and n.osm_id is null)
          or (m.member->>'type' = 'w' and w.osm_id is null)
        )
        limit 1
    """, (scope,))
    if cursor.fetchone():
        raise ValueError("A restriction has a missing or unsupported member.")


def import_snapshot(connection, extract, scope, provenance):
    counts = Counter()
    started_at = datetime.now(timezone.utc)
    with connection:
        with connection.cursor() as cursor:
            verify_local(cursor)
            # One active snapshot per scope. Failed imports roll back completely.
            cursor.execute(
                "select pg_advisory_xact_lock(hashtext(%s))", (f"osm_network:{scope}",)
            )
            cursor.execute(
                "select pulled_at from osm_network_snapshots where scope_key = %s",
                (scope,),
            )
            last = cursor.fetchone()
            if last and last[0] > started_at:
                raise ValueError("A newer import already finished for this scope.")
            for table in ("raw_osm_restrictions", "raw_osm_ways", "raw_osm_nodes"):
                cursor.execute(f"delete from {table} where scope_key = %s", (scope,))
            cursor.execute("""
                insert into osm_network_snapshots
                  (scope_key, source_timestamp, source_sha256, extract_sha256,
                   study_area, metadata)
                values (%s, %s, %s, %s,
                  st_multi(st_setsrid(st_geomfromgeojson(%s), 4326)), %s::jsonb)
                on conflict (scope_key) do update set
                  source_timestamp = excluded.source_timestamp,
                  source_sha256 = excluded.source_sha256,
                  extract_sha256 = excluded.extract_sha256,
                  study_area = excluded.study_area,
                  metadata = excluded.metadata,
                  pulled_at = now()
            """, (
                scope, provenance["source_timestamp"], provenance["source_sha256"],
                provenance["extract_sha256"], provenance["area"],
                json.dumps(provenance["metadata"]),
            ))

            buffers = {"nodes": [], "ways": [], "restrictions": []}
            statements = {
                "nodes": (
                    "insert into raw_osm_nodes (scope_key, osm_id, tags, geom) values %s",
                    "(%s, %s, %s::jsonb, st_setsrid(st_point(%s, %s), 4326))",
                ),
                "ways": (
                    "insert into raw_osm_ways (scope_key, osm_id, node_ids, tags, geom) values %s",
                    "(%s, %s, %s::bigint[], %s::jsonb, st_setsrid(st_geomfromgeojson(%s), 4326))",
                ),
                "restrictions": (
                    "insert into raw_osm_restrictions (scope_key, osm_id, tags, members) values %s",
                    "(%s, %s, %s::jsonb, %s::jsonb)",
                ),
            }

            def flush(kind):
                rows = buffers[kind]
                if rows:
                    statement, template = statements[kind]
                    execute_values(cursor, statement, rows, template=template, page_size=1000)
                    rows.clear()

            print("Importing nodes, ways, and restrictions…", flush=True)
            for obj in osmium.FileProcessor(extract).with_locations():
                tags = json.dumps(dict(obj.tags))
                if obj.is_node():
                    kind = "nodes"
                    row = (scope, obj.id, tags, obj.lon, obj.lat)
                elif obj.is_way():
                    kind = "ways"
                    if len(obj.nodes) < 2:
                        raise ValueError(f"Way {obj.id} has fewer than two nodes.")
                    geometry = json.dumps({
                        "type": "LineString",
                        "coordinates": [(node.lon, node.lat) for node in obj.nodes],
                    })
                    row = (scope, obj.id, [node.ref for node in obj.nodes], tags, geometry)
                elif obj.is_relation():
                    kind = "restrictions"
                    relation_type = obj.tags.get("type", "")
                    if relation_type != "restriction" and not relation_type.startswith("restriction:"):
                        raise ValueError(f"Unexpected relation type in extract: {relation_type}")
                    members = [{"type": m.type, "ref": m.ref, "role": m.role} for m in obj.members]
                    row = (scope, obj.id, tags, json.dumps(members))
                else:
                    continue
                buffers[kind].append(row)
                counts[kind] += 1
                if len(buffers[kind]) >= 5000:
                    flush(kind)
                if counts[kind] % 100000 == 0:
                    print(f"Read {counts[kind]:,} {kind}", flush=True)
            for kind in buffers:
                flush(kind)
            if not counts["nodes"] or not counts["ways"]:
                raise ValueError("Refusing to replace the snapshot with an empty network.")
            print("Checking node and restriction references…", flush=True)
            validate_references(cursor, scope)
            for kind, table in (
                ("nodes", "raw_osm_nodes"), ("ways", "raw_osm_ways"),
                ("restrictions", "raw_osm_restrictions"),
            ):
                cursor.execute(f"select count(*) from {table} where scope_key = %s", (scope,))
                if cursor.fetchone()[0] != counts[kind]:
                    raise ValueError(f"Imported {kind} count does not match the input.")
            provenance["metadata"]["counts"] = dict(counts)
            cursor.execute(
                "update osm_network_snapshots set metadata = %s::jsonb where scope_key = %s",
                (json.dumps(provenance["metadata"]), scope),
            )
    return counts


def main():
    cache = Path.home() / ".cache/tucson-bikes"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract", type=Path, default=cache / "tucson-network.osm.pbf")
    parser.add_argument("--source", type=Path, default=cache / "arizona-latest.osm.pbf")
    parser.add_argument("--area", type=Path, default=cache / "tucson-routing-area.geojson")
    parser.add_argument("--scope", default="tucson_3mi")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parent / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL is required in your environment or root .env.")
    with closing(psycopg2.connect(database_url, connect_timeout=5)) as connection:
        with connection.cursor() as cursor:
            verify_local(cursor)
        connection.rollback()
        print("Recording source hashes and snapshot timestamp…", flush=True)
        provenance = read_provenance(args.source, args.extract, args.area)
        counts = import_snapshot(connection, args.extract, args.scope, provenance)
    print("Committed local snapshot: " + ", ".join(f"{v:,} {k}" for k, v in counts.items()))
    print("Bicycle eligibility, graph construction, and stress scoring remain separate steps.")


if __name__ == "__main__":
    main()
