-- Regional bicycle stress, posted speeds, and functional classification.
-- Full source records stay in raw JSON, with indexed WGS84 line geometry.
-- These are private development views. Source measurements can be historical.

create extension if not exists postgis;

create table if not exists raw_roadway_features (
  source_key text not null
  , layer_id integer not null
  , layer_name text not null
  , object_id text not null
  , payload jsonb not null
  , geom geometry(Geometry, 4326) not null
  , pulled_at timestamptz not null default now()
  , primary key (source_key, layer_id, object_id)
);

create index if not exists raw_roadway_features_geom_gix
  on raw_roadway_features using gist (geom);

create table if not exists roadway_source_snapshots (
  source_key text not null
  , layer_id integer not null
  , layer_name text not null
  , source_url text not null
  , feature_count bigint not null
  , metadata jsonb not null
  , pulled_at timestamptz not null default now()
  , primary key (source_key, layer_id)
);

create or replace view preview_bicycle_stress as
select object_id
  , layer_id
  , payload->'properties'->>'ROADID' as road_id
  , payload->'properties'->>'STREET' as street
  , payload->'properties'->>'C_FN_Class' as regional_classification
  , payload->'properties'->>'F_FN_Class' as federal_classification
  , nullif(payload->'properties'->>'Speed', '')::double precision as speed_limit_mph
  , nullif(payload->'properties'->>'Lanes', '')::double precision as travel_lanes
  , nullif(payload->'properties'->>'AADT', '')::double precision as aadt
  , payload->'properties'->>'BikeFac_Ty' as bike_facility_type
  , nullif(payload->'properties'->>'Bike_LTS_Score_Right', '')::double precision as stress_right
  , nullif(payload->'properties'->>'Bike_LTS_Score_Left', '')::double precision as stress_left
  , nullif(payload->'properties'->>'Bike_LTS_Score_Combined', '')::double precision as stress_level
  , payload->'properties' as properties
  , st_asgeojson(geom)::json as geometry
  , pulled_at
from raw_roadway_features
where source_key = 'pag_bicycle_lts';

create or replace view preview_road_speed_limits as
select object_id
  , payload->'properties'->>'ROADID' as road_id
  , payload->'properties'->>'STREET' as street
  , payload->'properties'->>'ROADCAT_DS' as road_category
  , nullif(payload->'properties'->>'COT_SPEED', '')::double precision as speed_limit_mph
  , nullif(payload->'properties'->>'SpeedNight', '')::double precision as night_speed_limit_mph
  , payload->'properties'->>'TRAVDIR_CD' as travel_direction
  , payload->'properties' as properties
  , st_asgeojson(geom)::json as geometry
  , pulled_at
from raw_roadway_features
where source_key = 'tucson_speed_limits';

create or replace view preview_road_classification as
select object_id
  , payload->'properties'->>'STR_NAME' as street_name
  , payload->'properties'->>'STR_TYPE' as street_type
  , payload->'properties'->>'ROADCAT_CD' as road_category_code
  , payload->'properties'->>'StreetType_Update' as move_tucson_street_type
  , payload->'properties'->>'FederalClassification_Text' as federal_classification
  , nullif(payload->'properties'->>'COT_SPEED', '')::double precision as speed_limit_mph
  , payload->'properties'->>'Overlay_BicycleBoulevard' as bicycle_boulevard
  , payload->'properties'->>'Overlay_BicyclePriority' as bicycle_priority
  , payload->'properties' as properties
  , st_asgeojson(geom)::json as geometry
  , pulled_at
from raw_roadway_features
where source_key = 'move_tucson_classification';

create or replace view preview_roadway_sources as
select s.source_key
  , s.layer_id
  , s.layer_name
  , s.source_url
  , s.feature_count
  , s.pulled_at
  , to_timestamp((s.metadata->'editingInfo'->>'dataLastEditDate')::double precision / 1000)
      as source_data_edited_at
  , s.metadata->>'description' as source_description
from roadway_source_snapshots s;

alter table raw_roadway_features enable row level security;
alter table roadway_source_snapshots enable row level security;

revoke all on raw_roadway_features, roadway_source_snapshots,
  preview_bicycle_stress, preview_road_speed_limits,
  preview_road_classification, preview_roadway_sources from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on raw_roadway_features, roadway_source_snapshots,
      preview_bicycle_stress, preview_road_speed_limits,
      preview_road_classification, preview_roadway_sources from anon, authenticated;
  end if;
end $$;
