"""Serve the local site and bike-route GeoJSON from the local PostgreSQL copy."""

import json
import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def station_name(name, address):
    """Prefer supplied street intersections, retaining landmark names as fallback."""
    candidates = [address or "", name or ""]
    label = next(
        (value for value in candidates if re.search(r"@|&|\band\b", value, re.I)),
        name or address or "Unnamed station",
    )
    label = re.sub(r"\bSMART\b", "", label, flags=re.I)
    label = re.sub(r"^UA\s*-\s*", "", label, flags=re.I)
    label = re.sub(r"\s*(?:@|&|\band\b)\s*", " & ", label, flags=re.I)
    label = re.sub(r"\s+", " ", label).strip()
    return re.sub(r"(^|\s)([a-z])", lambda match: match[0].upper(), label)


def bike_route_data():
    with psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5) as connection:
        connection.set_session(readonly=True)
        with connection.cursor() as cursor:
            cursor.execute("select current_database(), inet_server_addr()::text")
            database, address = cursor.fetchone()
            if database != "tucson_bikes_local" or address not in (
                None,
                "127.0.0.1",
                "::1",
            ):
                raise ValueError(
                    "Set DATABASE_URL to your local tucson_bikes_local database."
                )

            cursor.execute("""
                select objectid, street, facility_type, facility_description
                    , length_miles, geometry, pulled_at
                from preview_pag_bikeways
                order by objectid
            """)
            routes = []
            timestamps = []
            for (
                objectid,
                street,
                kind,
                description,
                miles,
                geometry,
                pulled_at,
            ) in cursor:
                routes.append(
                    {
                        "type": "Feature",
                        "id": objectid,
                        "geometry": geometry,
                        "properties": {
                            "street": street,
                            "facility_type": kind or "Unclassified",
                            "facility_description": description,
                            "length_miles": miles,
                        },
                    }
                )
                timestamps.append(pulled_at)

            cursor.execute("""
                select object_id, properties, geometry, pulled_at
                from preview_pag_bikemap_features
                where source_key = 'pag_tucson_bikemap'
                  and layer_name = 'Push Button Crossings'
                  and geometry is not null
                order by object_id
            """)
            crossings = []
            for object_id, properties, geometry, pulled_at in cursor:
                crossings.append(
                    {
                        "type": "Feature",
                        "id": object_id,
                        "geometry": geometry,
                        "properties": properties,
                    }
                )
                timestamps.append(pulled_at)

            cursor.execute("""
                select station_id, name, address, lat, lon
                    , bikes_available, docks_available, status_reported_at
                    , status_captured_at
                from preview_tugo_stations
                where lat is not null and lon is not null
                order by station_id
            """)
            stations = []
            for (
                station_id,
                name,
                address,
                lat,
                lon,
                bikes,
                docks,
                reported,
                captured,
            ) in cursor:
                stations.append(
                    {
                        "type": "Feature",
                        "id": station_id,
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                        "properties": {
                            "name": station_name(name, address),
                            "is_smart": bool(
                                re.search(
                                    r"\bSMART\b", f"{name or ''} {address or ''}", re.I
                                )
                            ),
                            "bikes_available": bikes,
                            "spots_available": docks,
                            "status_reported_at": reported.isoformat()
                            if reported
                            else None,
                            "status_captured_at": captured.isoformat()
                            if captured
                            else None,
                        },
                    }
                )

    return {
        "routes": {"type": "FeatureCollection", "features": routes},
        "crossings": {"type": "FeatureCollection", "features": crossings},
        "stations": {"type": "FeatureCollection", "features": stations},
        "snapshot_at": min(timestamps).isoformat() if timestamps else None,
    }


class PreviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path != "/api/bike-routes":
            return super().do_GET()
        try:
            data = bike_route_data()
            status = 200
        except (psycopg2.Error, KeyError, ValueError):
            data = {
                "error": "Unable to load local bike data. Check PostgreSQL and DATABASE_URL in .env."
            }
            status = 503
        body = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    handler = partial(PreviewHandler, directory=str(ROOT / "web"))
    print("Local preview at http://localhost:8000", flush=True)
    with ThreadingHTTPServer(("127.0.0.1", 8000), handler) as server:
        server.serve_forever()
