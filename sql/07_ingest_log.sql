-- ============================================================================
-- 07_ingest_log.sql  ·  per-pull freshness log
-- ----------------------------------------------------------------------------
-- One row per ingest run so we can tell whether each pull is current. Because
-- bike thefts are sparse, we also record the source's "leading edge" = the most
-- recent crime of ANY type in the 45-day layer (a denser freshness signal).
-- Populated by pull_tpd_incidents.py at the end of every run.
-- ============================================================================

create table if not exists ingest_runs (
    id                      bigserial primary key,
    run_at                  timestamptz not null default now(),
    mode                    text,               -- 'backfill' | 'refresh'
    bikes_processed         integer,            -- bike rows upserted this run
    source_45d_count        integer,            -- total crimes in the 45-day layer now
    source_latest_occurred  timestamptz,        -- newest crime (any type) — occur time
    source_latest_reported  timestamptz,        -- newest crime (any type) — report time
    our_latest_bike         timestamptz         -- newest bike theft we hold
);

create index if not exists ingest_runs_run_at_idx on ingest_runs (run_at desc);


-- Latest run + how stale the source is (Arizona time). Handy for a "data updated"
-- indicator on the site and for a quick freshness check.
create or replace view mart_freshness as
select
    run_at,
    (run_at at time zone 'America/Phoenix')                 as run_at_az,
    mode,
    bikes_processed,
    source_45d_count,
    (source_latest_reported at time zone 'America/Phoenix') as source_latest_reported_az,
    (our_latest_bike at time zone 'America/Phoenix')        as our_latest_bike_az,
    (now()::date - source_latest_reported::date)            as source_lag_days
from ingest_runs
order by run_at desc
limit 1;


-- read-only API access (Supabase; no-op locally where the anon role is absent)
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    grant select on mart_freshness to anon, authenticated;
  end if;
end $$;
