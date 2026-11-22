-- Private, rebuildable infrastructure inventory. No routing recommendations.
begin;

create table if not exists raw_osm_bicycle_routes (
  scope_key text not null references osm_network_snapshots(scope_key)
  , osm_id bigint not null
  , tags jsonb not null
  , members jsonb not null
  , source_version integer
  , source_edited_at timestamptz
  , primary key (scope_key, osm_id)
);

create table if not exists osm_bicycle_route_snapshots (
  scope_key text primary key references osm_network_snapshots(scope_key)
  , source_sha256 text not null
  , source_timestamp timestamptz not null
  , imported_at timestamptz not null default now()
  , metadata jsonb not null
);

create table if not exists bikeway_catalog (
  scope_key text not null references osm_network_snapshots(scope_key)
  , bikeway_id uuid not null
  , name text not null
  , kind text not null
  , source_names jsonb not null
  , details jsonb not null
  , primary key (scope_key, bikeway_id)
);

create table if not exists bikeway_sections (
  scope_key text not null references osm_network_snapshots(scope_key)
  , section_id text not null
  , source text not null check (source in ('pag', 'osm'))
  , source_id text not null
  , source_url text not null
  , street text
  , facility_type text not null
  , source_date timestamptz
  , geom geometry(MultiLineString, 4326) not null
  , facts jsonb not null
  , primary key (scope_key, section_id)
);

create index if not exists bikeway_sections_geom_gix
  on bikeway_sections using gist (geom);

create table if not exists bikeway_memberships (
  scope_key text not null
  , bikeway_id uuid not null
  , section_id text not null
  , evidence jsonb not null
  , primary key (scope_key, bikeway_id, section_id)
  , foreign key (scope_key, bikeway_id) references bikeway_catalog(scope_key, bikeway_id)
  , foreign key (scope_key, section_id) references bikeway_sections(scope_key, section_id)
);

create index if not exists bikeway_memberships_section_idx
  on bikeway_memberships (scope_key, section_id);

create table if not exists bikeway_matches (
  scope_key text not null
  , agency_section_id text not null
  , osm_way_id bigint not null
  , matched_meters double precision not null
  , details jsonb not null
  , primary key (scope_key, agency_section_id, osm_way_id)
  , foreign key (scope_key, agency_section_id) references bikeway_sections(scope_key, section_id)
);

create table if not exists bikeway_issues (
  scope_key text not null references osm_network_snapshots(scope_key)
  , issue_id text not null
  , issue_type text not null
  , section_id text
  , bikeway_ids uuid[] not null
  , description text not null
  , geom geometry(Geometry, 4326)
  , details jsonb not null
  , primary key (scope_key, issue_id)
);

create index if not exists bikeway_issues_type_idx
  on bikeway_issues (scope_key, issue_type);

create table if not exists bikeway_builds (
  scope_key text primary key references osm_network_snapshots(scope_key)
  , built_at timestamptz not null default now()
  , input_fingerprints jsonb not null
  , summary jsonb not null
);

create or replace view preview_bikeway_catalog with (security_invoker = true) as
select scope_key, bikeway_id, name, kind, source_names, details
from bikeway_catalog;

create or replace view preview_bikeway_audit with (security_invoker = true) as
select scope_key, issue_id, issue_type, section_id, bikeway_ids, description,
  st_asgeojson(geom)::json as geometry, details
from bikeway_issues;

do $$
declare
  table_name text;
  client_role text;
begin
  foreach table_name in array array[
    'raw_osm_bicycle_routes', 'osm_bicycle_route_snapshots', 'bikeway_catalog',
    'bikeway_sections', 'bikeway_memberships', 'bikeway_matches',
    'bikeway_issues', 'bikeway_builds'
  ] loop
    execute format('alter table %I enable row level security', table_name);
    execute format('revoke all on %I from public', table_name);
  end loop;
  revoke all on preview_bikeway_catalog, preview_bikeway_audit from public;
  foreach client_role in array array['anon', 'authenticated'] loop
    if exists (select 1 from pg_roles where rolname = client_role) then
      execute format(
        'revoke all on raw_osm_bicycle_routes, osm_bicycle_route_snapshots,
         bikeway_catalog, bikeway_sections, bikeway_memberships, bikeway_matches,
         bikeway_issues, bikeway_builds, preview_bikeway_catalog,
         preview_bikeway_audit from %I', client_role);
    end if;
  end loop;
end $$;

commit;
