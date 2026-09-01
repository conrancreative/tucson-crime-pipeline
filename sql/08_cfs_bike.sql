-- ============================================================================
-- 08_cfs_bike.sql  ·  RAW LANDING for bike-related Calls-For-Service
-- ----------------------------------------------------------------------------
-- Near-real-time (~2-day) dispatch events from TUCSON_CFS_PUBLIC_45D (layer 41),
-- filtered to bike-related nature codes. One shared feed; split into per-code
-- marts (theft calls / bike traffic / injury crashes) in a later step.
-- Keyed on call_id and upserted, so it accumulates history beyond the 45 days.
-- Populated by pull_tpd_cfs_bike.py.
--
-- Bike nature codes seen in this feed:
--   'LARCENY/BICYCLES'   -> preliminary bike-theft calls (not yet reviewed)
--   'BICYCLE TRAFFIC'    -> bike traffic incidents / enforcement
--   'MVA - INJURY ACCIDENT: ... PED/MC/BICY ...' -> injury crashes (bike+ped+moto, lumped)
-- ============================================================================

create table if not exists raw_tpd_cfs_bike (
    call_id     text primary key,
    nature_code text,               -- NatureCodeDesc, denormalized for easy mart splits
    payload     jsonb not null,     -- full CFS feature: attributes + geometry
    pulled_at   timestamptz default now()
);

create index if not exists raw_tpd_cfs_bike_nature_idx on raw_tpd_cfs_bike (nature_code);


-- ----------------------------------------------------------------------------
-- TRANSFORM: flatten the CFS bike feed. ACTDATETIME is epoch-ms (call time).
-- ----------------------------------------------------------------------------
create or replace view int_cfs_bike as
with a as (
    select call_id, nature_code,
           payload->'attributes' as attrs,
           payload->'geometry'   as geom,
           pulled_at
    from raw_tpd_cfs_bike
)
select
    call_id,
    nullif(attrs->>'case_id', '')                          as case_id,
    nature_code,
    to_timestamp((attrs->>'ACTDATETIME')::bigint / 1000.0) as occurred_at,
    (to_timestamp((attrs->>'ACTDATETIME')::bigint / 1000.0)
        at time zone 'America/Phoenix')                    as occurred_at_az,
    nullif(attrs->>'WARD', '')                             as ward,
    coalesce(attrs->>'NHA_NAME', attrs->>'NEIGHBORHD')     as neighborhood,
    attrs->>'ADDRESS_PUBLIC'                               as address,
    nullif(attrs->>'DispositionCodeDesc', '')             as disposition,
    (geom->>'x')::double precision                         as lon,
    (geom->>'y')::double precision                         as lat,
    pulled_at
from a;


-- ----------------------------------------------------------------------------
-- REPORTING: one mart per code (each a self-contained map layer / API source).
-- ----------------------------------------------------------------------------

-- 1) Preliminary bike-theft CALLS — only those NEWER than the reviewed data's
--    leading edge, so they never double-count the reported thefts. As the
--    reviewed edge advances, a call crosses the boundary and drops out here
--    (it has "become" a reported theft).
drop materialized view if exists mart_bike_theft_calls;
create materialized view mart_bike_theft_calls as
select call_id as id, occurred_at, occurred_at_az, ward, neighborhood, address, lat, lon,
       'call'::text as status
from int_cfs_bike
where nature_code = 'LARCENY/BICYCLES'
  and lat is not null and lon is not null
  and occurred_at > coalesce(
        (select max(occurred_at) from int_incidents where is_bicycle),
        timestamp '1900-01-01')
order by occurred_at desc;
create unique index if not exists mart_bike_theft_calls_id_idx on mart_bike_theft_calls (id);

-- 2) Bike traffic incidents / enforcement
drop materialized view if exists mart_bike_traffic;
create materialized view mart_bike_traffic as
select call_id as id, occurred_at, occurred_at_az, ward, neighborhood, address, lat, lon
from int_cfs_bike
where nature_code = 'BICYCLE TRAFFIC'
  and lat is not null and lon is not null
order by occurred_at desc;
create unique index if not exists mart_bike_traffic_id_idx on mart_bike_traffic (id);

-- 3) Injury crashes (LUMPED bike + pedestrian + motorcycle — the fresh feed
--    can't be narrowed to bike-only; labeled accordingly).
drop materialized view if exists mart_bike_crashes;
create materialized view mart_bike_crashes as
select call_id as id, occurred_at, occurred_at_az, ward, neighborhood, address, lat, lon,
       'bike/ped/moto injury crash'::text as note
from int_cfs_bike
where nature_code like 'MVA%'
  and lat is not null and lon is not null
order by occurred_at desc;
create unique index if not exists mart_bike_crashes_id_idx on mart_bike_crashes (id);


-- read-only API access (Supabase; no-op locally where the anon role is absent)
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    grant select on mart_bike_theft_calls, mart_bike_traffic, mart_bike_crashes
        to anon, authenticated;
  end if;
end $$;

