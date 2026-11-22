"""Extract complete highway ways and related turn restrictions for a study area.

This prepares a local source file, not a routable graph. Access decisions and
splitting ways at shared nodes happen in subsequent processing.
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import osmium
from shapely.geometry import LineString, shape
from shapely.ops import unary_union
from shapely.prepared import prep


def extract(source, area_file, output):
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    data = json.loads(area_file.read_text())
    area = unary_union([shape(f["geometry"]) for f in data["features"]])
    if area.is_empty or not area.is_valid or area.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError("Study area must contain valid polygon geometry in WGS84.")
    prepared_area = prep(area)
    selected = set()
    counts = Counter()
    restrictions = 0
    output.parent.mkdir(parents=True, exist_ok=True)

    # Final output appears only after the extraction completes successfully.
    with TemporaryDirectory(dir=output.parent) as temporary:
        staged = Path(temporary) / "network.osm.pbf"
        with osmium.BackReferenceWriter(staged, source, remove_tags=False) as writer:
            print("Selecting roads and paths intersecting the study area…", flush=True)
            for obj in osmium.FileProcessor(source).with_locations():
                if not obj.is_way() or "highway" not in obj.tags:
                    continue
                # Retain all highway types and access tags for later decisions.
                if len(obj.nodes) < 2:
                    raise ValueError(f"Highway way {obj.id} has fewer than two nodes.")
                line = LineString([(n.lon, n.lat) for n in obj.nodes])
                if prepared_area.intersects(line):
                    writer.add_way(obj)
                    selected.add(obj.id)
                    counts[obj.tags["highway"]] += 1
            if not selected:
                raise ValueError("No highway ways intersect the study area.")

            print("Retaining related turn restrictions and referenced objects…", flush=True)
            for obj in osmium.FileProcessor(source):
                if not obj.is_relation():
                    continue
                kind = obj.tags.get("type", "")
                if kind != "restriction" and not kind.startswith("restriction:"):
                    continue
                if any(m.type == "w" and m.ref in selected for m in obj.members):
                    if any(m.type == "r" for m in obj.members):
                        raise ValueError(f"Restriction {obj.id} has unsupported nested relations.")
                    writer.add_relation(obj)
                    restrictions += 1

        # Validate that all retained way-node references resolve, including ways
        # added by the writer to complete restriction relations.
        total_ways = 0
        for obj in osmium.FileProcessor(staged).with_locations():
            if obj.is_way():
                for node in obj.nodes:
                    if not node.location.valid():
                        raise ValueError(f"Unresolved node {node.ref} in way {obj.id}.")
                total_ways += 1
        staged.rename(output)

    print(f"Selected highway ways: {len(selected):,}")
    print(f"Retained restriction relations: {restrictions:,}")
    print(f"Total ways including restriction references: {total_ways:,}")
    for highway, count in sorted(counts.items()):
        print(f"  {highway}: {count:,}")
    print(f"Saved: {output}")
    print("Source: OpenStreetMap contributors, ODbL. No database changes made.")


def main():
    cache = Path.home() / ".cache/tucson-bikes"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=cache / "arizona-latest.osm.pbf")
    parser.add_argument("--area", type=Path, default=cache / "tucson-routing-area.geojson")
    parser.add_argument("--output", type=Path, default=cache / "tucson-network.osm.pbf")
    args = parser.parse_args()
    extract(args.source, args.area, args.output)


if __name__ == "__main__":
    main()
