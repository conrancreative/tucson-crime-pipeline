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
- The 45-day window is by **report** date, so a few records have an `occurred_at` in the prior year.

---

## Repo layout

```
pull_tpd_incidents.py   # ingestion (backfill | refresh)
apply_sql.sh            # apply .sql files to .env's DATABASE_URL
sql/
  01_raw.sql            # landing table (raw_tpd_incidents)
  03_transform.sql      # int_incidents view
  04_reporting.sql      # mart_bike_crimes, mart_bike_stats
  05_api_grants.sql     # read-only API grants (Supabase)
  inspect.sql           # per-layer sanity report
  scratch.sql           # ad-hoc query playground
.github/workflows/
  ingest.yml            # daily cron (refresh) + manual dispatch
requirements.txt
.env                    # DB connection (gitignored)
```
