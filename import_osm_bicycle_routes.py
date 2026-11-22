"""Extract bicycle-route relation metadata for the existing local OSM network.

Full ordered member lists are retained, including members absent from the local
extract. This avoids silently clipping relation identities or importing entire
interstate routes into the study-area road network.
"""

import argparse
import json
import os
from contextlib import closing
from pathlib import Path

import osmium
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

from import_osm_network import sha256_file, verify_local


class BicycleRelations(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.routes = {}

    def relation(self, relation):
        tags = dict(relation.tags)
        if tags.get("route") not in ("bicycle", "mtb"):
            return
        if tags.get("type") not in ("route", "superroute", "route_master"):
            return
        self.routes[relation.id] = {
            "tags": tags,
            "members": [{"type": m.type, "ref": m.ref, "role": m.role} for m in relation.members],
            "version": relation.version,
            "edited_at": relation.timestamp.isoformat() if relation.timestamp else None,
        }


def relevant_relations(routes, local_way_ids):
    selected = {
        identifier for identifier, route in routes.items()
        if any(m["type"] == "w" and m["ref"] in local_way_ids for m in route["members"])
    }
    # Preserve parent identities and all available bicycle child relations.
    # Missing children remain explicit members and are reported by the audit.
    while True:
        expanded = set(selected)
        for identifier, route in routes.items():
            children = {m["ref"] for m in route["members"] if m["type"] == "r"}
            if identifier in selected or children & selected:
                expanded.add(identifier)
                expanded.update(children & routes.keys())
        if expanded == selected:
            return {identifier: routes[identifier] for identifier in sorted(selected)}
        selected = expanded


def import_routes(connection, source, scope="tucson_3mi"):
    source_hash = sha256_file(source)
    with connection:
        with connection.cursor() as cursor:
            verify_local(cursor)
            # Serialize with the underlying road snapshot importer.
            cursor.execute("select pg_advisory_xact_lock(hashtext(%s))", (f"osm_network:{scope}",))
            cursor.execute("select source_sha256, source_timestamp from osm_network_snapshots where scope_key = %s", (scope,))
            snapshot = cursor.fetchone()
            if not snapshot or snapshot[0] != source_hash:
                raise ValueError("Arizona source must match the imported network snapshot hash.")
            cursor.execute("select osm_id from raw_osm_ways where scope_key = %s", (scope,))
            local_way_ids = {row[0] for row in cursor}
            if not local_way_ids:
                raise ValueError("Import the local road network first.")
            print("Reading bicycle and MTB route relations from the original snapshot…", flush=True)
            reader = BicycleRelations()
            reader.apply_file(str(source))
            selected = relevant_relations(reader.routes, local_way_ids)
            # A zero-route region is valid. A surprising loss needs explicit review.
            cursor.execute("select count(*) from raw_osm_bicycle_routes where scope_key = %s", (scope,))
            previous_count = cursor.fetchone()[0]
            if previous_count and not selected:
                raise ValueError("Refusing to replace existing bicycle routes with an empty import.")
            cursor.execute("delete from raw_osm_bicycle_routes where scope_key = %s", (scope,))
            if selected:
                execute_values(cursor, """
                    insert into raw_osm_bicycle_routes
                      (scope_key, osm_id, tags, members, source_version, source_edited_at)
                    values %s
                """, [
                    (scope, identifier, json.dumps(route["tags"]), json.dumps(route["members"]),
                     route["version"], route["edited_at"])
                    for identifier, route in selected.items()
                ], template="(%s, %s, %s::jsonb, %s::jsonb, %s, %s)")
            metadata = {
                "relations_in_arizona_source": len(reader.routes),
                "retained_relations": len(selected),
                "direct_way_members": sum(m["type"] == "w" for r in selected.values() for m in r["members"]),
                "local_direct_way_members": sum(m["type"] == "w" and m["ref"] in local_way_ids for r in selected.values() for m in r["members"]),
                "license": "ODbL-1.0", "attribution": "OpenStreetMap contributors",
            }
            cursor.execute("""
                insert into osm_bicycle_route_snapshots
                  (scope_key, source_sha256, source_timestamp, metadata)
                values (%s, %s, %s, %s::jsonb)
                on conflict (scope_key) do update set source_sha256 = excluded.source_sha256,
                  source_timestamp = excluded.source_timestamp, metadata = excluded.metadata,
                  imported_at = now()
            """, (scope, source_hash, snapshot[1], json.dumps(metadata)))
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.home() / ".cache/tucson-bikes/arizona-latest.osm.pbf")
    parser.add_argument("--scope", default="tucson_3mi")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parent / ".env")
    with closing(psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5)) as connection:
        result = import_routes(connection, args.source, args.scope)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
