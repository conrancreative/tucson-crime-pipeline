# Tucson Bike Crime Pipeline

A data pipeline and (soon) web map showing **reported bicycle thefts in Tucson, AZ**,
sourced live from the Tucson Police Department's public ArcGIS layers.

The end goal: a filterable map for local cyclists — where bikes get stolen, when,
and how often it's solved.

---

## Architecture

```
Tucson PD ArcGIS layers ──► pull_tpd_incidents.py ──► raw ──► transform ──► reporting ──► (API + map)
   (spatial incident            (Python, bike-only)   jsonb    SQL view    materialized
    layers, OFFENSE=0606)                                                    views
```

- **Raw** (`raw_tpd_incidents`) — untouched ArcGIS features stored as `jsonb`, keyed on `INCI_ID`.
- **Transform** (`int_incidents`, a *view*) — flattens jsonb to typed columns, parses dates,
  extracts lat/lon, sets the `is_bicycle` flag. Always reflects raw live; no storage.
- **Reporting** (`mart_bike_crimes`, `mart_bike_stats`, *materialized views*) — the fast,
  public-facing layer the website/API reads. Stored snapshots; must be refreshed after each pull.

Scope is deliberately **bike-only** (`OFFENSE='0606'`, "Larceny - Bicycles"), filtered at the
source — ~7,500 rows, tiny and fast.

---

## Prerequisites (one-time)

- **PostgreSQL** running locally with a `tucson_crime` database.
- **Python virtualenv** with dependencies:
  ```bash
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  ```
- **`.env`** file in the project root (NOT committed) containing the DB connection string:
  ```
  DATABASE_URL=postgresql://localhost/tucson_crime
  ```

---

## Running it locally

> Run every command from the project root (`cd` here first, or use the VSCode built-in
> terminal, which opens here automatically). The commands use relative paths.

### First-time build (backfill)

```bash
# 1. Create the landing tables (idempotent)
psql "$DATABASE_URL" -f sql/01_raw.sql

# 2. Ingest all historical bike thefts with geometry (upserts on INCI_ID; safe to re-run)
.venv/bin/python pull_tpd_incidents.py backfill

# 3. Build the transform layer (creates the int_incidents view)
psql "$DATABASE_URL" -f sql/03_transform.sql

# 4. Build the reporting layer (creates the materialized marts + indexes)
psql "$DATABASE_URL" -f sql/04_reporting.sql
```

*(`$DATABASE_URL` is read from your shell; if it's not exported, use the literal
`postgresql://localhost/tucson_crime`.)*

### Verify

```bash
psql "$DATABASE_URL" -f sql/inspect.sql      # walks every layer with counts + samples
```

Or explore interactively in VSCode using `sql/scratch.sql` (SQLTools "tucson crime" connection).

### Ongoing refresh (what the daily job runs)

```bash
# Pull only the rolling 45-day layer (full schema), upsert into raw
.venv/bin/python pull_tpd_incidents.py refresh

# Re-bake the public snapshots so new data becomes visible
psql "$DATABASE_URL" -c "refresh materialized view mart_bike_crimes; refresh materialized view mart_bike_stats;"
```

Run a full `backfill` occasionally (e.g. monthly, or when TPD publishes a new year-layer) to
reconcile case-status changes and corrections on records older than 45 days.

---

## Key concepts

| Thing | What it is | Fresh automatically? |
|---|---|---|
| `raw_tpd_incidents` | jsonb landing table, upsert on `INCI_ID` | — |
| `int_incidents` | **view** (a saved query over raw) | ✅ yes, live |
| `mart_bike_crimes` / `mart_bike_stats` | **materialized views** (stored snapshots) | ❌ no — run `refresh materialized view` |

- **Upsert** (`ON CONFLICT (inci_id) DO UPDATE`) makes every pull idempotent — re-runs never duplicate.
- Time comes solely from `DATETIME_OCCU` (epoch ms, populated on every record); `occurred_at`
  is Arizona time (UTC−7, no DST).

---

## Schema / data dictionary

The pipeline is four objects, chained raw → transform → reporting:

```
ArcGIS ──► raw_tpd_incidents ──► int_incidents ──►  mart_bike_crimes   ──► map (dots)
 puller       TABLE                VIEW              MATERIALIZED VIEW
            jsonb landing       live, 0 bytes    └►  mart_bike_stats    ──► trend charts
                                                     MATERIALIZED VIEW
```

| Object | Type | Role |
|---|---|---|
| `raw_tpd_incidents` | table | Landing zone. One row per theft, keyed on `inci_id`, full ArcGIS feature as `jsonb`. The puller writes here; source of truth. |
| `int_incidents` | view | Cleaner. Live query over raw — flattens jsonb into typed columns (`occurred_at`, `lat`/`lon`, `ward`, `parcel_group`, `*_az`, `is_bicycle`). Stores nothing; always current. |
| `mart_bike_crimes` | materialized view | Map feed. Stored snapshot from `int_incidents`, bike-only + geocoded, one row per point. What the site's map reads. |
| `mart_bike_stats` | materialized view | Trend feed. Pre-aggregated counts by year/month/ward for charts. |

How they interact: the puller **writes** `raw_tpd_incidents`; `int_incidents` reflects it **automatically** (live view); the two marts are **stored snapshots** that only update when `refresh materialized view` runs — which the puller does at the end of every pull. So the cycle is **write raw → refresh marts**, with the view carrying data through in between.

---

## Data source notes

- Source: Tucson `PublicMaps/OpenData_PublicSafety/MapServer` spatial incident layers
  (per-year `TPD_INCIDENTS_PUBLIC_YYYY` + 45-day `TUCSON_INCIDENTS_PUBLIC_45D`).
- The `current` layer (id 24) is **deliberately excluded** — it lacks `DATETIME_OCCU` and the
  parcel/census fields, and would degrade records on conflict.
- PAG's public Tucson Metro Bike Map Bikeways layer (FeatureServer layer 4) is mirrored to
  `raw_pag_bikeways`. `preview_pag_bikeways` and `preview_pag_bikeways_summary` are private
  database inspection views and are not used by the website.
- The 45-day window is by **report** date, so a few records have an `occurred_at` in the prior year.
- **Neighborhood labels:** the 2018-2025 year layers tag ~10-25% of thefts with a TPD police-team
  code (`T101`..`T408`) or a blank instead of a neighborhood name. `mart_bike_crimes` fills only those
  placeholders by point-in-polygon against the city's `NEIGHBORHOODS_ALL` layer (`ref_neighborhoods`,
  loaded by `pull_neighborhoods.py`); real reported names are never overridden (2026 coordinates are
  privacy-offset, so the reported name is more accurate). The original label stays in
  `neighborhood_reported`; `neighborhood_source` = `reported` | `spatial` | `unassigned` (outside city limits).

### PAG Bikeways preview

Apply the schema once, then load or refresh the source snapshot:

```bash
./apply_sql.sh sql/18_pag_bikeways.sql
./.venv/bin/python pull_pag_bikeways.py
```

Inspect a few segments or the source's class/mileage totals in SQL:

```sql
select * from preview_pag_bikeways order by objectid limit 20;
select * from preview_pag_bikeways_summary;
```

### Full PAG bike map + Tugo data

The pipeline also mirrors the other six layers in PAG's Tucson Metro Bike Map and the
legacy Tugo station layer, preserving full source GeoJSON in `raw_pag_bikemap_features`.
`preview_pag_bikemap_features` combines those features with the primary bikeways layer;
`preview_pag_bikemap_layer_summary` reports each source layer's count and geometry coverage.

Tugo's public GBFS manifest is used to discover and store every advertised feed, including
station inventory and live station status, vehicle types, pricing plans, regions,
geofencing zones, and system information. Complete response payloads are retained in
`raw_tugo_gbfs_snapshots`; `preview_tugo_gbfs_feeds` exposes the latest snapshot of each
feed and `preview_tugo_stations` joins the latest station information and status. The
scheduled job captures one snapshot per day, so it is not a continuous availability history.

```bash
./apply_sql.sh sql/19_pag_bikemap_and_tugo.sql
.venv/bin/python pull_pag_bikemap_layers.py
.venv/bin/python pull_tugo_gbfs.py
```

The preview views and raw tables are private database inspection data; they are not wired
to the public site.

---

## Repo layout

```
pull_tpd_incidents.py   # ingestion (backfill | refresh)
pull_pag_bikeways.py   # PAG bikeway network snapshot -> raw_pag_bikeways
pull_pag_bikemap_layers.py # Other PAG map layers + legacy Tugo station GIS
pull_tugo_gbfs.py      # Complete TuGo GBFS feed snapshots
pull_neighborhoods.py   # neighborhood polygons -> ref_neighborhoods (run once / rarely)
apply_sql.sh            # apply .sql files to .env's DATABASE_URL
sql/
  01_raw.sql            # landing table (raw_tpd_incidents)
  03_transform.sql      # int_incidents view
  04_reporting.sql      # mart_bike_crimes, mart_bike_stats
  05_api_grants.sql     # read-only API grants (Supabase)
  17_ref_neighborhoods.sql # neighborhood polygons + nbhd_at() lookup (apply before 04)
  18_pag_bikeways.sql # PAG bike-network snapshot table + private preview views
  19_pag_bikemap_and_tugo.sql # Remaining PAG map layers + all TuGo GBFS feeds
  inspect.sql           # per-layer sanity report
  scratch.sql           # ad-hoc query playground
.github/workflows/
  ingest.yml            # daily cron (refresh) + manual dispatch
requirements.txt
.env                    # DB connection (gitignored)
```
