-- ============================================================================
-- 18_pag_bikeways.sql  ·  PAG Tucson Metro Bike Map network snapshot
-- ----------------------------------------------------------------------------
-- Source: PAG's public TucsonMetroBikeMapVecLive FeatureServer, layer 4.
-- Loaded by pull_pag_bikeways.py. This preview stays separate from the site's
-- API and frontend; no public grants are made.
-- ============================================================================

create extension if not exists postgis;

create table if not exists raw_pag_bikeways (
    objectid bigint primary key,
    payload jsonb not null, -- complete ArcGIS GeoJSON feature
    geom geometry(MultiLineString, 4326) not null,
    pulled_at timestamptz not null default now()
);

create index if not exists raw_pag_bikeways_geom_gix
    on raw_pag_bikeways using gist (geom);
create index if not exists raw_pag_bikeways_display_idx
    on raw_pag_bikeways ((payload->'properties'->>'Display'));

-- SQLTools/PostgREST-free inspection surface. Geometry is exposed as GeoJSON
-- for convenient previews; the source geometry remains indexed in PostGIS.
create or replace view preview_pag_bikeways as
select objectid
    , payload->'properties'->>'STREET' as street
    , payload->'properties'->>'BIKERTE_CD' as facility_code
    , payload->'properties'->>'NAME_BKWY' as bikeway_name
    , payload->'properties'->>'BIKERTE_DS' as facility_description
    , payload->'properties'->>'Display' as facility_type
    , payload->'properties'->>'Verify' as verify_status
    , nullif(payload->'properties'->>'Length_feet', '')::double precision as length_feet
    , nullif(payload->'properties'->>'Length_miles', '')::double precision as length_miles
    , st_asgeojson(geom)::json as geometry
    , pulled_at
from raw_pag_bikeways;

create or replace view preview_pag_bikeways_summary as
select payload->'properties'->>'Display' as facility_type
    , count(*)::bigint as segment_count
    , sum(nullif(payload->'properties'->>'Length_miles', '')::double precision) as miles
    , max(pulled_at) as last_pulled_at
from raw_pag_bikeways
group by 1
order by 1;

-- The source is public, but keep this exploratory mirror private to database
-- users. In particular, do not expose the raw table or preview views through
-- the site's anonymous Supabase API.
alter table raw_pag_bikeways enable row level security;
revoke all on raw_pag_bikeways from public;
revoke all on preview_pag_bikeways from public;
revoke all on preview_pag_bikeways_summary from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on raw_pag_bikeways from anon, authenticated;
    revoke all on preview_pag_bikeways from anon, authenticated;
    revoke all on preview_pag_bikeways_summary from anon, authenticated;
  end if;
end $$;
