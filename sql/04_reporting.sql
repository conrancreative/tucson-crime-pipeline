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

-- Bike thefts, three sources, tagged by `source` so the frontend can style and
-- split them:
--   TPD  · 2018-2025 history (year layers) + 2026 (ReportedCrimes2026). No year
--          overlap, so no double-counting. The 45-day incidents layer's 2026 rows
--          sit in int_incidents but are excluded (year <= 2025) -- backup only.
--   UAPD · University of Arizona PD bike THEFTS (crashes stay in mart_uapd_bike),
--          attributed to Ward 6 (the campus sits in Ward 6) but flagged source =
--          'UAPD' so the map colors them differently and the Ward 6 metrics can
--          split TPD vs UA. `geocoded` = false marks Old-Main-fallback points.
create materialized view mart_bike_crimes as
select
    incident_id                            as id,
    occurred_at, occurred_at_az, year,
    extract(month from occurred_at)::int   as month,
    trim(to_char(occurred_at, 'Dy'))       as day_of_week,
    time_occur, division, ward, neighborhood, address,
    parcel_group, parcel_category, case_status, offense_description,
    lat, lon, pulled_at, pulled_at_az,
    'TPD'::text as source, true as geocoded
from int_incidents
where is_bicycle and year <= 2025
  and lat is not null and lon is not null
union all
select
    incident_id                            as id,
    occurred_at, occurred_at_az, year,
    extract(month from occurred_at)::int   as month,
    trim(to_char(occurred_at, 'Dy'))       as day_of_week,
    null::text, null::text, ward, neighborhood, address,
    null::text, null::text, null::text, offense_description,
    lat, lon, pulled_at, pulled_at_az,
    'TPD'::text as source, true as geocoded
from int_reported_2026
where is_bicycle and lat is not null and lon is not null
union all
-- Read int_uapd (the view) directly -- NOT mart_uapd_bike -- so this matview
-- doesn't depend on that one. Apply the Old-Main fallback + geocoded flag inline.
select
    'UA:' || case_number                   as id,
    (occurred_at at time zone 'America/Phoenix')  as occurred_at,
    occurred_at                            as occurred_at_az,
    extract(year  from occurred_at)::int   as year,
    extract(month from occurred_at)::int   as month,
    trim(to_char(occurred_at, 'Dy'))       as day_of_week,
    null::text, null::text,                                    -- time_occur, division
    '6'::text as ward, 'University of Arizona'::text as neighborhood, address,
    null::text, null::text, disposition,                      -- parcel_group, parcel_category, case_status
    nature                                 as offense_description,
    coalesce(lat, 32.2313)::double precision  as lat,          -- Old Main fallback
    coalesce(lon, -110.9558)::double precision as lon,
    now() as pulled_at, (now() at time zone 'America/Phoenix') as pulled_at_az,
    'UAPD'::text as source, (lat is not null) as geocoded
from int_uapd
where is_bike_theft
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
with all_bikes as (
    select occurred_at, year, ward
    from int_incidents
    where is_bicycle and year <= 2025
    union all
    select occurred_at, year, ward
    from int_reported_2026
    where is_bicycle
)
select
    year,
    date_trunc('month', occurred_at)::date as month,
    ward,
    count(*)                               as incidents
from all_bikes
group by 1, 2, 3
order by 2 desc, 4 desc;

create unique index if not exists mart_bike_stats_key_idx
    on mart_bike_stats (year, month, ward);
