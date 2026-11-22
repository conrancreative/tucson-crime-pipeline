"""Build a private, source-documented bicycle infrastructure inventory.

No route selection, riding permission, or stress scoring is performed here.
Geometry matches are candidates; route memberships retain their own evidence.
"""

import argparse
import hashlib
import json
import math
import os
import re
import uuid
from difflib import SequenceMatcher
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from shapely import from_wkb
from shapely.geometry import Point, mapping
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

from import_osm_network import verify_local

ROOT = Path(__file__).resolve().parent
PAG_LAYER = "https://maps.pagregion.com/server/rest/services/TucsonMetroBikeMapVecLive/FeatureServer/4"
MATCH_METERS = 8
CONTINUITY_METERS = 10


def clean(value):
    value = (value or "").strip()
    return "" if value.lower() in ("<null>", "null", "none") else value


def normalized_name(value):
    return " ".join(re.findall(r"\w+", clean(value).casefold().replace("bicycle", "bike")))


def normalized_street(value):
    abbreviations = {"north": "n", "south": "s", "east": "e", "west": "w",
                     "avenue": "av", "ave": "av", "street": "st", "road": "rd",
                     "boulevard": "bl", "blvd": "bl", "drive": "dr", "place": "pl"}
    return " ".join(abbreviations.get(word, word) for word in re.findall(r"[a-z0-9]+", clean(value).lower()))


class Names:
    def __init__(self, config):
        self.aliases = {}
        self.relations = {}
        for record in config["routes"]:
            for alias in record["aliases"]:
                key = normalized_name(alias)
                if key in self.aliases and self.aliases[key]["id"] != record["id"]:
                    raise ValueError(f"Ambiguous bikeway alias: {alias}")
                self.aliases[key] = record
            for identifier in record.get("osm_relation_ids", []):
                if identifier in self.relations:
                    raise ValueError(f"Ambiguous OSM route alias: {identifier}")
                self.relations[identifier] = record

    def identify(self, name, *, relation_id=None, fallback=None, kind="named_bikeway"):
        record = self.relations.get(relation_id) or self.aliases.get(normalized_name(name))
        if record:
            identity, label, kind = "registered:" + record["id"], record["name"], record["kind"]
        elif clean(name):
            identity, label = "name:" + normalized_name(name), clean(name)
        else:
            identity, label = fallback, fallback
        if not identity:
            raise ValueError("Missing bikeway identity.")
        return str(uuid.uuid5(uuid.NAMESPACE_URL, "tucson-bikes:" + identity)), label, kind


def flatten_members(identifier, routes, trail=()):
    if identifier in trail:
        return [], [{"type": "relation_cycle", "ref": identifier}]
    if identifier not in routes:
        return [], [{"type": "missing_relation", "ref": identifier}]
    members, problems = [], []
    for member in routes[identifier]["members"]:
        if member["type"] == "r":
            children, issues = flatten_members(member["ref"], routes, (*trail, identifier))
            members.extend(children)
            problems.extend(issues)
        else:
            members.append(member)
    return members, problems


def osm_facility(tags, has_route=False):
    cycle_values = {value for key, value in tags.items() if key == "cycleway" or key.startswith("cycleway:")}
    if tags.get("highway") == "cycleway":
        return "OSM cycleway"
    if tags.get("bicycle_road") == "yes" or tags.get("cyclestreet") == "yes":
        return "OSM bicycle street"
    if cycle_values & {"track", "opposite_track"}:
        return "OSM cycle track"
    if cycle_values & {"lane", "opposite_lane"}:
        return "OSM bicycle lane"
    if cycle_values & {"shared_lane", "share_busway", "opposite_share_busway"}:
        return "OSM shared-lane markings"
    if has_route or tags.get("lcn") == "yes" or tags.get("rcn") == "yes" or tags.get("route") in ("bicycle", "mtb"):
        return "OSM bicycle route"
    if tags.get("bicycle") in ("yes", "designated", "permissive"):
        return "OSM bicycle permission only"
    return None


def status(tags):
    if tags.get("state") in ("proposed", "alternate", "connection"):
        return tags["state"]
    if tags.get("highway") in ("construction", "proposed") or tags.get("state") in ("construction", "disused", "abandoned"):
        return tags.get("state") or tags["highway"]
    return "existing_source_record"


def geometry_match(agency, way):
    a, w = agency["metric"], way["metric"]
    if w.is_empty or a.is_empty or not w.length or not a.length:
        return None
    tags = way["tags"]
    if tags.get("highway") == "footway" and agency["facility_type"] != "Shared-Use Path":
        return None
    aw = normalized_street(agency["street"])
    ww = normalized_street(tags.get("name"))
    same_name = bool(aw and ww and aw == ww)
    different_names = bool(aw and ww and aw != ww)
    if different_names and not (agency["facility_type"] == "Bike Boulevard" and agency["bikeway_name"]):
        return None
    tolerance = 6 if different_names else MATCH_METERS
    covered_way = w.intersection(a.buffer(tolerance))
    covered_agency = a.intersection(w.buffer(tolerance))
    if max(covered_way.length / w.length, covered_agency.length / a.length) < (0.9 if different_names else 0.8):
        return None
    # Crossing lines can share a small buffer. Require a meaningful aligned
    # stretch whenever names do not establish the physical street identity.
    if not same_name:
        parts = list(covered_way.geoms) if hasattr(covered_way, "geoms") else [covered_way]
        parts = [part for part in parts if part.geom_type == "LineString" and part.length >= 3]
        if not parts:
            return None
        part = max(parts, key=lambda item: item.length)
        p, q = Point(part.coords[0]), Point(part.coords[-1])
        ap, aq = nearest_points(p, a)[1], nearest_points(q, a)[1]
        dx, dy = q.x - p.x, q.y - p.y
        ax, ay = aq.x - ap.x, aq.y - ap.y
        denom = math.hypot(dx, dy) * math.hypot(ax, ay)
        if not denom or abs(dx * ax + dy * ay) / denom < math.cos(math.radians(25)):
            return None
    return {
        "matched_meters": round(covered_agency.length, 2),
        "agency_coverage": round(covered_agency.length / a.length, 4),
        "osm_way_coverage": round(covered_way.length / w.length, 4),
        "method": "street_and_geometry" if same_name else "aligned_geometry",
        "street_name_agrees": same_name,
        "status": "candidate_not_permission",
    }


def geometry_components(geometries, tolerance=CONTINUITY_METERS):
    parts = []
    for geometry in geometries:
        parts.extend(list(geometry.geoms) if hasattr(geometry, "geoms") else [geometry])
    parts = [part for part in parts if part.geom_type == "LineString" and part.length]
    if not parts:
        return 0
    parent = list(range(len(parts)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    cells = defaultdict(list)
    for i, part in enumerate(parts):
        for x, y, *_ in (part.coords[0], part.coords[-1]):
            cell = (math.floor(x / tolerance), math.floor(y / tolerance))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for other, ox, oy in cells[(cell[0] + dx, cell[1] + dy)]:
                        if math.hypot(x - ox, y - oy) <= tolerance:
                            parent[root(i)] = root(other)
            cells[cell].append((i, x, y))
    return len({root(i) for i in range(len(parts))})


def input_fingerprints(cursor, scope):
    cursor.execute("select source_sha256, extract_sha256, source_timestamp from osm_network_snapshots where scope_key = %s", (scope,))
    row = cursor.fetchone()
    if not row:
        raise ValueError("Import the OSM network first.")
    cursor.execute("select source_sha256, imported_at from osm_bicycle_route_snapshots where scope_key = %s", (scope,))
    route_snapshot = cursor.fetchone()
    if not route_snapshot or route_snapshot[0] != row[0]:
        raise ValueError("Import bicycle relations from the same network snapshot first.")
    cursor.execute("select count(*), max(pulled_at)::text from raw_pag_bikeways")
    pag_count, pag_pulled = cursor.fetchone()
    return {"osm_source_sha256": row[0], "osm_extract_sha256": row[1],
            "osm_source_timestamp": row[2].isoformat(), "osm_routes_imported_at": route_snapshot[1].isoformat(),
            "pag_record_count": pag_count, "pag_imported_at": pag_pulled,
            "aliases_sha256": hashlib.sha256((ROOT / "config/bikeway_aliases.json").read_bytes()).hexdigest(),
            "review_notes_sha256": hashlib.sha256((ROOT / "config/bikeway_review_notes.json").read_bytes()).hexdigest(),
            "matching_version": 1, "match_meters": MATCH_METERS, "continuity_meters": CONTINUITY_METERS}


def read_inputs(cursor, scope):
    cursor.execute("""
        select w.osm_id, w.tags, w.node_ids,
          st_asbinary(st_transform(st_collectionextract(st_intersection(w.geom, s.study_area), 2), 32612))
        from raw_osm_ways w join osm_network_snapshots s using (scope_key)
        where w.scope_key = %s and w.geom && s.study_area and st_intersects(w.geom, s.study_area)
        order by w.osm_id
    """, (scope,))
    ways = {}
    for identifier, tags, nodes, geometry in cursor:
        metric = from_wkb(bytes(geometry))
        if not metric.is_empty and metric.length:
            ways[identifier] = {"id": identifier, "tags": tags, "nodes": nodes, "metric": metric}
    cursor.execute("""
        select b.objectid, b.payload->'properties', b.pulled_at,
          st_asbinary(st_transform(st_collectionextract(st_intersection(b.geom, s.study_area), 2), 32612))
        from raw_pag_bikeways b cross join osm_network_snapshots s
        where s.scope_key = %s and b.geom && s.study_area and st_intersects(b.geom, s.study_area)
        order by b.objectid
    """, (scope,))
    agency = []
    for identifier, tags, pulled, geometry in cursor:
        metric = from_wkb(bytes(geometry))
        if not metric.is_empty and metric.length:
            agency.append({"id": identifier, "properties": tags, "metric": metric,
                           "street": clean(tags.get("STREET")), "facility_type": clean(tags.get("Display")) or "Unclassified agency facility",
                           "bikeway_name": clean(tags.get("NAME_BKWY")), "pulled_at": pulled})
    cursor.execute("select osm_id, tags, members, source_edited_at from raw_osm_bicycle_routes where scope_key = %s order by osm_id", (scope,))
    routes = {identifier: {"tags": tags, "members": members, "edited_at": edited} for identifier, tags, members, edited in cursor}
    return agency, ways, routes


def build(connection, scope="tucson_3mi"):
    names = Names(json.loads((ROOT / "config/bikeway_aliases.json").read_text()))
    notes = json.loads((ROOT / "config/bikeway_review_notes.json").read_text())["notes"]
    with connection:
        with connection.cursor() as cursor:
            verify_local(cursor)
            cursor.execute("select pg_advisory_xact_lock(hashtext(%s))", (f"osm_network:{scope}",))
            fingerprints = input_fingerprints(cursor, scope)
            print("Reading study-area facilities and OSM geometry…", flush=True)
            agency, ways, routes = read_inputs(cursor, scope)
            if not agency or not ways:
                raise ValueError("Refusing an empty inventory build.")
            sections, catalog, memberships, issues, matches = {}, {}, {}, [], []
            section_groups = defaultdict(set)

            def register(name, source_name, *, relation_id=None, fallback=None, kind="named_bikeway"):
                identifier, label, kind = names.identify(name, relation_id=relation_id, fallback=fallback, kind=kind)
                record = catalog.setdefault(identifier, {"id": identifier, "name": label, "kind": kind, "source_names": set(), "details": {}})
                if clean(source_name):
                    record["source_names"].add(clean(source_name))
                return identifier

            def member(bikeway_id, section_id, evidence):
                memberships.setdefault((bikeway_id, section_id), []).append(evidence)
                section_groups[section_id].add(bikeway_id)

            def issue(kind, key, text, *, section_id=None, route_ids=(), details=None):
                issues.append({"id": f"{kind}:{key}", "type": kind, "description": text,
                               "section_id": section_id, "bikeway_ids": list(route_ids or section_groups.get(section_id, ())),
                               "details": details or {}})

            for a in agency:
                section_id = f"pag:{a['id']}"
                source_name = a["bikeway_name"]
                if source_name:
                    bikeway_id = register(source_name, source_name)
                else:
                    fallback = f"{a['street']} · {a['facility_type']}" if a["street"] else f"Unnamed {a['facility_type']} · PAG {a['id']}"
                    bikeway_id = register("", "", fallback="agency-section:" + fallback, kind="street_group" if a["street"] else "unnamed_facility")
                    catalog[bikeway_id]["name"] = fallback
                sections[section_id] = {"source": "pag", "source_id": str(a["id"]), "street": a["street"],
                    "facility_type": a["facility_type"], "metric": a["metric"], "source_date": a["pulled_at"],
                    "source_url": PAG_LAYER + "/query?where=OBJECTID%3D" + str(a["id"]) + "&outFields=*&f=pjson",
                    "facts": {"agency_properties": a["properties"], "source_date_kind": "imported_at",
                              "status": "existing_source_record", "permission_evaluated": False}}
                member(bikeway_id, section_id, {"kind": "agency_name" if source_name else "agency_facility", "source_name": source_name})

            route_way_members = defaultdict(list)
            for identifier, route in routes.items():
                label = clean(route["tags"].get("name")) or clean(route["tags"].get("ref"))
                bikeway_id = register(label, label, relation_id=identifier, fallback=f"osm-route:{identifier}")
                if not label:
                    catalog[bikeway_id]["name"] = f"OSM bicycle route {identifier}"
                flattened, nested_problems = flatten_members(identifier, routes)
                way_members = [m for m in flattened if m["type"] == "w"]
                available = [m for m in way_members if m["ref"] in ways]
                unavailable = [m for m in way_members if m["ref"] not in ways]
                info = {"id": identifier, "name": label, "ref": route["tags"].get("ref"),
                        "network": route["tags"].get("network"), "route": route["tags"].get("route"),
                        "status": status(route["tags"]), "source_edited_at": route["edited_at"].isoformat() if route["edited_at"] else None,
                        "direct_member_count": len(route["members"]), "flattened_way_members": len(way_members),
                        "local_way_members": len(available), "unavailable_way_members": len(unavailable),
                        "non_way_members": sum(m["type"] != "w" for m in flattened), "nested_issues": nested_problems,
                        "source_url": f"https://www.openstreetmap.org/relation/{identifier}"}
                catalog[bikeway_id]["details"].setdefault("osm_relations", []).append(info)
                if unavailable or nested_problems:
                    issue("route_members_unavailable", identifier,
                          f"OSM route has {len(unavailable)} way memberships absent from the local extract. They may be beyond the study area or missing from the source extract.",
                          route_ids=[bikeway_id], details=info)
                for m in available:
                    route_way_members[m["ref"]].append((bikeway_id, {"kind": "osm_relation", "relation_id": identifier,
                                                                   "role": m["role"], "status": status(route["tags"])}))

            print(f"Matching {len(agency):,} agency sections against {len(ways):,} OSM ways…", flush=True)
            identifiers = list(ways)
            tree = STRtree([ways[identifier]["metric"] for identifier in identifiers])
            matched_agency, matched_ways = set(), set()
            matching_by_way = defaultdict(list)
            for index, a in enumerate(agency):
                for candidate in tree.query(a["metric"].buffer(MATCH_METERS)):
                    way = ways[identifiers[candidate]]
                    result = geometry_match(a, way)
                    if result:
                        section_id = f"pag:{a['id']}"
                        matches.append((scope, section_id, way["id"], result["matched_meters"], json.dumps(result)))
                        matched_agency.add(a["id"])
                        matched_ways.add(way["id"])
                        matching_by_way[way["id"]].append({"agency_section_id": section_id, **result,
                                                           "facility_type": a["facility_type"]})
                if (index + 1) % 1000 == 0:
                    print(f"Matched candidates for {index + 1:,} agency sections", flush=True)
            for a in agency:
                if a["id"] not in matched_agency:
                    issue("agency_no_osm_match", a["id"],
                          "No OSM geometry match met the documented thresholds. This is a matching/data review item, not proof of a missing physical connection.",
                          section_id=f"pag:{a['id']}")

            selected_ways = {}
            for identifier, way in ways.items():
                kind = osm_facility(way["tags"], identifier in route_way_members)
                if not kind:
                    continue
                selected_ways[identifier] = way
                section_id = f"osm:{identifier}"
                tags = way["tags"]
                sections[section_id] = {"source": "osm", "source_id": str(identifier), "street": clean(tags.get("name")),
                    "facility_type": kind, "metric": way["metric"], "source_date": fingerprints["osm_source_timestamp"],
                    "source_url": f"https://www.openstreetmap.org/way/{identifier}",
                    "facts": {"osm_tags": tags, "status": status(tags), "permission_evaluated": False,
                              "agency_matches": matching_by_way[identifier], "source_date_kind": "snapshot_at"}}
                for bikeway_id, evidence in route_way_members[identifier]:
                    member(bikeway_id, section_id, evidence)
                if not section_groups[section_id]:
                    # A way name is not automatically an official named bikeway.
                    label = clean(tags.get("name")) or f"Unnamed {kind} · OSM {identifier}"
                    bikeway_id = register("", "", fallback="osm-facility:" + label + ":" + kind, kind="osm_facility_group")
                    catalog[bikeway_id]["name"] = label
                    member(bikeway_id, section_id, {"kind": "osm_way_tags"})
                if identifier not in matched_ways:
                    issue("osm_no_agency_match", identifier, "OSM bicycle evidence has no agency geometry match. Source coverage can legitimately differ.", section_id=section_id)
                has_existing_relation = any(evidence["status"] == "existing_source_record" for _, evidence in route_way_members[identifier])
                if tags.get("bicycle") in ("no", "dismount") and (matching_by_way[identifier] or has_existing_relation):
                    issue("bicycle_tag_conflict", identifier,
                          f"OSM bicycle={tags['bicycle']} conflicts with bicycle-facility or route evidence. Preserve both sources; riding eligibility is not evaluated by this inventory.",
                          section_id=section_id, details={"osm_bicycle": tags["bicycle"], "agency_matches": matching_by_way[identifier]})
                if tags.get("highway") == "footway" and not any(m["facility_type"] == "Shared-Use Path" for m in matching_by_way[identifier]):
                    issue("footway_shared_use_unverified", identifier, "Footway bicycle evidence needs shared-use-path verification before riding eligibility.", section_id=section_id)
                if status(tags) != "existing_source_record":
                    issue("nonstandard_facility_status", identifier, f"OSM status is {status(tags)}; do not assume an existing unrestricted bicycle facility.", section_id=section_id)

            # A conflicting OSM tag may be the reason a way has no affirmative
            # OSM bicycle classification. Audit those agency matches too.
            for identifier, evidence in matching_by_way.items():
                if identifier in selected_ways or ways[identifier]["tags"].get("bicycle") not in ("no", "dismount"):
                    continue
                bicycle = ways[identifier]["tags"]["bicycle"]
                issue("bicycle_tag_conflict", identifier,
                      f"OSM bicycle={bicycle} conflicts with candidate agency facility matches. Review the matched portion; do not apply a partial match to the entire way.",
                      section_id=evidence[0]["agency_section_id"],
                      details={"osm_way_id": identifier, "osm_bicycle": bicycle,
                               "source_url": f"https://www.openstreetmap.org/way/{identifier}", "agency_matches": evidence})

            # Suggest additional cross-source identity reviews map-wide. A
            # similar name plus substantial shared geometry is evidence for
            # review, never an automatic identity merge or access override.
            alias_pairs = defaultdict(lambda: {"ways": set(), "meters": 0, "section_id": None})
            for _, agency_id, way_id, meters, _ in matches:
                for agency_route in section_groups[agency_id]:
                    if catalog[agency_route]["kind"] != "named_bikeway":
                        continue
                    for osm_route, _ in route_way_members[way_id]:
                        if agency_route == osm_route:
                            continue
                        a_name = normalized_name(catalog[agency_route]["name"])
                        o_name = normalized_name(catalog[osm_route]["name"])
                        if SequenceMatcher(None, a_name, o_name).ratio() < 0.6:
                            continue
                        record = alias_pairs[(agency_route, osm_route)]
                        record["ways"].add(way_id)
                        record["meters"] += meters
                        record["section_id"] = agency_id
            for (agency_route, osm_route), evidence in alias_pairs.items():
                if len(evidence["ways"]) >= 3 and evidence["meters"] >= 150:
                    issue("route_identity_review", f"{agency_route}:{osm_route}",
                          f"{catalog[agency_route]['name']} and {catalog[osm_route]['name']} have similar names and shared geometry candidates. Review whether they are the same named route or intentionally overlapping routes.",
                          section_id=evidence["section_id"], route_ids=[agency_route, osm_route],
                          details={"osm_ways_with_candidates": len(evidence["ways"]), "candidate_meters": round(evidence["meters"]), "merged": False})

            print("Documenting named-route continuity and source coverage…", flush=True)
            grouped_sections = defaultdict(lambda: defaultdict(list))
            for (bikeway_id, section_id), evidence in memberships.items():
                grouped_sections[bikeway_id][sections[section_id]["source"]].append(section_id)
            for bikeway_id, record in catalog.items():
                source_summary = {}
                for source, section_ids in grouped_sections[bikeway_id].items():
                    geometries = [sections[identifier]["metric"] for identifier in section_ids]
                    source_summary[source] = {
                        "sections": len(section_ids), "source_miles": round(sum(g.length for g in geometries) / 1609.344, 2),
                        "geometry_groups": geometry_components(geometries),
                    }
                record["details"].update({"sources": source_summary,
                    "facility_types": sorted({sections[s]["facility_type"] for ids in grouped_sections[bikeway_id].values() for s in ids}),
                    "streets": sorted({sections[s]["street"] for ids in grouped_sections[bikeway_id].values() for s in ids if sections[s]["street"]}),
                    "continuity_method": "Endpoints within 10 m, within study area. Geometry groups are not proof of routing connectivity.",
                    "permission_evaluated": False})
                if record["kind"] == "named_bikeway" and any(info["geometry_groups"] > 1 for info in source_summary.values()):
                    section_id = next(iter(next(iter(grouped_sections[bikeway_id].values()))), None)
                    issue("named_route_continuity_review", bikeway_id,
                          "Named bikeway has separate source geometry groups. Review boundary clipping, branches, missing links, or source geometry; no connection was invented.",
                          section_id=section_id, route_ids=[bikeway_id], details=source_summary)
            for note in notes:
                way_id = note.get("osm_way_id")
                section_id = f"osm:{way_id}" if way_id in selected_ways else None
                note_routes = []
                if note.get("bikeway_name"):
                    candidate_id = names.identify(note["bikeway_name"])[0]
                    if candidate_id in catalog:
                        note_routes.append(candidate_id)
                issue("reported_source_update", note["id"], note["description"], section_id=section_id,
                      route_ids=note_routes, details=note)
                # Unmapped observations can still be located without altering data.
                if way_id and not section_id and way_id in ways:
                    issues[-1]["metric_point"] = ways[way_id]["metric"].representative_point()

            issue_counts = Counter(item["type"] for item in issues)
            summary = {"scope_key": scope, "agency_sections_in_scope": len(agency),
                "agency_records_total": fingerprints["pag_record_count"],
                "agency_records_outside_or_boundary_only": fingerprints["pag_record_count"] - len(agency),
                "agency_sections_with_osm_candidates": len(matched_agency),
                "agency_sections_without_osm_candidates": len(agency) - len(matched_agency),
                "osm_input_ways_in_scope": len(ways), "osm_bicycle_sections": len(selected_ways),
                "osm_bicycle_route_relations": len(routes), "catalog_entries": len(catalog),
                "named_bikeways": sum(record["kind"] == "named_bikeway" for record in catalog.values()),
                "unnamed_agency_sections": sum(not a["bikeway_name"] for a in agency),
                "sections": len(sections), "memberships": len(memberships), "geometry_matches": len(matches),
                "issues": dict(issue_counts), "permission_evaluated": False,
                "completeness": "Complete accounting of imported source records within the study area; real-world completeness is not established."}
            write_inventory(cursor, scope, sections, catalog, memberships, matches, issues, fingerprints, summary)
    return summary


def write_inventory(cursor, scope, sections, catalog, memberships, matches, issues, fingerprints, summary):
    for table in ("bikeway_memberships", "bikeway_matches", "bikeway_issues", "bikeway_sections", "bikeway_catalog"):
        cursor.execute(f"delete from {table} where scope_key = %s", (scope,))
    execute_values(cursor, "insert into bikeway_catalog (scope_key,bikeway_id,name,kind,source_names,details) values %s", [
        (scope, record["id"], record["name"], record["kind"], json.dumps(sorted(record["source_names"])), json.dumps(record["details"]))
        for record in catalog.values()
    ], template="(%s,%s::uuid,%s,%s,%s::jsonb,%s::jsonb)")
    execute_values(cursor, """
        insert into bikeway_sections
          (scope_key,section_id,source,source_id,source_url,street,facility_type,source_date,geom,facts)
        select v.scope_key,v.section_id,v.source,v.source_id,v.source_url,v.street,v.facility_type,v.source_date::timestamptz,
          st_multi(st_transform(st_geomfromwkb(decode(v.geometry_hex,'hex'),32612),4326)),v.facts::jsonb
        from (values %s) as v(scope_key,section_id,source,source_id,source_url,street,facility_type,source_date,geometry_hex,facts)
    """, [
        (scope, identifier, s["source"], s["source_id"], s["source_url"], s["street"], s["facility_type"], s["source_date"], s["metric"].wkb_hex, json.dumps(s["facts"]))
        for identifier, s in sections.items()
    ], page_size=500)
    execute_values(cursor, "insert into bikeway_memberships (scope_key,bikeway_id,section_id,evidence) values %s", [
        (scope, identifier, section_id, json.dumps(evidence)) for (identifier, section_id), evidence in memberships.items()
    ], template="(%s,%s::uuid,%s,%s::jsonb)")
    if matches:
        execute_values(cursor, "insert into bikeway_matches (scope_key,agency_section_id,osm_way_id,matched_meters,details) values %s", matches,
                       template="(%s,%s,%s,%s,%s::jsonb)")
    if issues:
        execute_values(cursor, """
            insert into bikeway_issues (scope_key,issue_id,issue_type,section_id,bikeway_ids,description,geom,details)
            select v.scope_key,v.issue_id,v.issue_type,v.section_id,v.bikeway_ids::uuid[],v.description,
              case when v.geometry_hex is not null then st_transform(st_geomfromwkb(decode(v.geometry_hex,'hex'),32612),4326)
                when v.coordinates is not null then st_setsrid(st_geomfromgeojson(v.coordinates),4326)
                else (select st_lineinterpolatepoint(st_geometryn(s.geom,1),0.5) from bikeway_sections s where s.scope_key=v.scope_key and s.section_id=v.section_id)
              end,v.details::jsonb
            from (values %s) as v(scope_key,issue_id,issue_type,section_id,bikeway_ids,description,geometry_hex,coordinates,details)
        """, [
            (scope, item["id"], item["type"], item["section_id"], item["bikeway_ids"], item["description"],
             item["metric_point"].wkb_hex if item.get("metric_point") is not None else None,
             json.dumps({"type": "Point", "coordinates": item["details"]["coordinates"]}) if "coordinates" in item["details"] else None,
             json.dumps(item["details"]))
            for item in issues
        ], page_size=500)
    # Verify source accounting before committing the replacement.
    cursor.execute("select count(*) from bikeway_sections where scope_key=%s and source='pag'", (scope,))
    if cursor.fetchone()[0] != summary["agency_sections_in_scope"]:
        raise ValueError("Agency source accounting failed.")
    cursor.execute("""select count(*) from bikeway_sections s where s.scope_key=%s and not exists (
        select 1 from bikeway_memberships m where m.scope_key=s.scope_key and m.section_id=s.section_id)
    """, (scope,))
    if cursor.fetchone()[0]:
        raise ValueError("Inventory contains sections without catalog membership.")
    cursor.execute("""
        insert into bikeway_builds (scope_key,input_fingerprints,summary) values (%s,%s::jsonb,%s::jsonb)
        on conflict (scope_key) do update set input_fingerprints=excluded.input_fingerprints,
          summary=excluded.summary,built_at=now()
    """, (scope, json.dumps(fingerprints), json.dumps(summary)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", default="tucson_3mi")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    with closing(psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5)) as connection:
        connection.set_session(isolation_level="REPEATABLE READ")
        summary = build(connection, args.scope)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
