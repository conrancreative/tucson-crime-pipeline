-- ============================================================================
-- 17_ref_neighborhoods.sql  ·  REFERENCE LAYER  ·  Tucson neighborhood polygons
-- ----------------------------------------------------------------------------
-- Spatial (PostGIS) reference table of the city's NEIGHBORHOODS_ALL layer:
-- registered neighborhood associations PLUS the named unaffiliated areas
-- (malls, commercial districts, e.g. "Park Place Mall", "NEC Speedway & Kolb").
-- Source: gis.tucsonaz.gov PublicMaps/NeighborhoodsPlans/MapServer/11.
-- Populated by pull_neighborhoods.py.
--
-- Why: the TPD 2018-2025 year layers label ~10-25% of thefts with a police-team
-- code (T101..T408) or a blank instead of a neighborhood name; the 2026 source
-- names every theft. The names in this layer match the 2026 names exactly, so
-- mart_bike_crimes fills ONLY those placeholder labels by point-in-polygon.
-- Real reported names are never overridden: the 2026 source publishes
-- privacy-offset coordinates, so its own name beats a spatial lookup.
-- ============================================================================

create extension if not exists postgis;

create table if not exists ref_neighborhoods (
    objectid int primary key  -- source OBJECTID (names are not unique)
    , name text not null
    , ward text
    , is_registered_nha boolean  -- a registered city neighborhood association
    , geom geometry(MultiPolygon, 4326) not null
    , pulled_at timestamptz default now()
);

-- spatial index → fast point-in-polygon lookups
create index if not exists ref_neighborhoods_geom_gix on ref_neighborhoods using gist (geom);

-- every new table gets RLS (see 15_rls_lockdown.sql); no policies = anon denied
alter table ref_neighborhoods enable row level security;


-- ----------------------------------------------------------------------------
-- neighborhood_is_placeholder(name) / is this label missing or a TPD team code?
-- ----------------------------------------------------------------------------
create or replace function neighborhood_is_placeholder(nb text)
returns boolean
language sql
immutable
as $$
    select nb is null or trim(nb) = '' or trim(nb) ~ '^T[0-9]+$';
$$;


-- ----------------------------------------------------------------------------
-- nbhd_at(lon, lat) / which neighborhood contains this point? (WGS84 lon/lat)
-- A few polygons nest or overlap; the smallest containing one wins (most
-- specific). Returns NULL outside every polygon, or if the table is empty.
-- search_path is pinned because PG17 builds/refreshes materialized views with a
-- restricted search_path, and mart_bike_crimes calls this.
-- ----------------------------------------------------------------------------
create or replace function nbhd_at(lon double precision, lat double precision)
returns text
language sql
stable
set search_path = public
as $$
    select name
    from ref_neighborhoods
    where st_contains(geom, st_setsrid(st_point(lon, lat), 4326))
    order by st_area(geom)
    limit 1;
$$;
