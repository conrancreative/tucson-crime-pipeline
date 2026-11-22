"""Meaningful invariants for source identity, matching, and relation extraction."""

import json
import tempfile
import unittest
from pathlib import Path

from shapely.geometry import LineString

from build_bikeway_catalog import Names, flatten_members, geometry_components, geometry_match, osm_facility
from import_osm_bicycle_routes import BicycleRelations, relevant_relations


class InventoryTests(unittest.TestCase):
    def test_identity_survives_street_and_source_name_changes(self):
        names = Names(json.loads(Path("config/bikeway_aliases.json").read_text()))
        agency = names.identify("Treat Avenue Bikeway")
        osm = names.identify("Treat", relation_id=1023625)
        renamed = names.identify("Changed source label", relation_id=1023625)
        self.assertEqual(agency, osm)
        self.assertEqual(osm, renamed)
        self.assertNotEqual(agency[0], names.identify("Unrelated Treat Road")[0])

    def test_reviewed_university_aliases_group_without_fuzzy_merging(self):
        names = Names(json.loads(Path("config/bikeway_aliases.json").read_text()))
        ids = {names.identify(name)[0] for name in ["3RD STREET - UNIVERSITY BIKE BL", "3rd Street - University Bikeway"]}
        ids.add(names.identify("University", relation_id=1023555)[0])
        self.assertEqual(len(ids), 1)
        self.assertNotIn(names.identify("University of Arizona")[0], ids)

    def test_conflicting_aliases_fail(self):
        with self.assertRaises(ValueError):
            Names({"routes": [
                {"id": "a", "name": "A", "kind": "named_bikeway", "aliases": ["same"]},
                {"id": "b", "name": "B", "kind": "named_bikeway", "aliases": ["SAME"]},
            ]})

    def test_named_boulevard_geometry_can_cross_street_names(self):
        agency = {"metric": LineString([(0, 0), (0, 100), (100, 100)]),
                  "street": "N TREAT AV", "facility_type": "Bike Boulevard", "bikeway_name": "Treat Avenue Bikeway"}
        way = {"metric": LineString([(3, 5), (3, 95)]), "tags": {"name": "North East Plaza Drive", "highway": "residential"}}
        match = geometry_match(agency, way)
        self.assertIsNotNone(match)
        self.assertFalse(match["street_name_agrees"])
        self.assertEqual(match["status"], "candidate_not_permission")

    def test_parallel_sidewalk_does_not_inherit_boulevard(self):
        agency = {"metric": LineString([(0, 0), (100, 0)]), "street": "MAIN ST",
                  "facility_type": "Bike Boulevard", "bikeway_name": "Main Bikeway"}
        way = {"metric": LineString([(0, 2), (100, 2)]), "tags": {"highway": "footway", "footway": "sidewalk", "bicycle": "yes"}}
        self.assertIsNone(geometry_match(agency, way))
        agency["facility_type"] = "Shared-Use Path"
        self.assertIsNotNone(geometry_match(agency, way))

    def test_crossing_line_is_not_a_route_match(self):
        agency = {"metric": LineString([(0, 0), (100, 0)]), "street": "N TREAT AV",
                  "facility_type": "Bike Boulevard", "bikeway_name": "Treat Avenue Bikeway"}
        way = {"metric": LineString([(50, -2), (50, 2)]), "tags": {"name": "Another Street", "highway": "residential"}}
        self.assertIsNone(geometry_match(agency, way))

    def test_partial_match_does_not_claim_full_way_coverage(self):
        agency = {"metric": LineString([(0, 0), (100, 0)]), "street": "MAIN ST",
                  "facility_type": "Bike Lane", "bikeway_name": ""}
        way = {"metric": LineString([(0, 0), (1000, 0)]), "tags": {"name": "Main Street", "highway": "residential"}}
        match = geometry_match(agency, way)
        self.assertGreater(match["agency_coverage"], .99)
        self.assertLess(match["osm_way_coverage"], .12)

    def test_permission_only_is_not_a_bike_lane(self):
        self.assertEqual(osm_facility({"bicycle": "yes", "highway": "residential"}), "OSM bicycle permission only")
        self.assertEqual(osm_facility({"cycleway:right": "lane"}), "OSM bicycle lane")
        self.assertEqual(osm_facility({"cycleway": "shared_lane"}), "OSM shared-lane markings")
        self.assertIsNone(osm_facility({"cycleway": "no"}))

    def test_continuity_does_not_bridge_large_gaps(self):
        self.assertEqual(geometry_components([LineString([(0, 0), (10, 0)]), LineString([(15, 0), (20, 0)])]), 1)
        self.assertEqual(geometry_components([LineString([(0, 0), (10, 0)]), LineString([(50, 0), (60, 0)])]), 2)

    def test_nested_routes_preserve_order_and_report_cycles(self):
        routes = {
            1: {"members": [{"type": "r", "ref": 2, "role": ""}, {"type": "w", "ref": 11, "role": "forward"}]},
            2: {"members": [{"type": "w", "ref": 10, "role": ""}, {"type": "r", "ref": 1, "role": ""}]},
        }
        members, issues = flatten_members(1, routes)
        self.assertEqual([m["ref"] for m in members], [10, 11])
        self.assertEqual(issues[0]["type"], "relation_cycle")

    def test_scope_selection_preserves_full_members_and_parent(self):
        routes = {
            1: {"members": [{"type": "w", "ref": 10, "role": ""}, {"type": "w", "ref": 99, "role": ""}]},
            2: {"members": [{"type": "r", "ref": 1, "role": ""}]},
            3: {"members": [{"type": "w", "ref": 88, "role": ""}]},
        }
        result = relevant_relations(routes, {10})
        self.assertEqual(set(result), {1, 2})
        self.assertEqual([m["ref"] for m in result[1]["members"]], [10, 99])

    def test_actual_osm_reader_preserves_route_tags_members_and_order(self):
        xml = '''<osm version="0.6"><relation id="1" version="2" timestamp="2026-11-21T00:00:00Z"><member type="way" ref="10" role="forward"/><member type="way" ref="99" role=""/><tag k="type" v="route"/><tag k="route" v="bicycle"/><tag k="name" v="Example Bikeway"/></relation><relation id="2"><tag k="type" v="restriction"/></relation></osm>'''
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.osm"
            path.write_text(xml)
            reader = BicycleRelations()
            reader.apply_file(str(path))
        self.assertEqual(set(reader.routes), {1})
        route = reader.routes[1]
        self.assertEqual(route["tags"]["name"], "Example Bikeway")
        self.assertEqual(route["version"], 2)
        self.assertEqual(route["members"][0]["role"], "forward")
        self.assertEqual([m["ref"] for m in route["members"]], [10, 99])


if __name__ == "__main__":
    unittest.main()
