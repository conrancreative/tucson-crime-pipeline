-- ============================================================================
-- 16_ingest_heartbeat.sql  ·  "this step ran" heartbeat
-- ----------------------------------------------------------------------------
-- Some ingest steps don't write a data row every run. The geocoder, for
-- example, only inserts into geocode_cache when a *new* distinct address turns
-- up -- on a small campus footprint most days add none, so max(geocoded_at)
-- freezes even though the step ran and did its job. That made the Data Sources
-- tab flag geocoding "stale" while the pipeline was healthy.
--
-- This table records the wall-clock time each such step last COMPLETED, keyed
-- by step name, so freshness reflects "did the step run" rather than "did the
-- data grow". One row per step, upserted at the end of the step's script.
-- ============================================================================

create table if not exists ingest_heartbeat (
    step text primary key
    , ran_at timestamptz not null default now()
    , note text -- optional human-readable summary of the run
);
