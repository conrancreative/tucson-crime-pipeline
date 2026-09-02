-- ============================================================================
-- 15_rls_lockdown.sql  ·  security: enable RLS + drop public write access
-- ----------------------------------------------------------------------------
-- Supabase flagged rls_disabled_in_public: every base table had RLS OFF while
-- the public `anon` role (whose key ships in the frontend) held full CRUD --
-- including DELETE and TRUNCATE. That let anyone with the key wipe or edit the
-- raw data. Fix:
--   1. Enable RLS on every base table. With no policies, non-owner roles (anon,
--      authenticated) are denied all access. `postgres` (table owner) and
--      `service_role` both have rolbypassrls, so the pipeline is unaffected.
--   2. Defense in depth: revoke write privileges from anon/authenticated across
--      the schema. The frontend only needs SELECT, and only on the marts + api
--      views, which stay readable (a view runs as its owner, bypassing RLS).
-- ============================================================================

alter table raw_tpd_incidents          enable row level security;
alter table raw_tpd_reported_2026      enable row level security;
alter table raw_tpd_cfs_bike           enable row level security;
alter table raw_uapd_log               enable row level security;
alter table geocode_cache              enable row level security;
alter table geocode_overrides          enable row level security;
alter table ingest_runs                enable row level security;
alter table ref_wards                  enable row level security;
-- legacy tables from earlier iterations, still present in the project
alter table raw_tpd_reported_crimes    enable row level security;
alter table raw_tpd_calls_last_45_days enable row level security;

-- no write access for the public roles anywhere; SELECT grants are left intact
-- (RLS already blocks base-table rows; the public marts/views stay readable)
revoke insert, update, delete, truncate, references, trigger
  on all tables in schema public from anon, authenticated;
