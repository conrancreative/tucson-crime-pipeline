# Tucson Bikes foundation plan

Updated November 18, 2026.

## Purpose and decisions

Build one Tucson biking site with theft exploration, infrastructure and route
planning, and data analysis. Share geographic data, map components, navigation,
and product measurement. Each feature has its own entry point.

The production domain is `bikes.thomaspconran.com`. The beta domain is
`beta.thomaspconran.com`. The earlier testing subdomain proposal is superseded.

Tom approved the umbrella name **Tucson Bikes**, technical slug `tucson-bikes`,
and SQL prefix `tucson_bikes`. Apply resource renames as individual learning steps.

## Current checkpoint

- `bike-route-data` is saved on GitHub through `1a26ba7`.
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
