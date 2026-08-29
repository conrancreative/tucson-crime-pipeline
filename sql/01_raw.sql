-- ============================================================================
-- 01_raw.sql  ·  RAW LAYER  (landing tables, untouched source as jsonb)
-- ============================================================================

-- Geo-enabled reported incidents (bike theft, OFFENSE='0606') pulled from the
-- spatial TPD_INCIDENTS_PUBLIC_* layers. Keyed on INCI_ID so the one-time
-- historical backfill and the ongoing 45-day pull upsert into the same table.
create table if not exists raw_tpd_incidents (
    inci_id     text primary key,
    source_layer text,                       -- which ArcGIS layer this came from
    payload     jsonb not null,              -- full feature: attributes + geometry
    pulled_at   timestamptz default now()
);
