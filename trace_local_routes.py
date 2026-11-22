"""Reconstruct user-described route corridors for local visual inspection.

Reads private scenarios from ~/.cache/tucson-bikes/commute-scenarios.json.
These are physical traces, not a bicycle router. Scenarios can opt into mapped
one-way and footway checks; full access, turn, and stress logic is not applied.
Departures from specified corridors are flagged. Personal scenarios stay off Git.
"""

import heapq
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from shapely.geometry import LineString, Point, shape
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree


def normalized_street(value):
    abbreviations = {
        "north": "n", "south": "s", "east": "e", "west": "w",
        "avenue": "av", "ave": "av", "street": "st", "road": "rd",
        "boulevard": "bl", "blvd": "bl", "drive": "dr", "place": "pl",
    }
    return " ".join(abbreviations.get(word, word) for word in re.findall(r"[a-z0-9]+", (value or "").lower()))


def on_corridor(edge, preferred, bikeways):
    return edge["name"] in preferred or any(
        match["bikeway"] in bikeways for match in edge["agency_matches"]
    )


def bicycle_direction(tags):
    return tags.get("oneway:bicycle", tags.get("oneway", "yes" if tags.get("junction") == "roundabout" else "no"))


def can_trace(edge, start, finish, constraints):
    tags = edge["tags"]
    if constraints.get("exclude_unverified_footways") and tags.get("highway") == "footway":
        if not any(match["facility_type"] == "Shared-Use Path" for match in edge["agency_matches"]):
            return False
    if constraints.get("respect_bicycle_conflicts") and tags.get("bicycle") in ("no", "dismount") and not edge["agency_matches"]:
        return False
    if constraints.get("respect_oneway"):
        direction = bicycle_direction(tags)
        forward = (start, finish) == edge["forward"]
        if direction in ("yes", "1", "true") and not forward:
            return False
        if direction == "-1" and forward:
            return False
    return True


def shortest_path(graph, start, finish, preferred, connector_ids, bikeways, constraints=None):
    queue = [(0, start)]
    costs = {start: 0}
    previous = {}
    while queue:
        cost, node = heapq.heappop(queue)
        if cost != costs[node]:
            continue
        if node == finish:
            path = []
            while node != start:
                parent, edge = previous[node]
                path.append((parent, node, edge))
                node = parent
            return list(reversed(path))
        for neighbor, edge in graph.get(node, []):
            if not can_trace(edge, node, neighbor, constraints or {}):
                continue
            factor = 1 if on_corridor(edge, preferred, bikeways) or edge["way_id"] in connector_ids else 100
            candidate = cost + edge["meters"] * factor
            if candidate < costs.get(neighbor, math.inf):
                costs[neighbor] = candidate
                previous[neighbor] = (node, edge)
                heapq.heappush(queue, (candidate, neighbor))
    raise ValueError("No connected physical trace between the selected checkpoints.")


def trace(connection, config):
    with connection.cursor() as cursor:
        cursor.execute("select current_database(), inet_server_addr()::text")
        database, address = cursor.fetchone()
        if database != "tucson_bikes_local" or address not in (None, "127.0.0.1", "::1"):
            raise ValueError("Use the local tucson_bikes_local database.")
        cursor.execute("""
            select osm_id, node_ids, tags, st_asgeojson(geom)::json,
              st_asgeojson(st_transform(geom, 32612))::json
            from raw_osm_ways
            where scope_key = %s
              and geom && st_makeenvelope(%s, %s, %s, %s, 4326)
              and tags->>'highway' = any(%s)
            order by osm_id
        """, (
            config["scope_key"], *config["bounds"],
            ["residential", "unclassified", "tertiary", "secondary", "primary",
             "tertiary_link", "secondary_link", "primary_link", "cycleway",
             "pedestrian", "path", "footway", "living_street", "service"],
        ))
        ways = cursor.fetchall()
        cursor.execute("""
            select objectid, payload->'properties'->>'STREET',
              payload->'properties'->>'Display', payload->'properties'->>'NAME_BKWY',
              st_asgeojson(st_transform(geom, 32612))::json
            from raw_pag_bikeways
            where geom && st_makeenvelope(%s, %s, %s, %s, 4326)
            order by objectid
        """, config["bounds"])
        agency = [
            {"objectid": oid, "street": street, "facility_type": kind,
             "bikeway": (name or "").strip(), "geometry": shape(geometry)}
            for oid, street, kind, name, geometry in cursor.fetchall()
            if kind in ("Bike Boulevard", "Bike Lane", "Shared-Use Path", "Bike Route",
                        "Enhanced Bike Route", "Separated Bike Lane", "Bike Lane - Frontage Road")
        ]
        cursor.execute("select source_timestamp from osm_network_snapshots where scope_key = %s",
                       (config["scope_key"],))
        source_timestamp = cursor.fetchone()[0].isoformat()

    graph = defaultdict(list)
    agency_tree = STRtree([record["geometry"] for record in agency])
    agency_buffers = [record["geometry"].buffer(8) for record in agency]
    named_route_buffers = [record["geometry"].buffer(6) for record in agency]
    coordinates = {}
    metric_coordinates = {}
    geometries = []
    for way_id, nodes, tags, geojson, metric_geojson in ways:
        # This traces a reported physical journey. Pedestrian connections are
        # retained for inspection and flagged below, never granted eligibility.
        if tags.get("access") in ("private", "no") and tags.get("bicycle") not in ("yes", "designated"):
            continue
        points = geojson["coordinates"]
        metric_points = metric_geojson["coordinates"]
        if len(nodes) != len(points) or len(nodes) != len(metric_points):
            raise ValueError(f"Node/coordinate mismatch on way {way_id}.")
        metric_line = shape(metric_geojson)
        geometries.append((way_id, tags, metric_line))
        for node, point, metric_point in zip(nodes, points, metric_points):
            coordinates[node] = point
            metric_coordinates[node] = metric_point
        for index, (a, b) in enumerate(zip(nodes, nodes[1:])):
            meters = math.dist(metric_points[index], metric_points[index + 1])
            if a == b or not meters:
                continue
            line = LineString(metric_points[index:index + 2])
            matches = []
            for candidate in agency_tree.query(line.buffer(8)):
                record = agency[candidate]
                # Sidewalk proximity alone cannot transfer a road's bike status.
                if tags["highway"] == "footway":
                    if record["facility_type"] != "Shared-Use Path":
                        continue
                same_street = bool(tags.get("name")) and normalized_street(tags["name"]) == normalized_street(record["street"])
                different_name = bool(tags.get("name")) and not same_street
                # Some agency records follow several physical streets but carry
                # one street label (for example Treat around La Madera Park).
                # Accept that candidate only with close, aligned route geometry.
                if tags["highway"] != "footway" and different_name:
                    if record["facility_type"] != "Bike Boulevard" or not record["bikeway"]:
                        continue
                    projected = [nearest_points(Point(point), record["geometry"])[1] for point in line.coords]
                    vector = (projected[-1].x - projected[0].x, projected[-1].y - projected[0].y)
                    edge_vector = (line.coords[-1][0] - line.coords[0][0], line.coords[-1][1] - line.coords[0][1])
                    magnitude = math.hypot(*vector)
                    alignment = abs(sum(a * b for a, b in zip(vector, edge_vector))) / (magnitude * meters) if magnitude else 0
                    if alignment < math.cos(math.radians(25)):
                        continue
                    if line.intersection(named_route_buffers[candidate]).length / meters < 0.9:
                        continue
                coverage = line.intersection(agency_buffers[candidate]).length / meters
                if coverage >= 0.8:
                    match = {key: record[key] for key in ("objectid", "street", "facility_type", "bikeway")}
                    match["street_name_agrees"] = same_street
                    match["method"] = "named_bikeway_geometry" if different_name else "street_and_geometry" if same_street else "geometry_candidate"
                    matches.append(match)
            if tags["highway"] == "service" and not matches and tags.get("bicycle") not in ("yes", "designated"):
                continue
            edge = {"way_id": way_id, "name": tags.get("name", "Unnamed connection"),
                    "tags": tags, "meters": meters, "forward": (a, b),
                    "agency_matches": matches}
            graph[a].append((b, edge))
            graph[b].append((a, edge))

    features = []
    summaries = []
    for route in config["routes"]:
        route_id = route["id"]
        checkpoint_nodes = []
        for checkpoint in route["checkpoints"]:
            lon, lat = checkpoint["coordinates"]
            def distance(node):
                point = coordinates[node]
                return math.hypot((point[0] - lon) * math.cos(math.radians(lat)), point[1] - lat)
            node = checkpoint.get("osm_node_id")
            if node is None:
                node = min(graph, key=distance)
            elif node not in graph:
                raise ValueError(f"Checkpoint node is absent: {checkpoint['label']}")
            if distance(node) * 111195 > 80:
                raise ValueError(f"Checkpoint too far from a graph node: {checkpoint['label']}")
            checkpoint_nodes.append(node)
        total = 0
        departures = 0
        for index, leg in enumerate(route["legs"]):
            preferred = set(leg["streets"])
            bikeways = set(leg.get("bikeways", []))
            preferred_lines = [g for _, tags, g in geometries if tags.get("name") in preferred]
            preferred_lines.extend(record["geometry"] for record in agency if record["bikeway"] in bikeways)
            if not preferred_lines:
                raise ValueError(f"No source geometry for {leg['label']}.")
            corridor = unary_union(preferred_lines).buffer(45)
            connector_ids = {
                way_id for way_id, tags, geom in geometries
                if tags["highway"] in ("cycleway", "pedestrian", "path", "footway")
                and corridor.covers(geom)
            }
            # User-confirmed physical connections can be unnamed or tagged
            # inconsistently. Explicit way IDs constrain only this draft trace;
            # original access/dismount flags below remain visible.
            connector_ids.update(leg.get("way_ids", []))
            path = shortest_path(graph, checkpoint_nodes[index], checkpoint_nodes[index + 1],
                                 preferred, connector_ids, bikeways, route.get("constraints"))
            for a, b, edge in path:
                departure = not on_corridor(edge, preferred, bikeways) and edge["way_id"] not in connector_ids
                tags = edge["tags"]
                flags = []
                if departure:
                    departures += edge["meters"]
                    flags.append("Leaves requested corridor: inspect connection")
                if tags.get("bicycle") in ("no", "dismount"):
                    flags.append(f"OSM bicycle={tags['bicycle']}: unresolved")
                if tags["highway"] == "footway":
                    flags.append("Footway: shared-use-path status not verified; not riding-eligible")
                elif tags["highway"] in ("pedestrian", "path") and tags.get("bicycle") not in ("yes", "designated"):
                    flags.append("Path bicycle permission not verified")
                direction = bicycle_direction(tags)
                forward = (a, b) == edge["forward"]
                if (direction in ("yes", "1", "true") and not forward) or (direction == "-1" and forward):
                    flags.append("Against tagged one-way direction: inspect bicycle exception")
                total += edge["meters"]
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [coordinates[a], coordinates[b]]},
                    "properties": {
                        "route_id": route_id, "route_label": route["label"],
                        "leg": leg["label"], "street": edge["name"], "osm_way_id": edge["way_id"],
                        "highway": tags["highway"], "bicycle": tags.get("bicycle"),
                        "maxspeed": tags.get("maxspeed"), "lanes": tags.get("lanes"),
                        "meters": round(edge["meters"], 2), "flags": flags,
                        "departure": departure,
                        "from_osm_node": a,
                        "to_osm_node": b,
                        "agency_matches": edge["agency_matches"],
                        "observation": leg.get("observation"),
                    },
                })
            crossings = ([leg["crossing"]] if leg.get("crossing") else []) + leg.get("crossings", [])
            for crossing in crossings:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": crossing["coordinates"]},
                    "properties": {
                        "route_id": route_id, "kind": "crossing",
                        "label": crossing["label"], "signal_type": crossing["signal_type"],
                        "source": crossing["source"], "object_id": crossing["object_id"],
                    },
                })
        for index, checkpoint in enumerate(route["checkpoints"]):
            features.append({
                "type": "Feature", "geometry": {"type": "Point", "coordinates": coordinates[checkpoint_nodes[index]]},
                "properties": {"route_id": route_id, "label": checkpoint["label"], "kind": "checkpoint"},
            })
        for endpoint in route.get("business_endpoints", []):
            features.append({"type": "Feature",
                "geometry": {"type": "Point", "coordinates": endpoint["coordinates"]},
                "properties": {"route_id": route_id, "kind": "business_endpoint", "label": endpoint["label"],
                               "role": endpoint["role"], "source_url": endpoint["source_url"]}})
        summaries.append({"id": route_id, "label": route["label"], "notes": route["notes"],
                          "miles": round(total / 1609.344, 2), "departure_meters": round(departures),
                          "color": route.get("color"), "endpoint_note": route.get("endpoint_note"),
                          "validation_note": route.get("validation_note")})
    return {
        "type": "FeatureCollection", "features": features, "routes": summaries,
        "source_timestamp": source_timestamp,
        "notice": "Draft physical traces for review. Validation limits and endpoint access are documented per example. Dashed orange segments leave the requested street or named agency bikeway corridor.",
    }


def main():
    cache = Path.home() / ".cache/tucson-bikes"
    config = json.loads((cache / "commute-scenarios.json").read_text())
    load_dotenv(Path(__file__).resolve().parent / ".env")
    with psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5) as connection:
        connection.set_session(readonly=True)
        result = trace(connection, config)
    path = cache / "commute-traces.geojson"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result))
    temporary.replace(path)
    for route in result["routes"]:
        print(f"{route['label']}: {route['miles']} miles; {route['departure_meters']} m outside named corridor")
    print(f"Saved local draft: {path}")


if __name__ == "__main__":
    main()
