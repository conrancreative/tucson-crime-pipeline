-- ============================================================================
-- 12_geocode_overrides.sql  ·  manual lat/lon for un-geocodable campus spots
-- ----------------------------------------------------------------------------
-- The U.S. Census geocoder can't place a handful of campus-interior streets
-- (University Blvd mall, James E Rogers Way, Enke Dr, National Championship Dr,
-- the 900 block of E 5th, ...). Two-part fix:
--   1. uapd_norm_addr() canonicalizes an address so formatting variants collapse
--      to one key ("744 N HIGHLAND AV" / "AVENUE" -> "744 N HIGHLAND AVE",
--      "1400 E 6 ST" -> "1400 E 6TH ST", periods dropped). The geocoder uses the
--      same idea to boost Census matches.
--   2. geocode_overrides holds a hand-picked lat/lon per canonical address. It
--      wins over the Census result in int_uapd; anything still un-placed falls
--      back to Old Main in mart_uapd_bike. Fill lat/lon in by hand.
-- ============================================================================

-- Canonical form of a street address (uppercase, no punctuation, standardized
-- suffixes, ordinal street names). Immutable so it can be used in joins/indexes.
create or replace function uapd_norm_addr(a text) returns text
language plpgsql immutable as $$
declare s text;
begin
  if a is null then return null; end if;
  s := upper(btrim(a));
  s := regexp_replace(s, '[.,]', '', 'g');          -- drop periods / commas
  s := regexp_replace(s, '\s+', ' ', 'g');          -- collapse whitespace
  -- standardize street-type suffixes
  s := regexp_replace(s, '\y(AVENUE|AV)\y',   'AVE',  'g');
  s := regexp_replace(s, '\y(BOULEVARD|BL)\y','BLVD', 'g');
  s := regexp_replace(s, '\ySTREET\y',        'ST',   'g');
  s := regexp_replace(s, '\yDRIVE\y',         'DR',   'g');
  s := regexp_replace(s, '\yROAD\y',          'RD',   'g');
  s := regexp_replace(s, '\yPLACE\y',         'PL',   'g');
  s := regexp_replace(s, '\yLANE\y',          'LN',   'g');
  s := regexp_replace(s, '\yWY\y',            'WAY',  'g');
  -- ordinal street NAMES before a suffix: "6 ST" -> "6TH ST"
  s := regexp_replace(s, '\y1 (ST|AVE)\y',            '1ST \1', 'g');
  s := regexp_replace(s, '\y2 (ST|AVE)\y',            '2ND \1', 'g');
  s := regexp_replace(s, '\y3 (ST|AVE)\y',            '3RD \1', 'g');
  s := regexp_replace(s, '\y([4-9]|1[0-9]) (ST|AVE)\y', '\1TH \2', 'g');
  return s;
end
$$;

create table if not exists geocode_overrides (
    norm_address text primary key,      -- uapd_norm_addr() of the source address
    lat          double precision,      -- <-- FILL IN by hand
    lon          double precision,      -- <-- FILL IN by hand
    label        text,                  -- human name for the spot
    example_raw  text,                  -- a sample raw address that maps here
    incidents    int,                   -- bike incidents here (prioritize by this)
    note         text
);
