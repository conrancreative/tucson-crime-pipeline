# Session handoff — November 22, 2026

## Resume here

Tom is stopping for today. Continue refining the accuracy and usability of the
documented infrastructure map before proceeding to a production routing engine.
The working branch is `bicycle-access-rules`; save/push this checkpoint without
merging into `bike-route-data` or production. Check Git status when resuming.

Read this file, `PROJECT_PLAN.md`, and `docs/BIKEWAY_INVENTORY.md`. The current
checkout and local database remain `/Users/tom/tucson-crime-pipeline` and
`tucson_bikes_local`. Production is unchanged.

## What is working

- Scope: Tucson city boundary plus a 3-mile buffer, with configurable coverage.
- Local infrastructure inventory: 6,394 agency sections, 7,105 OSM bicycle-
  evidence sections, 33 OSM bicycle/MTB route relations, and 126 named bikeways.
- All imported in-scope agency sections are represented. This establishes source
  accounting, not real-world completeness or riding permission.
- Private tables and local preview support named-route search, source toggles,
  provenance/raw attributes, review markers, and an audit JSON download.
- Named identities span street-name changes. Reviewed aliases have stable IDs.
  Additional possible aliases are flagged rather than silently merged.
- Matching uses geometry and alignment, without transferring roadway bicycle
  status to an adjacent sidewalk or applying partial matches to entire roads.
- The catalog detects changed source/config inputs and supports transactional
  rebuilds. No new production API grants or scheduled jobs were enabled.

## Data reviews remaining

- 1,183 agency sections lack accepted OSM geometry candidates.
- 3,828 OSM bicycle-evidence sections lack agency geometry matches.
- 14 bicycle-tag conflicts, 123 footway/shared-use reviews, 59 named-route
  continuity reviews, 5 route-member availability reviews, 5 nonstandard-status
  reviews, and 5 possible route-name aliases are documented.
- These categories overlap. They are not counts of unsafe or missing paths.
- The newer 6th Avenue protected lane needs refreshed source geometry and a
  verified completed extent. Do not label all of 6th Avenue protected.
- The straight East University connection across Bear Down toward Old Main is
  reported by the rider as a bike connection. OSM says bicycle=dismount on way
  32967558, and its named bicycle-route relation omits that way. This discrepancy
  remains a review item, not a silent source edit.
- Examples of potential name aliases: Rillito River Park/Path, Mountain Avenue,
  Aviation, Cañada del Oro, and Liberty. Check extents and shared geometry before
  merging identities; overlap can be intentional.

## Agreed rules and product direction

- Eligibility evidence order: verified existing bike infrastructure, explicit
  OSM bicycle permission, then speed and lanes for ordinary streets. Crossings
  affect all routes. Ordinary-street thresholds remain undecided.
- Confirmed existing bike routes/lanes/boulevards/shared paths may override OSM
  bicycle=no or bicycle=dismount. Retain the conflict and reason. This does not
  override closures, other access restrictions, or travel direction.
- Sidewalks require shared-use-path evidence, even if bicycle=yes is present.
- Named bikeways retain identity across street changes and separate crossing
  links. Shared names do not establish physical connections by themselves.
- The routing model will use Tom's own matrix. Keep PAG stress and federal road
  class separately for comparison; federal classification is not bicycle stress.
- Eventually show up to three materially different alternatives: lower stress,
  balanced, and more direct. These are different cost preferences, not mandatory
  differences in safety or infrastructure. Do not manufacture alternatives.
- Score riding segments and intersection movements separately. Surface the
  hardest crossing rather than hiding it inside an average stress score.
- User corrections become general rules and acceptance tests. Hand-pinned
  commutes are inspection examples, not proof that an engine can discover routes.
  Evaluate unseen trips after building the shared model.

## Local route examples

The existing commute examples were corrected for Treat/Christmas/La Madera,
the Fort Lowell separate connection and BikeHawk, and the University/Old Main
connection. They remain physical traces, without a complete eligibility model.

A new assisted proposal goes from Tucson Hop Shop to Café Passe:

```text
Dodge south → Glenn west → Mountain south → James E. Rogers Way / Park
→ University west → 4th Avenue south
```

It is approximately 5.71 street miles, with business pins separate from street
access points (about 73 m at Hop Shop and 13 m at Café Passe). Nine mapped signal
or stop-control locations are marked. Ordinary traffic signals are not HAWKs.
Glenn is a shared-road bike-route corridor, not a verified protected lane.

That example opts into mapped one-way/roundabout checks and exclusion of
unverified footways. Three applicable simple turn restrictions were inspected
with no violation found; this is not a complete turn/conditional-access engine.
The route was proposed through assisted corridor selection, not an automatic
start/end route-ranking service.

Open:
http://localhost:8000/routes/?example=hop-shop-cafe-passe&context=off

The optional `context=off` hides background facilities/stations/crossings for
the example view. It does not change the all-facilities landing-page default.

Private scenarios and generated traces are outside Git:

```text
~/.cache/tucson-bikes/commute-scenarios.json
~/.cache/tucson-bikes/commute-traces.geojson
```

A second copy is saved outside the disposable cache:

```text
~/.local/share/tucson-bikes/session-checkpoints/2026-11-22/
```

Do not commit personal commute locations. The original verified Arizona PBF
and study-area geometry remain in the external cache; database data is persisted
in the local PostgreSQL installation.

## Commands and checks

Put tools on PATH if required:

```bash
export PATH="$HOME/.local/share/dev-tools/bin:$PATH"
```

Refresh inventory from the existing local network and matching source snapshot:

```bash
.venv/bin/python prepare_bikeway_inventory.py
```

Regenerate private physical examples after changing their local configuration:

```bash
.venv/bin/python trace_local_routes.py
```

Start the preview only if port 8000 is free:

```bash
npm run preview
```

The preview was left running. Check the existing process before starting another.
Static preview responses now disable caching; the routes stylesheet also has a
version query so older cached CSS does not mask the current layout.

Validation completed: 16 unit tests, Python/JS/shell checks, CSS build, live API
and source-accounting checks, RLS/grant inspection, repeat local builds, and
browser checks of search, source filters, audit location/download, and the new
route overlay. The pipeline remains local-only.

## First task tomorrow

Review the infrastructure together on the map. Start with known corridors and
the campus/6th Avenue source gaps, then sample unrelated areas to avoid tuning
only to Tom's commute. Use the audit to distinguish missing data, identity
differences, geometry-match limitations, and actual connectivity questions.
Agree on evidence before changing source aliases or claiming a facility type.

The future production sequence is ingestion → documented/matched sections →
connected graph with access/direction/crossing attributes → versioned route costs
→ routing service → frontend alternatives and explanations. The graph and service
are not implemented yet. No language model is needed to select the final route.
