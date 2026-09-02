-- ============================================================================
-- 14_api_data_sources.sql  ·  live status feed for the "Data Sources" tab
-- ----------------------------------------------------------------------------
-- One row per upstream source with: the date of the latest record we hold,
-- when the source was last refreshed, and how many rows we store. The frontend
-- joins these live values to static per-source copy (name, endpoint, blurb) and
-- flags a *live* source as stale when it hasn't refreshed in > 48h. Static
-- sources (historical year layers, ward boundaries) are backfilled once and are
-- not expected to refresh, so the frontend exempts them from the staleness rule.
-- ============================================================================

create or replace view api_data_sources as
select 'reported_2026'::text as source_key,
  (select max(occurred_at)::date from int_reported_2026 where is_bicycle)         as latest_data_row,
  (select max(pulled_at) from raw_tpd_reported_2026)                              as last_refreshed,
  (select max(pulled_at) at time zone 'America/Phoenix' from raw_tpd_reported_2026) as last_refreshed_az,
  (select count(*)::int from raw_tpd_reported_2026)                               as row_count
union all
select 'uapd',
  (select max(coalesce(offense_dt, report_dt))::date from raw_uapd_log),
  (select max(scraped_at) from raw_uapd_log),
  (select max(scraped_at) at time zone 'America/Phoenix' from raw_uapd_log),
  (select count(*)::int from raw_uapd_log)
union all
select 'incidents_history',
  (select max(occurred_at)::date from int_incidents where is_bicycle and year <= 2025),
  (select max(pulled_at) from raw_tpd_incidents where source_layer like 'y%'),
  (select max(pulled_at) at time zone 'America/Phoenix' from raw_tpd_incidents where source_layer like 'y%'),
  (select count(*)::int from raw_tpd_incidents where source_layer like 'y%')
union all
select 'incidents_45day',
  (select max(occurred_at)::date from int_incidents),               -- leading edge = the 45-day rows
  (select max(pulled_at) from raw_tpd_incidents where source_layer = 'last45'),
  (select max(pulled_at) at time zone 'America/Phoenix' from raw_tpd_incidents where source_layer = 'last45'),
  (select count(*)::int from raw_tpd_incidents where source_layer = 'last45')
union all
select 'cfs_bike',
  (select max(occurred_at)::date from int_cfs_bike),
  (select max(pulled_at) from raw_tpd_cfs_bike),
  (select max(pulled_at) at time zone 'America/Phoenix' from raw_tpd_cfs_bike),
  (select count(*)::int from raw_tpd_cfs_bike)
union all
select 'geocoding',
  null::date,
  (select max(geocoded_at) from geocode_cache),
  (select max(geocoded_at) at time zone 'America/Phoenix' from geocode_cache),
  (select count(*)::int from geocode_cache)
union all
select 'wards',
  null::date,
  (select max(pulled_at) from ref_wards),
  (select max(pulled_at) at time zone 'America/Phoenix' from ref_wards),
  (select count(*)::int from ref_wards);

-- read-only API access (Supabase; no-op locally where the anon role is absent)
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    grant select on api_data_sources to anon, authenticated;
  end if;
end $$;
