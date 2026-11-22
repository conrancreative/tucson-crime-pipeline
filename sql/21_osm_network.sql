-- Private OpenStreetMap source snapshots. These are not routable graph edges.
-- Preserve tags, ordered node IDs, and restriction members for later rules.
begin;

create extension if not exists postgis;

create table if not exists osm_network_snapshots (
  scope_key text primary key
  , source_timestamp timestamptz
  , source_sha256 text not null
  , extract_sha256 text not null
  , study_area geometry(MultiPolygon, 4326) not null
  , metadata jsonb not null
  , pulled_at timestamptz not null default now()
);

create table if not exists raw_osm_nodes (
  scope_key text not null references osm_network_snapshots(scope_key)
  , osm_id bigint not null
  , tags jsonb not null
  , geom geometry(Point, 4326) not null
  , primary key (scope_key, osm_id)
);

create table if not exists raw_osm_ways (
  scope_key text not null references osm_network_snapshots(scope_key)
  , osm_id bigint not null
  , node_ids bigint[] not null
  , tags jsonb not null
  , geom geometry(LineString, 4326) not null
  , primary key (scope_key, osm_id)
  , check (cardinality(node_ids) >= 2)
);

create table if not exists raw_osm_restrictions (
  scope_key text not null references osm_network_snapshots(scope_key)
  , osm_id bigint not null
  , tags jsonb not null
  , members jsonb not null
  , primary key (scope_key, osm_id)
  , check (jsonb_typeof(members) = 'array')
);

create index if not exists raw_osm_nodes_geom_gix
  on raw_osm_nodes using gist (geom);
create index if not exists raw_osm_ways_geom_gix
  on raw_osm_ways using gist (geom);

alter table osm_network_snapshots enable row level security;
alter table raw_osm_nodes enable row level security;
alter table raw_osm_ways enable row level security;
alter table raw_osm_restrictions enable row level security;

revoke all on osm_network_snapshots, raw_osm_nodes, raw_osm_ways,
  raw_osm_restrictions from public;

do $$
declare
  client_role text;
begin
  foreach client_role in array array['anon', 'authenticated'] loop
    if exists (select 1 from pg_roles where rolname = client_role) then
      execute format(
        'revoke all on osm_network_snapshots, raw_osm_nodes, raw_osm_ways, raw_osm_restrictions from %I'
        , client_role
      );
    end if;
  end loop;
end $$;

commit;
