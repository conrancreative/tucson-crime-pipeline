# Documented bicycle infrastructure inventory

This milestone inventories source evidence for Tucson's incorporated boundary
plus a 3-mile buffer. It does not calculate riding eligibility, stress, directions,
or preferred journeys. The commute drafts are separate local inspection examples.

## Rebuild locally

The local OSM network must already be imported using `extract_osm_network.py`,
`sql/21_osm_network.sql`, and `import_osm_network.py`. The original Arizona PBF
must match the SHA-256 recorded in `osm_network_snapshots`. Existing agency
records come from `pull_pag_bikeways.py` and `sql/18_pag_bikeways.sql`.

From the repository root:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python prepare_bikeway_inventory.py
npm run preview
```

If a preview is already listening on port 8000, restart that process after Python
server changes instead of starting a second server. Reload `/routes/` after a
data rebuild. The runner applies `sql/22_bikeway_catalog.sql`, extracts OSM
bicycle relations, and rebuilds the catalog. It confirms a local
`tucson_bikes_local` database before writing. Other datasets are retained.

All derived inventory tables are replaced transactionally. Failure rolls back
the catalog replacement. Relation import is a separate transaction; a successful
relation refresh followed by a failed catalog build leaves the previous catalog
with an input-staleness warning. No hosted migration or scheduled workflow was
enabled in this milestone.

## Sources and evidence

| Source | Facility or identity evidence | Retained provenance |
| --- | --- | --- |
| PAG Metro Bike Map, layer 4 | `Display`, `BIKERTE_DS`, `NAME_BKWY`, `STREET`, line geometry | Original attributes, object ID, source URL, import time |
| OpenStreetMap ways | Cycleway tags, bicycle-street tags, route tags, bicycle permission | Original way ID and tags, source URL, PBF snapshot timestamp |
| OpenStreetMap bicycle/MTB relations | Name, reference, network, ordered member list and roles | Relation ID/version/edit time, complete members, original tags |
| PAG push-button crossings | Location, street/intersection, `SignalType` | Existing source layer record |
| Rider reports | Locations where observed infrastructure differs from source data | Explicitly labeled reports needing source verification |

PAG source: https://maps.pagregion.com/server/rest/services/TucsonMetroBikeMapVecLive/FeatureServer/4

Arizona OSM source: https://download.geofabrik.de/north-america/us/arizona/arizona-latest.osm.pbf

OSM route documentation: https://wiki.openstreetmap.org/wiki/Cycle_routes

OSM data is attributed to OpenStreetMap contributors under ODbL 1.0. Agency
data retains its own attribution. Source miles are shown separately by source;
overlapping source representations must not be summed as unique physical miles.

The OSM snapshot is November 21, 2026, 21:20:51 UTC. Agency import timestamps
describe downloads, not necessarily the age of facility information. Null source
edit dates remain unknown. The study boundary snapshot was published August 2025.

## Route identity across street changes

`config/bikeway_aliases.json` contains reviewed identity aliases. Internal IDs
are deterministic UUIDs from identity keys, independent of individual street
names. Registered keys remain stable when a source label changes. Unknown names
are grouped conservatively; no fuzzy name matching creates riding permission.
New names/renames need reviewed aliases to retain an existing identity.

For example, Treat Avenue Bikeway groups Treat, Christmas, Kleindale, and other
sections. PAG record 5375 follows La Madera Drive, East Plaza Drive, and Florence
Drive while labeling the full record `N TREAT AV`. The geometry and named
bikeway establish the candidate correspondence across those street changes.

An OSM route relation can overlap another route. Both memberships are retained.
An area network, such as University of Arizona paths, is identified separately
from a single named bikeway. Unnamed agency facilities remain in the inventory;
street-based groups are not presented as official named routes.

## Matching and continuity rules

- Clip source geometry to the study area while retaining source IDs and links.
- Compare geometry in UTM zone 12N meters (EPSG:32612).
- Candidate matching uses an 8-meter corridor and at least 80% coverage of one
  participating section. Coverage of each section is retained separately.
- Different street names require a named agency bike boulevard, a tighter
  6-meter/90% geometric correspondence, and direction alignment within 25 degrees.
- Unnamed geometry also requires alignment. A short perpendicular intersection
  must not become a facility match.
- A footway can match agency shared-use-path geometry, but cannot inherit an
  adjacent roadway's lane or boulevard designation.
- Matches are candidates, not access decisions. A short agency facility matched
  to part of a long OSM way does not establish the whole way as a bike facility.
- Continuity counts source line groups whose endpoints lie within 10 meters.
  These counts can reflect branches, clipping, or mapping differences. They do
  not prove physical gaps, grade-separated connections, or routing connectivity.
- OSM relation memberships are explicit source evidence, independent of the
  geometry matcher. Missing local members remain counted and inspectable in
  the full relation record. Long-distance routes are not silently truncated.

Source conflicts remain visible. The approved future eligibility policy lets a
confirmed existing bicycle facility override conflicting OSM `bicycle=no` or
`bicycle=dismount`, with the reason retained. Sidewalks still need shared-use-path
evidence. This inventory does not implement that eligibility or route ranking.

## Map inspection

The named-bikeway search supports route names, source aliases, and street names.
Selecting a route highlights its available sections across street changes.
Agency geometry is solid and OSM geometry dashed. Source and facility-type
toggles work together. Popups expose provenance, status, and original attributes.

Coverage and review lists source discrepancies with location controls, optional
review markers, and a downloadable JSON audit. The study-area button returns to
the full work area. Private commute drafts are collapsed and off by default.

The preview marks the inventory stale when source snapshots or alias/review
configuration change. Rebuild before treating that catalog as current.

## Initial audit, November 22, 2026

| Measure | Count |
| --- | ---: |
| Imported agency records | 8,236 |
| Agency sections within the study area, all represented | 6,394 |
| Agency records outside the area or touching only its boundary | 1,842 |
| Agency sections with OSM geometry candidates | 5,211 |
| Agency sections needing matching review | 1,183 |
| OSM sections with bicycle evidence | 7,105 |
| Relevant OSM bicycle-route relations | 33 |
| Named bikeway catalog entries | 126 |
| Source sections in the combined inventory | 13,499 |
| Cross-source geometry candidate pairs | 7,482 |

There are 4,849 agency sections without a named bikeway label; many still have
street names. They are retained. OSM permission-only sections are labeled as
permission evidence, not dedicated bicycle infrastructure.

The initial review includes 14 OSM bicycle-tag conflicts, 123 footways needing
shared-use verification, 59 named-route continuity reviews, 5 relation-member
availability reviews, and 5 nonstandard-status sections. An additional 3,828 OSM
bicycle-evidence sections have no agency geometry match. These are review
categories, not a count of unsafe or missing facilities. Some categories overlap.

Five additional name-identity reviews pair similar agency/OSM route names with
substantial shared geometry candidates, including Rillito, Mountain Avenue,
Aviation, Cañada del Oro, and Liberty. They are not automatically merged: shared
sections can belong to intentionally different routes. These reviews are found
by a general name-and-geometry rule rather than commute-specific waypoints.

Two rider reports remain explicit: the newer 6th Avenue protected lane and the
straight University approach across Bear Down toward Old Main. The latter is
tagged `bicycle=dismount` in OSM and absent from its named bicycle-route relation.
The draft commute follows the reported physical route without changing source
data or turning that observation into a map-wide permission override.

Individual draft scenarios can enable mapped one-way/roundabout checks and
exclude unverified footways. `?example=<scenario-id>` opens a saved example on
the map; this is an inspection aid, not a start/end routing API. Business endpoint
pins and approximate street-access points are recorded separately.

## Verification and SQL inspection

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_bikeway_inventory.py' -v
```

The tests cover alias identity, OSM parsing and nested membership, scope
accounting, street-name changes, partial coverage, sidewalk separation, and
perpendicular crossings. Local builds also verify that every source section has
catalog membership and that agency counts reconcile before committing.

```sql
select name
  , kind
  , source_names
  , details
from preview_bikeway_catalog
where name ilike '%treat%';

select issue_type
  , count(*) as review_items
from preview_bikeway_audit
group by 1
order by 2 desc;
```

All raw, catalog, matching, and audit tables remain private, with RLS enabled and
client-role grants revoked. The local preview reads them through its server-side
database connection. No private database credentials are sent to the browser.
