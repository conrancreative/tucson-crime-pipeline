-- ============================================================================
-- 19_pag_bikemap_and_tugo.sql  ·  remaining map layers + Tugo GBFS snapshots
-- ----------------------------------------------------------------------------
-- Imports the other six TucsonMetroBikeMapVecLive layers, the older Tugo point
-- layer used by the map, and every feed currently advertised by Tugo GBFS 3.0.
-- All relations are private inspection data; none are used by the website.
-- ============================================================================

create extension if not exists postgis;

create table if not exists raw_pag_bikemap_features (
    source_key text not null,
    layer_id integer not null,
    layer_name text not null,
    object_id text not null,
    payload jsonb not null, -- complete source GeoJSON feature
    geom geometry(Geometry, 4326),
    pulled_at timestamptz not null default now(),
    primary key (source_key, layer_id, object_id)
);

create index if not exists raw_pag_bikemap_features_geom_gix
    on raw_pag_bikemap_features using gist (geom);
create index if not exists raw_pag_bikemap_features_layer_idx
    on raw_pag_bikemap_features (source_key, layer_id);

create table if not exists raw_tugo_gbfs_snapshots (
    feed_name text not null,
    feed_url text not null,
    feed_version text,
    feed_updated_at timestamptz,
    captured_at timestamptz not null,
    payload jsonb not null, -- complete GBFS response, including feed data
    primary key (feed_name, captured_at)
);

create index if not exists raw_tugo_gbfs_snapshots_latest_idx
    on raw_tugo_gbfs_snapshots (feed_name, captured_at desc);

-- One row per feature from all GIS layers. The primary bikeway lines (layer 4)
-- remain in raw_pag_bikeways; this view combines them with the ancillary layers
-- so a reviewer can browse the complete PAG map from one relation.
create or replace view preview_pag_bikemap_features as
select 'pag_tucson_bikemap'::text as source_key
    , 4 as layer_id
    , 'Bikeways'::text as layer_name
    , objectid::text as object_id
    , payload->'properties' as properties
    , st_asgeojson(geom)::json as geometry
    , pulled_at
from raw_pag_bikeways
union all
select source_key
    , layer_id
    , layer_name
    , object_id
    , payload->'properties' as properties
    , case when geom is null then null else st_asgeojson(geom)::json end as geometry
    , pulled_at
from raw_pag_bikemap_features;

create or replace view preview_pag_bikemap_layer_summary as
select source_key, layer_id, layer_name, count(*)::bigint as feature_count
    , count(*) filter (where geom is not null)::bigint as with_geometry
    , max(pulled_at) as last_pulled_at
from raw_pag_bikemap_features
group by source_key, layer_id, layer_name
union all
select 'pag_tucson_bikemap', 4, 'Bikeways', count(*)::bigint
    , count(*) filter (where geom is not null)::bigint
    , max(pulled_at)
from raw_pag_bikeways;

-- Latest complete response for each advertised GBFS feed (including the
-- discovery manifest and feeds with empty arrays).
create or replace view preview_tugo_gbfs_feeds as
select distinct on (feed_name) feed_name, feed_url, feed_version
    , feed_updated_at, captured_at, payload
from raw_tugo_gbfs_snapshots
order by feed_name, captured_at desc;

-- Current station inventory joined to current availability. The raw snapshots
-- retain each feed payload at every daily capture for later historical work.
create or replace view preview_tugo_stations as
with info as (
    select jsonb_array_elements(payload->'data'->'stations') as station
        , captured_at, feed_updated_at
    from preview_tugo_gbfs_feeds
    where feed_name = 'station_information'
), status as (
    select jsonb_array_elements(payload->'data'->'stations') as station
        , captured_at, feed_updated_at
    from preview_tugo_gbfs_feeds
    where feed_name = 'station_status'
)
select i.station->>'station_id' as station_id
    , (select n->>'text' from jsonb_array_elements(i.station->'name') n
       where n->>'language' = 'en' limit 1) as name
    , i.station->>'address' as address
    , nullif(i.station->>'lat', '')::double precision as lat
    , nullif(i.station->>'lon', '')::double precision as lon
    , nullif(i.station->>'capacity', '')::integer as capacity
    , nullif(i.station->>'is_virtual_station', '')::boolean as is_virtual_station
    , nullif(s.station->>'num_vehicles_available', '')::integer as bikes_available
    , nullif(s.station->>'num_vehicles_disabled', '')::integer as bikes_disabled
    , nullif(s.station->>'num_docks_available', '')::integer as docks_available
    , nullif(s.station->>'num_docks_disabled', '')::integer as docks_disabled
    , nullif(s.station->>'is_installed', '')::boolean as is_installed
    , nullif(s.station->>'is_renting', '')::boolean as is_renting
    , nullif(s.station->>'is_returning', '')::boolean as is_returning
    , nullif(s.station->>'last_reported', '')::timestamptz as status_reported_at
    , i.feed_updated_at as information_updated_at
    , s.feed_updated_at as status_updated_at
    , i.captured_at as information_captured_at
    , s.captured_at as status_captured_at
from info i
left join status s on s.station->>'station_id' = i.station->>'station_id';

-- Keep all imported source data private. No anonymous/authenticated grants.
alter table raw_pag_bikemap_features enable row level security;
alter table raw_tugo_gbfs_snapshots enable row level security;
revoke all on raw_pag_bikemap_features from public;
revoke all on raw_tugo_gbfs_snapshots from public;
revoke all on preview_pag_bikemap_features from public;
revoke all on preview_pag_bikemap_layer_summary from public;
revoke all on preview_tugo_gbfs_feeds from public;
revoke all on preview_tugo_stations from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on raw_pag_bikemap_features from anon, authenticated;
    revoke all on raw_tugo_gbfs_snapshots from anon, authenticated;
    revoke all on preview_pag_bikemap_features from anon, authenticated;
    revoke all on preview_pag_bikemap_layer_summary from anon, authenticated;
    revoke all on preview_tugo_gbfs_feeds from anon, authenticated;
    revoke all on preview_tugo_stations from anon, authenticated;
  end if;
end $$;
