-- ============================================================================
-- 04_reporting.sql  ·  REPORTING / MART LAYER
-- ----------------------------------------------------------------------------
-- The public, API-facing surface. The frontend (via Supabase PostgREST) only
-- ever reads from these objects -- never from raw/staging/transform.
--
-- Grant read-only access + row-level security in Supabase, e.g.:
--   grant select on mart_bike_crimes, mart_bike_stats to anon, authenticated;
-- ============================================================================


-- ----------------------------------------------------------------------------
-- mart_bike_crimes  ·  one row per bicycle theft, map-ready
-- Materialized so map/filter queries stay fast; refresh after each ingest:
--   refresh materialized view concurrently mart_bike_crimes;
-- ----------------------------------------------------------------------------
drop materialized view if exists mart_bike_crimes;

create materialized view mart_bike_crimes as
select
    incident_id                            as id,
    occurred_at,
    occurred_at_az,
    year,
    extract(month from occurred_at)::int   as month,
    trim(to_char(occurred_at, 'Dy'))       as day_of_week,
    time_occur,
    division,
    ward,
    neighborhood,
    address,
    parcel_group,
    parcel_category,
    case_status,
    offense_description,
    lat,
    lon,
    pulled_at,                             -- when we last refreshed this row
    pulled_at_az
from int_incidents
where is_bicycle
  and lat is not null and lon is not null      -- map needs a point
order by occurred_at desc;

-- unique index enables REFRESH ... CONCURRENTLY and speeds up point lookups
create unique index if not exists mart_bike_crimes_id_idx
    on mart_bike_crimes (id);

-- indexes for the frontend filters (date range, ward, map bounding box)
create index if not exists mart_bike_crimes_occurred_idx
    on mart_bike_crimes (occurred_at);
create index if not exists mart_bike_crimes_ward_idx
    on mart_bike_crimes (ward);
create index if not exists mart_bike_crimes_geo_idx
    on mart_bike_crimes (lat, lon);


-- ----------------------------------------------------------------------------
-- mart_bike_stats  ·  pre-aggregated counts for trend charts / summary panels
-- One row per (year, month, ward). Includes ALL bike thefts (even un-geocoded),
-- so trend totals aren't undercounted by missing coordinates.
-- ----------------------------------------------------------------------------
drop materialized view if exists mart_bike_stats;

create materialized view mart_bike_stats as
select
    year,
    date_trunc('month', occurred_at)::date as month,
    ward,
    count(*)                               as incidents
from int_incidents
where is_bicycle
group by 1, 2, 3
order by 2 desc, 4 desc;

create unique index if not exists mart_bike_stats_key_idx
    on mart_bike_stats (year, month, ward);
