-- ============================================================================
-- 03_transform.sql  ·  TRANSFORM LAYER
-- ----------------------------------------------------------------------------
-- Cleans + types the raw spatial incidents into one tidy model with real lat/lon.
-- Source: raw_tpd_incidents (pulled by pull_tpd_incidents.py from the spatial
-- TPD_INCIDENTS_PUBLIC_* layers). Field names vary a little between the year,
-- current, and 45-day layers, so we COALESCE across the known variants.
--
-- Facts: OFFENSE '0606' == 'Larceny - Bicycles'; DATE_OCCU = epoch MILLISECONDS;
-- geometry is WGS84 (outSR=4326) so x=lon, y=lat.
-- ============================================================================

-- dropped (not "or replace") so columns can be reordered/added freely.
-- cascade removes the dependent marts; 04_reporting.sql recreates them.
drop view if exists int_incidents cascade;

create view int_incidents as
with a as (
    select
        inci_id,
        source_layer,
        payload->'attributes'                                as attrs,
        payload->'geometry'                                  as geom,
        pulled_at
    from raw_tpd_incidents
)
select
    inci_id                                                  as incident_id,

    attrs->>'OFFENSE'                                        as offense_code,
    coalesce(attrs->>'STATUTDESC', attrs->>'Crime')         as offense_description,
    coalesce(attrs->>'UCRSummaryDesc', attrs->>'UCRsummary') as ucr_description,

    -- when: DATETIME_OCCU is epoch-ms and populated on every record. Arizona has
    -- no DST, so treating it as UTC keeps the wall-clock date/time correct.
    to_timestamp((attrs->>'DATETIME_OCCU')::bigint / 1000.0) as occurred_at,
    extract(year from
        to_timestamp((attrs->>'DATETIME_OCCU')::bigint / 1000.0)
    )::int                                                  as year,
    attrs->>'TIME_OCCU'                                      as time_occur,

    -- when reported (95% filled) -- pair with occurred_at for reporting lag
    to_timestamp(nullif(attrs->>'DATETIME_REPT','')::bigint / 1000.0) as reported_at,

    -- where (administrative)
    coalesce(attrs->>'DIVISION', attrs->>'emdivision')      as division,
    nullif(attrs->>'WARD', '')                              as ward,
    coalesce(attrs->>'NHA_NAME', attrs->>'NEIGHBORHD')     as neighborhood,
    attrs->>'ADDRESS_PUBLIC'                                as address,

    -- what kind of place it was stolen from (land use)
    nullif(attrs->>'PARCEL_GRP', '')                        as parcel_group,
    nullif(attrs->>'PARCEL_CATEGORY', '')                  as parcel_category,

    -- case outcome ('Open', 'Cleared ...') and census geo for later joins
    nullif(attrs->>'clearance_verbose', '')                as case_status,
    nullif(attrs->>'CENSUSTRACT', '')                      as census_tract,

    -- where (geographic) -- NULL when the source never geocoded the address
    (geom->>'x')::double precision                          as lon,
    (geom->>'y')::double precision                          as lat,

    -- classification -- widen this predicate to add offense categories
    (attrs->>'OFFENSE' = '0606')                            as is_bicycle,

    source_layer,
    pulled_at
from a;
