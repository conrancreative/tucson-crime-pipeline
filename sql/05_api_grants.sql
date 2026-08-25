-- ============================================================================
-- 05_api_grants.sql  ·  expose the reporting layer to the public read API
-- ----------------------------------------------------------------------------
-- Supabase only: grants the PostgREST roles read-only access to the marts, so
-- the website can query them with the public anon key. No-op on local Postgres
-- (the anon/authenticated roles don't exist there), so it's safe to run anywhere.
-- Run AFTER 04_reporting.sql.
-- ============================================================================

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    grant usage on schema public to anon, authenticated;
    grant select on mart_bike_crimes to anon, authenticated;
    grant select on mart_bike_stats  to anon, authenticated;
  end if;
end $$;
