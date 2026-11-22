import unittest

from trace_local_routes import can_trace


class LocalTraceTests(unittest.TestCase):
    def edge(self, tags, matches=None):
        return {"tags": tags, "forward": (1, 2), "agency_matches": matches or []}

    def test_oneway_and_bicycle_exception(self):
        constraints = {"respect_oneway": True}
        edge = self.edge({"oneway": "yes"})
        self.assertFalse(can_trace(edge, 2, 1, constraints))
        edge["tags"]["oneway:bicycle"] = "no"
        self.assertTrue(can_trace(edge, 2, 1, constraints))

    def test_roundabout_implies_direction(self):
        self.assertFalse(can_trace(self.edge({"junction": "roundabout"}), 2, 1, {"respect_oneway": True}))

    def test_bicycle_yes_does_not_turn_sidewalk_into_shared_path(self):
        edge = self.edge({"highway": "footway", "bicycle": "yes"})
        self.assertFalse(can_trace(edge, 1, 2, {"exclude_unverified_footways": True}))
        edge["agency_matches"] = [{"facility_type": "Shared-Use Path"}]
        self.assertTrue(can_trace(edge, 1, 2, {"exclude_unverified_footways": True}))

    def test_source_backed_dismount_conflict_is_retained_as_candidate(self):
        edge = self.edge({"bicycle": "dismount", "highway": "pedestrian"})
        self.assertFalse(can_trace(edge, 1, 2, {"respect_bicycle_conflicts": True}))
        edge["agency_matches"] = [{"facility_type": "Bike Boulevard"}]
        self.assertTrue(can_trace(edge, 1, 2, {"respect_bicycle_conflicts": True}))


if __name__ == "__main__":
    unittest.main()
