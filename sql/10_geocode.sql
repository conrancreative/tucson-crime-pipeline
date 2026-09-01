-- ============================================================================
-- 10_geocode.sql  ·  address -> lat/lon cache (shared geocoding)
-- ----------------------------------------------------------------------------
-- The UAPD log has addresses but no coordinates. We geocode each DISTINCT
-- address once (U.S. Census geocoder) and cache it here, so nothing is
-- geocoded twice and the daily run only handles new addresses. Rows with NULL
-- lat/lon are addresses the geocoder couldn't match (kept so we don't retry
-- them every run). Populated by geocode_uapd.py.
-- ============================================================================

create table if not exists geocode_cache (
    address         text primary key,       -- raw address string as it appears in the source
    lat             double precision,        -- NULL if not matched
    lon             double precision,
    matched_address text,                    -- what the geocoder matched (QA)
    source          text default 'census',
    geocoded_at     timestamptz default now()
);
