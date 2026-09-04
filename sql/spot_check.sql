-- ============================================================================
-- spot_check.sql  ·  data freshness spot-check (run any time)
-- ----------------------------------------------------------------------------
-- Run:  set -a; source .env; set +a; psql "$DATABASE_URL" -f sql/spot_check.sql
--
-- Two checks:
--   1. SOURCE vs MAP  -- newest theft in each source (the int_ views) vs what
--      mart_bike_crimes actually shows. If MAP is behind, the mart needs a
--      refresh (`refresh materialized view mart_bike_crimes;`).
--   2. api_data_sources -- the live per-source snapshot the Sources tab reads
--      (latest row + when we last pulled + row count).
-- ============================================================================

\echo '=== 1. SOURCE leading edge  vs  what the MAP shows ==='
with src as (
  select 'TPD reported 2026'   as source, max(occurred_at)::date as source_latest
    from int_reported_2026 where is_bicycle
  union all
  select 'TPD history (<=2025)', max(occurred_at)::date
    from int_incidents where is_bicycle and year <= 2025
  union all
  select 'UAPD thefts',          max(occurred_at)::date
    from int_uapd where is_bike_theft
),
mart as (
  select 'TPD reported 2026'   as source, max(occurred_at_az)::date as map_latest
    from mart_bike_crimes where source = 'TPD' and year = 2026
  union all
  select 'TPD history (<=2025)', max(occurred_at_az)::date
    from mart_bike_crimes where source = 'TPD' and year <= 2025
  union all
  select 'UAPD thefts',          max(occurred_at_az)::date
    from mart_bike_crimes where source = 'UAPD'
)
select s.source, s.source_latest, m.map_latest,
       case when s.source_latest is not distinct from m.map_latest
            then 'in sync' else '*** MAP STALE -> refresh mart_bike_crimes ***' end as status
from src s join mart m using (source)
order by s.source;

\echo ''
\echo '=== 2. api_data_sources (what the Sources tab shows) ==='
select source_key, latest_data_row, last_refreshed_az::timestamp(0) as last_refreshed_az, row_count
from api_data_sources
order by source_key;
