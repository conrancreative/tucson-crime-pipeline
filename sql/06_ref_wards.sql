-- ============================================================================
-- 06_ref_wards.sql  ·  REFERENCE LAYER  ·  Tucson City Council ward boundaries
-- ----------------------------------------------------------------------------
-- Spatial (PostGIS) reference table of the 6 city ward polygons, for drawing
-- ward areas on the map and point-in-polygon lookups (which ward a point is in).
-- Source: Pima County GIS open data "Wards - City of Tucson" (WGS84 polygons).
-- Populated by pull_wards.py. `ward` joins to int_incidents/mart_bike_crimes.ward.
-- ============================================================================

create extension if not exists postgis;

create table if not exists ref_wards (
    ward            text primary key,                 -- '1'..'6' (joins to crime.ward)
    council_member  text,
    office_address  text,
    phone           text,
    url             text,
    city            text,
    zipcode         text,
    geom            geometry(MultiPolygon, 4326) not null,
    pulled_at       timestamptz default now()
);

-- spatial index → fast point-in-polygon and bounding-box queries
create index if not exists ref_wards_geom_gix on ref_wards using gist (geom);


-- ----------------------------------------------------------------------------
-- api_wards  ·  what the frontend reads: attributes + geometry as GeoJSON.
-- The map wraps these rows into a FeatureCollection to draw ward boundaries.
-- ----------------------------------------------------------------------------
create or replace view api_wards as
select
    ward,
    council_member,
    office_address,
    phone,
    url,
    st_asgeojson(geom)::json as geometry
from ref_wards
order by ward;


-- ----------------------------------------------------------------------------
-- ward_at(lon, lat)  ·  which ward contains this point? (WGS84 lon/lat)
-- Powers "type an address → which ward": geocode the address to lon/lat, then
-- call this. Returns the ward number, or NULL if outside the city.
-- ----------------------------------------------------------------------------
create or replace function ward_at(lon double precision, lat double precision)
returns text
language sql
stable
as $$
    select ward
    from ref_wards
    where st_contains(geom, st_setsrid(st_point(lon, lat), 4326))
    limit 1;
$$;


-- ----------------------------------------------------------------------------
-- read-only API access (Supabase; no-op locally where the anon role is absent)
-- ----------------------------------------------------------------------------
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    grant usage on schema public to anon, authenticated;
    grant select on ref_wards, api_wards to anon, authenticated;
    grant execute on function ward_at(double precision, double precision) to anon, authenticated;
  end if;
end $$;
