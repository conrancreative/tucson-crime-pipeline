-- ============================================================================
-- 09_uapd.sql  ·  RAW LANDING for the UAPD Daily Crime Log (scraped)
-- ----------------------------------------------------------------------------
-- University of Arizona PD Clery Act daily crime & safety log, scraped from
-- https://uapd.arizona.edu/public-information/uapd-daily-activity-log (paginated
-- HTML table, ~40k rows back to Apr 2022). Populated by pull_uapd_log.py.
-- Keyed on case_number and upserted (dispositions can change after first report).
--
-- NOTE: the log has a street ADDRESS but NO coordinates — mapping UA bike crimes
-- will require geocoding the address (added in a later step).
-- ============================================================================

create table if not exists raw_uapd_log (
    case_number   text primary key,
    report_dt     timestamp,        -- Arizona local (no DST); parsed from the log
    offense_dt    timestamp,
    nature        text,             -- "Nature of Crime" (e.g. 'Bicycle Larceny')
    address       text,             -- campus-area street address (no lat/lon)
    disposition   text,
    scraped_at    timestamptz default now()
);

create index if not exists raw_uapd_log_nature_idx  on raw_uapd_log (nature);
create index if not exists raw_uapd_log_offense_idx on raw_uapd_log (offense_dt);


-- ----------------------------------------------------------------------------
-- TRANSFORM: clean the log + join geocoded coordinates. Uses offense time when
-- present, else report time. Drops a few malformed source dates (year < 2015).
-- ----------------------------------------------------------------------------
-- Coordinate preference: manual override (campus spots Census can't place) >
-- Census geocode > NULL (mart_uapd_bike then falls back to Old Main).
create or replace view int_uapd as
select
    u.case_number,
    coalesce(u.offense_dt, u.report_dt)              as occurred_at,   -- Arizona local
    u.report_dt,
    u.nature,
    u.address,
    u.disposition,
    coalesce(o.lat, g.lat)                           as lat,
    coalesce(o.lon, g.lon)                           as lon,
    -- `nature` is inconsistent free text (case, punctuation, word order, typos,
    -- compound offenses) and UAPD switched from ALL-CAPS codes to Title Case
    -- prose around 2026-06. Classify by content, not exact string:
    --   theft = a larceny/theft term + a bicycle term (either order)
    --   crash = a bicycle term + an accident/traffic term (and not a theft)
    -- 'larcen' also catches the LARCENT typo; 'bicy' catches BICYLCES / LARCENYBICYCLES.
    (u.nature ~* '(larcen|theft).*(bicy|bike)|(bicy|bike).*(larcen|theft)')  as is_bike_theft,
    (u.nature ~* '(bicy|bike)'
        and u.nature ~* '(accident|traffic|traf|crash|collision)'
        and u.nature !~* '(larcen|theft)')                                   as is_bike_crash
from raw_uapd_log u
left join geocode_cache     g on g.address = u.address
left join geocode_overrides o on o.norm_address = uapd_norm_addr(u.address)
                              and o.lat is not null
where coalesce(u.offense_dt, u.report_dt) >= timestamp '2015-01-01';


-- ----------------------------------------------------------------------------
-- REPORTING: UA bike crimes (theft + bike-specific injury crashes), map-ready.
-- ----------------------------------------------------------------------------
-- Un-geocodable addresses (dorm names, vague spots) fall back to Old Main (the
-- campus center) and are flagged approximate, so every bike incident still maps.
drop materialized view if exists mart_uapd_bike;
create materialized view mart_uapd_bike as
select
    case_number as id,
    occurred_at,
    nature,
    case when is_bike_theft then 'theft' else 'crash' end as kind,
    address,
    disposition,
    coalesce(lat, 32.2313)  as lat,     -- Old Main fallback
    coalesce(lon, -110.9558) as lon,
    (lat is not null)       as geocoded  -- false = approximate (placed at campus center)
from int_uapd
where (is_bike_theft or is_bike_crash)
order by occurred_at desc;
create unique index if not exists mart_uapd_bike_id_idx on mart_uapd_bike (id);

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    grant select on mart_uapd_bike to anon, authenticated;
  end if;
end $$;
