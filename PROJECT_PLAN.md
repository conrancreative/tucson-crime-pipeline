# Tucson Bikes foundation plan

Updated November 22, 2026.

Latest resume notes: [Session handoff](docs/SESSION_HANDOFF.md). Prioritize
infrastructure accuracy and usability before starting the production router.

## Purpose and decisions

Build one Tucson biking site with theft exploration, infrastructure and route
planning, and data analysis. Share geographic data, map components, navigation,
and product measurement. Each feature has its own entry point.

The production domain is `bikes.thomaspconran.com`. The beta domain is
`beta.thomaspconran.com`. The earlier testing subdomain proposal is superseded.

Tom approved the umbrella name **Tucson Bikes**, technical slug `tucson-bikes`,
and SQL prefix `tucson_bikes`. Apply resource renames as individual learning steps.

## Routing data preparation decisions

- V1 routing coverage targets the Tucson city boundary plus a 3-mile buffer.
  Keep the import boundary configurable for later expansion to Pima County.
  Evaluate an Arizona OpenStreetMap extract for the base network and preserve
  connectivity around the extraction boundary. Existing agency-layer coverage
  remains unverified. Local OSM extraction and ingestion are implemented and
  verified: 750,055 nodes, 144,688 ways, and 1,154 restriction relations over a
  551.3-square-mile study area. Routing graph construction remains future work.
- Calculate bicycle stress using our own versioned rules and matrix. Preserve
  PAG combined and left/right scores for comparison. Federal functional road
  classification describes road role and is distinct from a bicycle stress score.
- Local audit found 64,106 PAG bicycle-stress segments. Of these, 2,882 have
  zero FINT/TINT IDs, zero speed and lanes, blank direction, and missing street
  names: 2,834 Shared-Use Path, 24 Bike Boulevard, and 24 Bike Lane records.
  These endpoint IDs cannot establish connectivity. Geometry remains available.
- The remaining 61,224 segments have nonzero endpoint IDs and populated road
  IDs, but physical connectivity and travel-direction semantics remain unverified.
- Twelve records on W Tangerine Rd and W Twin Peaks Rd have combined stress 1
  and left/right stress 4. Preserve these values and flag the difference.
- Ask Tucson GIS for the authoritative shared-use-path network, endpoint field
  definitions, documented zero-value semantics, connection and grade-separation
  data, bicycle access/direction restrictions, countywide coverage, and refresh
  metadata. The inspected source is PAG's Level_of_Traffic_Stress MapServer,
  layer 7, BLTS 1 (Lowest Stress), downloaded November 18, 2026.
  Source: https://maps.pagregion.com/server/rest/services/RATP/Level_of_Traffic_Stress/MapServer/7
  Network extract candidate: https://download.geofabrik.de/north-america/us/arizona.html

### Approved V1 bicycle eligibility policy

- Evaluate candidates in this order: verified existing agency bicycle
  infrastructure, explicit OSM bicycle permission, then speed and lanes for
  ordinary streets. Evaluate crossings across all candidate routes. Ordinary
  street speed/lane thresholds are not yet chosen; missing values are unknown.
  Separate legal/access eligibility from our recommendation criteria. Neither
  infrastructure nor explicit permission alone establishes low stress.
- Explicit OSM bicycle permission (such as bicycle=yes or designated) supports
  bicycle eligibility, subject to the sidewalk rule below and other applicable
  restrictions. This does not yet implement travel-direction or turn rules.
- A verified match to an existing Tucson/PAG bicycle route or facility also
  supports eligibility. Mere inclusion in the bicycle-stress dataset, a nearby
  facility, or a planned facility does not establish a match or permission.
- Tom explicitly chose to let a verified existing agency bicycle-route match
  override OSM bicycle=no or bicycle=dismount. Retain the original tags and record the conflict,
  supporting agency record, and override reason for inspection. This override
  applies to that bicycle tag and does not blanket-override other restrictions.
- Sidewalks are excluded unless identified as shared-use paths, including the
  relevant downtown facilities. Explicit bicycle=yes alone does not override
  this sidewalk requirement. Match the actual facility, not an adjacent road.
- Preserve the source, reason, and confidence for each agency match. Matching
  candidates and a source-documented inventory are implemented on
  bicycle-access-rules. Riding eligibility and ranking remain future work.
- Local commute drafts now inspect genuine shared OSM nodes and agency bikeway
  geometry. They are undirected physical traces, not recommended directions.
  Private scenarios and output remain in ~/.cache/tucson-bikes, outside Git.
- Use NAME_BKWY as a source grouping label across street changes, retaining
  individual OBJECTIDs. It is not a documented persistent route identifier.
  Treat Avenue Bikeway record 5375 follows La Madera Drive, East Plaza Drive,
  and Florence Drive while the agency STREET label remains N TREAT AV.
  Name disagreement alone must not discard a close, aligned geometry match.
  Sidewalks cannot inherit adjacent roadway status through proximity.
- The draft Fort Lowell connection uses OSM ways 1222331041, 1443949517,
  and 1443949516, with PAG crossing record 7 identifying BikeHawk. Preserve
  the distinction between the user-reported shared path and OSM's residential
  classification of the separate bicycle=yes connection.
- Rider correction for the campus example: stay on the East University
  connection across Bear Down Bike Path and continue around Old Main rather
  than taking the earlier left. The local draft now follows that connection.
  OSM way 32967558 has bicycle=dismount; retain it as source disagreement,
  not an automatic exclusion if a confirmed existing bicycle facility supports
  the segment. Rider observations remain distinct from agency source evidence.

### Generalizing route eligibility and preference

- Build shared facility matching and eligibility decisions for the network;
  commute checkpoints are inspection examples, not map-wide routing rules.
- Read existing facility designations from preview_pag_bikeways.facility_type
  (raw Display), facility_description (raw BIKERTE_DS), and bikeway_name
  (raw NAME_BKWY). Preserve source record IDs and dates. Bicycle-stress scores
  and federal road classes are separate attributes, not facility permission.
- Group named bikeways under stable internal IDs with reviewed source-name
  aliases. Match physical geometry and connected nodes across street-name
  changes and separate crossing/path links; street-name equality is supporting
  evidence, not a requirement. Do not infer sidewalk status from nearby roads.
- A confirmed existing bicycle facility is affirmative eligibility evidence
  ahead of conflicting OSM bicycle=no/dismount. Store the conflict and decision
  reason separately from original tags. Sidewalks still require shared-use-path
  evidence. Other closures, access, direction, and turn rules remain separate.
- Eligibility admits candidates. Route preference then considers facility
  quality/continuity, speed and lanes on ordinary streets, crossing difficulty,
  distance, and detour tolerance. Designated routes are preferred candidates,
  not automatically the best complete journey irrespective of crossings.
- Turn rider feedback into saved acceptance cases: Treat continues through
  Christmas/La Madera street changes; Fort Lowell uses the separate connection
  and BikeHawk; campus continues across Bear Down toward Old Main; Park/Lester
  is an alternative to the problematic Blacklidge/Euclid crossing. Confirm
  route rankings with Tom before using them as expected routing outcomes.
- A supplemental relation importer now preserves 33 relevant OSM bicycle/MTB
  relations with full ordered membership, parent identities, source versions,
  and explicit accounting of members unavailable in study-area geometry.

### Documented inventory checkpoint, November 22

- Run `.venv/bin/python prepare_bikeway_inventory.py` against the existing local
  OSM network to refresh relation metadata and the private catalog in one command.
- The inventory represents all 6,394 imported agency sections within the study
  area and 7,105 OSM sections with bicycle evidence. It includes 126 named
  bikeways, with stable reviewed identities spanning street-name changes.
- The initial audit has 1,183 agency sections without accepted OSM geometry
  candidates, 14 bicycle-tag conflicts, and 59 named-route continuity reviews.
  These are source/matching reviews, not counts of missing or unsafe facilities.
- `/routes/` provides named-bikeway search, source controls, raw-attribute and
  provenance popups, review markers, and an audit JSON download. Commute drafts
  remain separate, collapsed, and off by default. No route engine was added.
- Source changes and alias/review configuration changes mark the derived
  inventory stale. Catalog replacements are transactional; raw sources remain.
- See docs/BIKEWAY_INVENTORY.md for source definitions, thresholds, limitations,
  reproducible commands, SQL inspection, and validation. Source accounting is
  verified; real-world completeness still needs field and user review.

## Current checkpoint

- `bike-route-data` is saved on GitHub through merge `6af7d2e`. The documented
  inventory and route inspection work are committed and pushed on
  `bicycle-access-rules` through implementation checkpoint `e26e2d5`; this branch
  has not been merged. See the session handoff for tomorrow's starting point.
- The local infrastructure map includes bikeways, crossings, and TuGo stations.
- `tucson_bikes_local` contains 80,300 newly imported roadway-context records.
- The roadway importer, private preview views, setup script, and future daily
  workflow step are committed. Production has not received those schema changes.
- The theft site is the currently deployed public frontend. The local playground
  serves bike data through `preview_server.py`; theft tabs read hosted Supabase.
- Beta DNS, hosting, database, tester access, feedback, and product-event
  collection are planned work.
- `shared-foundation` starts from the saved infrastructure checkpoint.

## Naming conventions

Use lowercase kebab-case for repositories, branches, and hosted project labels.
Use lowercase snake_case for databases, SQL objects, fields, and event names.
Use an explicit environment suffix for environment-specific resources.

| Resource | Approved name |
| --- | --- |
| GitHub repository | `conrancreative/tucson-bikes` |
| Mac checkout | `/Users/tom/tucson-bikes` |
| Local PostgreSQL database | `tucson_bikes_local` |
| Disposable automated-test database | `tucson_bikes_test` |
| Beta Supabase project label | `tucson-bikes-beta` |
| Production Supabase project label | `tucson-bikes-production` |
| SQLTools local connection | `LOCAL — Tucson Bikes` |
| SQLTools beta connection | `BETA — Tucson Bikes` |
| SQLTools production connection | `PRODUCTION — Tucson Bikes` |

Hosted Supabase databases retain their physical database name `postgres`.
Project labels, connection labels, and explicit environment configuration identify
the hosted environment. Project IDs and service hostnames remain configuration.

Tables describe their domain and purpose. Preserve the established `raw_`,
`int_`, `mart_`, and `preview_` conventions while we evolve the architecture.
Examples include `raw_pag_bikeways`, `ref_wards`, and `preview_bicycle_stress`.
Future product records can use names such as `feedback_submissions`,
`product_events`, and `routing_model_versions`. Environment separation happens
at the database/project boundary, so table names can match between environments.

## URLs and frontend structure

| Production URL | Purpose |
| --- | --- |
| `/` | Feature landing page |
| `/thefts/` | Theft map and table |
| `/routes/` | Infrastructure exploration and route planning |
| `/data/` | Analysis, dataset documentation, and methodology |
| `/about/` | Project background, sources, limitations, and feedback |

The beta domain initially opens the standalone routes experience. Feature paths
inside the beta app should support promotion to the production `/routes/` entry.
API base URLs and deployment paths are configuration.

Proposed repository layout, introduced in small changes:

```text
apps/site/       Landing page and public information
apps/thefts/     Theft frontend
apps/routes/     Infrastructure and routing frontend
shared/map/     Basemap, wards, geographic interactions
shared/ui/      Styling and reusable interface components
shared/data/    Data clients, loading, errors, refresh metadata
sql/            Reproducible schema changes and exploration
```

Move Python ingestion into a dedicated directory when needed, updating imports,
commands, and workflow paths together. Keep working entry points usable during
the transition. Extract shared components when both features need them.

## Environments and data

Local development uses the existing PostgreSQL/PostGIS installation and local
data snapshot. Beta gets a dedicated Supabase project containing real source
imports, derived data, tester access, feedback, and events. Production initially
continues in the existing Supabase project. Review capacity and access boundaries
before deploying the route feature there.

Raw and internal datasets remain private. Publish selected, documented read
surfaces for frontend use. Administrative credentials stay server-side. Feature
feedback and usage records have authenticated write paths and admin-only review.

Treat browser location as optional. Support manually selected or entered start
and destination points plus a user-triggered location button. Exact-location
retention requires an explicit collection decision. Keep precise trip locations,
emails, and free-text feedback out of Google Analytics.

## Pipelines and releases

- TuGo imports run hourly, with latest availability and timestamped history.
- Infrastructure imports run daily, preserving the last validated snapshot on
  failure. Store source edit dates separately from successful import timestamps.
- Derived matches and future routing graphs identify their input data versions.
- Record import health, counts, failures, and freshness. Alert on meaningful
  failures or stale data, and show freshness in the app.
- Frontend releases are deliberate beta checkpoints. Test data, credentials,
  feedback, and tester identities stay associated with their environment.
- GitHub scheduling needs a workflow on the default branch. Plan a reviewed
  scheduler targeting beta independently of production frontend deployment.
- Update and verify the Pages workflow when frontend files move. It currently
  uploads `web/` and does not build the ignored `web/styles.css` asset.

## Product learning and discovery

Gate beta with invited accounts and email sign-in. Store feedback before sending
an email notification, with retry handling. Attach app version, relevant data
version, and voluntarily supplied feature/location context.

Use a validated product-event endpoint and one frontend tracking interface.
Record event IDs for deduplication, session IDs, environment, app version, and
relevant structured properties. Start with map-load success, filter changes,
feature inspection, errors, and feedback. Add routing events with the routing
milestone. Agree on retention and tester-facing collection information before
external testing. GA4 can supplement acquisition reporting.

Public pages need useful HTML, stable URLs, titles, descriptions, headings,
canonical URLs, sitemap entries, accessibility, and accurate structured metadata.
Document dataset fields, provenance, freshness, and reuse terms for people and
programmatic consumers. Beta requires access control and noindex configuration.
Verify existing links and search behavior during the theft-homepage transition.

## Sequence and planning range

Tom can commit to one dedicated session per day. Use 60–90 minutes as a planning
assumption until actual session lengths are established. Target 28–42 daily
sessions, approximately 4–6 weeks, for a tested routing beta. External infrastructure
testing can begin earlier. Routing-network quality is the largest uncertainty;
re-estimate after GIS matching. These are planning targets, with milestone
completion determined by the evidence below.

| Milestone | Target range | Evidence of completion |
| --- | --- | --- |
| Naming transition and ward-layer lesson | Sessions 1–2 | Verified names/configuration; ward data traced to map |
| Standalone routes and shared map layer | Sessions 3–5 | Local entry points work; wards are reusable |
| Hosted beta and real pipelines | Sessions 6–8 | Gated beta loads real data; hourly/daily jobs verified |
| Feedback and product measurement | Sessions 9–11 | Feedback reaches database/email; events queryable |
| GIS matching and validation | Sessions 12–17 | Map exposes stress, speed, class, and match confidence |
| Routing prototype | Sessions 18–28 | Valid network and reproducible route alternatives |
| Tester calibration and release review | Sessions 29–35 | Evaluated trips, model versions, and release decision |

Keep sessions 36–42 available for data corrections, connectivity issues, and
tester-driven changes. An earlier prototype may be ready around session 28;
release depends on validation. Aim to invite infrastructure testers after session
11, once access, feedback, and measurement work end to end.

Initial testers can evaluate infrastructure before routing is available.

## Learning workflow

Each lesson covers one observable outcome. Explain the concept, identify the
files and data, give Tom one action, wait for his result, explain the result,
then verify and commit a working checkpoint. Automate repeated steps after he
has performed and understood one example.

The first lesson traces `ref_wards` through `api_wards`, a data request, and the
Leaflet ward layer. The next lessons cover frontend entry points, shared modules,
configuration, ingestion transactions, hosted access, spatial joins, product
events, and routing costs. Alternate teaching sessions with explicitly scoped
implementation sessions.

Use this plan and local `AGENTS.md` as session context. Inspect targeted diffs,
reuse existing code, run checks relevant to each change, and keep progress
updates concise. End sessions with current branch, checkpoint, and next action.

## Safe naming transition

1. Naming is approved. Explain each resource change before Tom performs it.
2. Check active sessions and local changes, record counts, and back up local data.
3. Rename the local database from a maintenance connection. Update `.env`,
   SQLTools, preview-server environment checks, examples, and setup instructions
   together. Verify Python, SQLTools, and the map against the renamed database.
4. Rename the repository and checkout in a separate lesson. Update remotes,
   workflow references, documentation, and editor paths; verify Git and commands.
5. Create the beta project and hosting with the reviewed names. Keep actual
   project IDs, credentials, and target URLs explicit in environment configuration.
6. Rename the production project display label during a separate reviewed step.
   Verify the actual connection endpoints and deployed configuration.

This milestone documents the foundation. Resource renames, provisioning, and
application restructuring follow as individual learning steps.
