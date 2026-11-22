"""Refresh the documented local inventory from the prepared network and source PBF."""

import argparse
import json
import os
from contextlib import closing
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from build_bikeway_catalog import build
from import_osm_bicycle_routes import import_routes
from import_osm_network import verify_local


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", default="tucson_3mi")
    parser.add_argument("--source", type=Path, default=Path.home() / ".cache/tucson-bikes/arizona-latest.osm.pbf")
    args = parser.parse_args()
    load_dotenv(root / ".env")
    with closing(psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5)) as connection:
        with connection:
            with connection.cursor() as cursor:
                verify_local(cursor)
                cursor.execute((root / "sql/22_bikeway_catalog.sql").read_text())
        import_routes(connection, args.source, args.scope)
        connection.set_session(isolation_level="REPEATABLE READ")
        result = build(connection, args.scope)
    print(json.dumps(result, indent=2))
    print("Local inventory refreshed. Reload http://localhost:8000/routes/.")


if __name__ == "__main__":
    main()
