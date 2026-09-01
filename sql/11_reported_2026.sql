-- ============================================================================
-- 11_reported_2026.sql  ·  current-year (2026) reported bike thefts
-- ----------------------------------------------------------------------------
-- Source: TPDOpenDataReportedCrimes2026 (services3.arcgis.com). Complete +
-- fresh 2026 reported crimes WITH geometry, ward, neighborhood, block address --
-- better than the 45-day incidents layer, which we keep only as a stored backup.
--
-- The source has ONE ROW PER PERSON/ROLE, so we key on incident_number to keep
-- one row per incident. Offense 0606 == 'Larceny - Bicycles'. Loaded by
-- pull_tpd_reported_2026.py. The bike mart (04_reporting.sql) uses this for 2026
-- and the year layers for 2018-2025.
-- ============================================================================

create table if not exists raw_tpd_reported_2026 (
    incident_number text primary key,
    payload         jsonb not null,
    pulled_at       timestamptz default now()
);

create or replace view int_reported_2026 as
with a as (
    select payload->'attributes' as attrs, payload->'geometry' as geom, pulled_at
    from raw_tpd_reported_2026
)
select
    attrs->>'IncidentNumber'                                 as incident_id,
    attrs->>'Offense'                                        as offense_code,
    coalesce(attrs->>'StatuteDescription', 'Larceny - Bicycles') as offense_description,
    to_timestamp((attrs->>'OccurredDateTime')::bigint / 1000.0) as occurred_at,
    (to_timestamp((attrs->>'OccurredDateTime')::bigint / 1000.0)
        at time zone 'America/Phoenix')                      as occurred_at_az,
    extract(year from
        to_timestamp((attrs->>'OccurredDateTime')::bigint / 1000.0))::int as year,
    nullif(attrs->>'Ward', '')                               as ward,
    nullif(attrs->>'NeighborhoodAssociation', '')            as neighborhood,
    attrs->>'Address100Block'                                as address,
    (attrs->>'Offense' = '0606')                             as is_bicycle,
    (geom->>'x')::double precision                           as lon,
    (geom->>'y')::double precision                           as lat,
    pulled_at,
    (pulled_at at time zone 'America/Phoenix')               as pulled_at_az
from a;
