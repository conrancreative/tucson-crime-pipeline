-- ============================================================================
-- 13_geocode_overrides_seed.sql  ·  FILL-IN list for un-geocodable UA bike spots
-- ----------------------------------------------------------------------------
-- These are the canonical campus addresses that the Census geocoder can't place
-- (after normalization), covering ~176 bike incidents. Rows are ordered by
-- incident count -- filling the top ones recovers the most coverage.
--
-- HOW TO FILL IN:
--   1. Look each address up (Google Maps: right-click the spot -> copy lat,lon).
--   2. Put the numbers in the `null, null` at the end of each row: (..., LAT, LON).
--      e.g.  values ('910 E 5TH ST', '910 E 5TH ST', 21, 'McKale/athletics', 32.2287, -110.9490)
--   3. Leave `label` as a short human note or null. Leave junk rows blank
--      (Old-Main fallback still catches them):
--        1400 E 6YH ST   -> typo for 1400 E 6TH ST
--        1209 UNIVERSITY OF AZ, 10000 N PARK AVE -> unusable, skip
--   4. Apply:  ./apply_sql.sh sql/13_geocode_overrides_seed.sql
--      then refresh:  refresh materialized view mart_uapd_bike;
--                     refresh materialized view mart_bike_crimes;
--
-- Re-running this file preserves any lat/lon you've entered (on-conflict updates
-- only the incident count + example), so it's safe to regenerate.
--
-- Clusters (same complex ~= same coords):
--   E UNIVERSITY BLVD 1103-1723 = the pedestrian mall / student union area
--   E JAMES E ROGERS WAY 1009-1235 = engineering quad
--   910/940 E 5TH ST, 1641/1721 E ENKE DR, 525 NATIONAL CHAMPIONSHIP DR = athletics
--   "X / Y" rows are intersections.
-- ============================================================================

insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1423 E UNIVERSITY BLVD', '1423 E UNIVERSITY BL', 22, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('910 E 5TH ST', '910 E 5TH ST', 21, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('940 E 5TH ST', '940 E 5TH ST', 16, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1721 E ENKE DR', '1721 E ENKE DR', 12, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('744 N HIGHLAND AVE', '744 N HIGHLAND AV', 11, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1503 E UNIVERSITY BLVD', '1503 E UNIVERSITY BL', 10, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1713 E UNIVERSITY BLVD', '1713 E UNIVERSITY BL', 8, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1009 E JAMES E ROGERS WAY', '1009 E JAMES E ROGERS WY', 7, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1110 E JAMES E ROGERS WAY', '1110 E JAMES E ROGERS WY', 7, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1107 E JAMES E ROGERS WAY', '1107 E JAMES E ROGERS WY', 6, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1127 E JAMES E ROGERS WAY', '1127 E JAMES E ROGERS WY', 6, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1031 E JAMES E ROGERS WAY', '1031 E JAMES E ROGERS WY', 4, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1133 E JAMES E ROGERS WAY', '1133 E JAMES E ROGERS WY', 4, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1100 E JAMES E ROGERS WAY', '1100 E JAMES E ROGERS WY', 3, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1209 E UNIVERSITY BLVD', '1209 E UNIVERSITY BL', 3, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1235 E JAMES E ROGERS WAY', '1235 E JAMES E ROGERS WY', 3, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1601 E UNIVERSITY BLVD', '1601 E UNIVERSITY BL', 3, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1641 E ENKE DR', '1641 E ENKE DR', 2, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('525 N NATIONAL CHAMPIONSHIP DR', '525 N NATIONAL CHAMPIONSHIP DR', 2, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('540 N VINE AVE', '540 N VINE AV', 2, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('750 N CHERRY AVE', '750 N CHERRY AVE', 2, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('E 2ND ST / N OLIVE RD', 'E 2ND ST / N OLIVE RD', 2, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('10000 N PARK AVE', '10000 N PARK AVE', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('103 N OLIVE RD', '103 N OLIVE RD', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1031 E JAMES ROGERS WAY', '1031 E JAMES ROGERS WY', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1031 JAMES E ROGERS WAY', '1031 JAMES E ROGERS WAY', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1103 E UNIVERSITY BLVD', '1103 E UNIVERSITY BLVD', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1209 UNIVERSITY OF AZ', '1209 UNIVERSITY OF AZ', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1212 E UNIVERSITY BLVD', '1212 E UNIVERSITY BLVD', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1400 E 6YH ST', '1400 E 6YH ST', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1401 E UNIVERSITY BLVD', '1401 E UNIVERSITY BLVD', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1503 E UNIVERSITY', '1503 E UNIVERSITY', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1629 E UNIVERSITY BLVD', '1629 E UNIVERSITY BL', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('1703 N MAPLES ST', '1703 N MAPLES ST', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('E 2ND ST / N CAMPBELL AVE', 'E 2ND ST / N CAMPBELL AV', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('E 2ND ST / N MARTIN AVE', 'E 2ND ST / N MARTIN AV', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('E 2ND ST/N MOUNTAIN AVE', 'E 2ND ST/N MOUNTAIN AV', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('E HELEN ST / N HIGHLAND BIKE PATH', 'E HELEN ST / N HIGHLAND BIKE PATH', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('E HELEN ST / N MOUNTAIN AVE', 'E HELEN ST / N MOUNTAIN AV', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('N CHERRY AVE / E ENKE DR', 'N CHERRY AV / E ENKE DR', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('N CHERRY AVE / E UNIVERSITY BLVD', 'N CHERRY AV / E UNIVERSITY BL', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
insert into geocode_overrides (norm_address, example_raw, incidents, label, lat, lon) values ('N MOUNTAIN AVE / E SPEEDWAY BLVD', 'N MOUNTAIN AV / E SPEEDWAY BL', 1, null, null, null)
  on conflict (norm_address) do update set incidents = excluded.incidents, example_raw = excluded.example_raw;
