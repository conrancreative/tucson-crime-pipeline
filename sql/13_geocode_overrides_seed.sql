-- ============================================================================
-- 13_geocode_overrides_seed.sql  ·  manual lat/lon for un-geocodable UA spots
-- ----------------------------------------------------------------------------
-- Campus-interior streets / intersections the U.S. Census geocoder can't place,
-- among UA bike incidents (theft + crash). Most are PRE-FILLED from OpenStreetMap
-- + Census-intersection lookups (validated inside a Tucson bounding box). The
-- rows marked "TODO" still need a lat/lon -- look the spot up on Google Maps
-- (right-click -> the first numbers are "lat, lon") and paste them in.
--
-- 44 of 53 pre-filled · 9 left to do.
-- Apply with ./apply_sql.sh sql/13_geocode_overrides_seed.sql, then refresh
-- mart_uapd_bike + mart_bike_crimes. Re-applying updates coords in place.
-- ============================================================================
-- [23 incidents] 1423 E UNIVERSITY BL   (osm:Modern Languages, 1423, East University Boulev)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1423 E UNIVERSITY BLVD',
    '1423 E UNIVERSITY BL',
    23,
    null,
    32.232744,
    -110.950089
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [21 incidents] 910 E 5TH ST   (osm:East 5th Street, West University, Tucson, Pima)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '910 E 5TH ST',
    '910 E 5TH ST',
    21,
    null,
    32.229009,
    -110.970222
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [16 incidents] 940 E 5TH ST   (osm:East 5th Street, West University, Tucson, Pima)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '940 E 5TH ST',
    '940 E 5TH ST',
    16,
    null,
    32.229009,
    -110.970222
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [12 incidents] 1721 E ENKE DR   (osm:Enke Drive, Tucson, Pima County, Arizona, 8570)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1721 E ENKE DR',
    '1721 E ENKE DR',
    12,
    null,
    32.229521,
    -110.945996
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [11 incidents] 744 N HIGHLAND AV   (osm:Albert B. Weaver Science Engineering Library, )
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '744 N HIGHLAND AVE',
    '744 N HIGHLAND AV',
    11,
    null,
    32.231182,
    -110.950659
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [10 incidents] 1503 E UNIVERSITY BL   (osm:1503, East University Boulevard, Tucson, Pima )
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1503 E UNIVERSITY BLVD',
    '1503 E UNIVERSITY BL',
    10,
    null,
    32.231639,
    -110.949515
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 8 incidents] 1713 E UNIVERSITY BL   (osm:1713, East University Boulevard, Tucson, Pima )
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1713 E UNIVERSITY BLVD',
    '1713 E UNIVERSITY BL',
    8,
    null,
    32.231652,
    -110.946509
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 7 incidents] 1009 E JAMES E ROGERS WY   (osm:Gila, 1009, East James E. Rogers Way, Tucson, )
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1009 E JAMES E ROGERS WAY',
    '1009 E JAMES E ROGERS WY',
    7,
    null,
    32.233479,
    -110.956126
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 7 incidents] 1110 E JAMES E ROGERS WY   (osm:Economics, 1110, East James E. Rogers Way, Tuc)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1110 E JAMES E ROGERS WAY',
    '1110 E JAMES E ROGERS WY',
    7,
    null,
    32.23272,
    -110.954207
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 6 incidents] 1107 E JAMES E ROGERS WY   (osm:East James E. Rogers Way, Tucson, Pima County,)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1107 E JAMES E ROGERS WAY',
    '1107 E JAMES E ROGERS WY',
    6,
    null,
    32.232985,
    -110.955332
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 6 incidents] 1127 E JAMES E ROGERS WY   (osm:Engineering, 1127, East James E. Rogers Way, T)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1127 E JAMES E ROGERS WAY',
    '1127 E JAMES E ROGERS WY',
    6,
    null,
    32.232852,
    -110.953183
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 4 incidents] 1031 E JAMES E ROGERS WY   (osm:Maricopa Hall, 1031, East James E. Rogers Way,)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1031 E JAMES E ROGERS WAY',
    '1031 E JAMES E ROGERS WY',
    4,
    null,
    32.233489,
    -110.955335
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 4 incidents] 1133 E JAMES E ROGERS WY   (osm:John W. Harshbarger Building, 1133, East James)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1133 E JAMES E ROGERS WAY',
    '1133 E JAMES E ROGERS WY',
    4,
    null,
    32.233474,
    -110.953616
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 3 incidents] 1100 E JAMES E ROGERS WY   (osm:English as a Second Language CESL, 1100, East )
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1100 E JAMES E ROGERS WAY',
    '1100 E JAMES E ROGERS WY',
    3,
    null,
    32.232637,
    -110.954754
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 3 incidents] 1209 E UNIVERSITY BL   (osm:East University Boulevard, West University, Tu)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1209 E UNIVERSITY BLVD',
    '1209 E UNIVERSITY BL',
    3,
    null,
    32.231693,
    -110.957359
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 3 incidents] 1235 E JAMES E ROGERS WY   (osm:Mines and Metallurgy, 1235, East James E. Roge)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1235 E JAMES E ROGERS WAY',
    '1235 E JAMES E ROGERS WY',
    3,
    null,
    32.233429,
    -110.95316
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 3 incidents] 1601 E UNIVERSITY BL   (osm:Flandrau Planetarium, 1601, East University Bo)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1601 E UNIVERSITY BLVD',
    '1601 E UNIVERSITY BL',
    3,
    null,
    32.232415,
    -110.947717
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 3 incidents] 1641 E ENKE DR   (TODO — find in Google Maps)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1641 E ENKE DR',
    '1641 E ENKE DR',
    3,
    null,
    32.23008201168907,
    -110.94794697444426
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 2 incidents] 525 N NATIONAL CHAMPIONSHIP DR   (TODO — find in Google Maps)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '525 N NATIONAL CHAMPIONSHIP DR',
    '525 N NATIONAL CHAMPIONSHIP DR',
    2,
    null,
    32.228880392990305,
    -110.94780676095094
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 2 incidents] 540 N VINE AV   (osm:North Vine Avenue, Monterey, Tucson, Pima Coun)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '540 N VINE AVE',
    '540 N VINE AV',
    2,
    null,
    32.246533,
    -110.949814
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 2 incidents] 750 N CHERRY AV   (osm:North Cherry Avenue, Richland Heights, Tucson,)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '750 N CHERRY AVE',
    '750 N CHERRY AV',
    2,
    null,
    32.270346,
    -110.948064
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 2 incidents] E 2ND ST / N MOUNTAIN AV   (TODO — find in Google Maps)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E 2ND ST / N MOUNTAIN AVE',
    'E 2ND ST / N MOUNTAIN AV',
    2,
    null,
    32.23398298075775,
    -110.95234513211513
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 2 incidents] E 2ND ST / N OLIVE RD   (census:E 2ND ST & OLIVE RD, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E 2ND ST / N OLIVE RD',
    'E 2ND ST / N OLIVE RD',
    2,
    null,
    32.233765,
    -110.954995
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 10000 N PARK AVE   (osm:North Park Avenue, Jefferson Park, Tucson, Pim)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '10000 N PARK AVE',
    '10000 N PARK AVE',
    1,
    null,
    32.249318,
    -110.956874
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 103 N OLIVE RD   (osm:North Olive Road, Tucson, Pima County, Arizona)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '103 N OLIVE RD',
    '103 N OLIVE RD',
    1,
    null,
    32.271427,
    -110.955002
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1031 E JAMES ROGERS WY   (manual:same as 1031 E James E Rogers Way)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1031 E JAMES ROGERS WAY',
    '1031 E JAMES ROGERS WY',
    1,
    null,
    32.233489,
    -110.955335
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1031 JAMES E ROGERS WAY   (manual:same as 1031 E James E Rogers Way)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1031 JAMES E ROGERS WAY',
    '1031 JAMES E ROGERS WAY',
    1,
    null,
    32.233489,
    -110.955335
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1103 E UNIVERSITY BLVD   (osm:East University Boulevard, West University, Tu)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1103 E UNIVERSITY BLVD',
    '1103 E UNIVERSITY BLVD',
    1,
    null,
    32.231693,
    -110.957359
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1200 E UNIVERSITY   (osm:Old Main, 1200, East University Boulevard, Tuc)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1200 E UNIVERSITY',
    '1200 E UNIVERSITY',
    1,
    null,
    32.231958,
    -110.953449
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1209 UNIVERSITY OF AZ   (TODO — find in Google Maps)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1209 UNIVERSITY OF AZ',
    '1209 UNIVERSITY OF AZ',
    1,
    null,
    null,
    null
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1212 E UNIVERSITY BLVD   (osm:East University Boulevard, Tucson, Pima County)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1212 E UNIVERSITY BLVD',
    '1212 E UNIVERSITY BLVD',
    1,
    null,
    32.232075,
    -110.948554
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1303 E JAMES E ROGERS WAY   (osm:East James E. Rogers Way, Tucson, Pima County,)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1303 E JAMES E ROGERS WAY',
    '1303 E JAMES E ROGERS WAY',
    1,
    null,
    32.232985,
    -110.955332
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1400 E 6YH ST   (TODO — find in Google Maps) -- note this should be 1400 E 6TH ST
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1400 E 6YH ST',
    '1400 E 6YH ST',
    1,
    null,
    32.2275119646913,
    -110.95048710327987
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1401 E UNIVERSITY BLVD   (osm:Administration, 1401, East University Boulevar)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1401 E UNIVERSITY BLVD',
    '1401 E UNIVERSITY BLVD',
    1,
    null,
    32.232751,
    -110.950946
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1503 E UNIVERSITY   (osm:1503, East University Boulevard, Tucson, Pima )
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1503 E UNIVERSITY',
    '1503 E UNIVERSITY',
    1,
    null,
    32.231639,
    -110.949515
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1629 E UNIVERSITY BL   (osm:Lunar and Planetary Laboratory, 1629, East Uni)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1629 E UNIVERSITY BLVD',
    '1629 E UNIVERSITY BL',
    1,
    null,
    32.232559,
    -110.947213
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] 1703 N MAPLES ST   (TODO — find in Google Maps) -- fallback to old main doesn't exist
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    '1703 N MAPLES ST',
    '1703 N MAPLES ST',
    1,
    null,
    null,
    null
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E 1ST ST / N VINE AV   (census:E 1ST ST & N VINE AVE, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E 1ST ST / N VINE AVE',
    'E 1ST ST / N VINE AV',
    1,
    null,
    32.234863,
    -110.949397
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E 2ND ST / N CAMPBELL AV   (census:E 2ND ST & N CAMPBELL AVE, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E 2ND ST / N CAMPBELL AVE',
    'E 2ND ST / N CAMPBELL AV',
    1,
    null,
    32.233837,
    -110.943939
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E 2ND ST / N HIGHLAND BIKE PATH   (census:E 2ND ST & N HIGHLAND AVE, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E 2ND ST / N HIGHLAND BIKE PATH',
    'E 2ND ST / N HIGHLAND BIKE PATH',
    1,
    null,
    32.233783,
    -110.950846
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E 2ND ST / N MARTIN AV   (census:E 2ND ST & N MARTIN AVE, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E 2ND ST / N MARTIN AVE',
    'E 2ND ST / N MARTIN AV',
    1,
    null,
    32.233837,
    -110.945239
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E 2ND ST/N MOUNTAIN AV   (TODO — find in Google Maps)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E 2ND ST/N MOUNTAIN AVE',
    'E 2ND ST/N MOUNTAIN AV',
    1,
    null,
    32.23398298075775,
    -110.95234513211513
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E 4TH ST/N SANTA RITA AV   (TODO — find in Google Maps)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E 4TH ST/N SANTA RITA AVE',
    'E 4TH ST/N SANTA RITA AV',
    1,
    null,
    32.23057463512192,
    -110.95101030327982
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E 4TH ST/N TYNDALL AV   (census:E 4TH ST & N TYNDALL AVE, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E 4TH ST/N TYNDALL AVE',
    'E 4TH ST/N TYNDALL AV',
    1,
    null,
    32.230372,
    -110.957898
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E 6TH ST / N HIGHLAND AV   (census:E 6TH ST & N HIGHLAND AVE, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E 6TH ST / N HIGHLAND AVE',
    'E 6TH ST / N HIGHLAND AV',
    1,
    null,
    32.22778,
    -110.950999
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E 6TH ST / N PARK AV   (census:E 6TH ST & N PARK AVE, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E 6TH ST / N PARK AVE',
    'E 6TH ST / N PARK AV',
    1,
    null,
    32.227762,
    -110.956354
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E HELEN ST / N HIGHLAND BIKE PATH   (census:E HELEN ST & N HIGHLAND AVE, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E HELEN ST / N HIGHLAND BIKE PATH',
    'E HELEN ST / N HIGHLAND BIKE PATH',
    1,
    null,
    32.23732,
    -110.951211
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E HELEN ST / N MOUNTAIN AV   (census:E HELEN ST & N MOUNTAIN AVE, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E HELEN ST / N MOUNTAIN AVE',
    'E HELEN ST / N MOUNTAIN AV',
    1,
    null,
    32.237302,
    -110.952448
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] E HELEN ST/N MOUNTAIN AV   (census:E HELEN ST & N MOUNTAIN AVE, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'E HELEN ST/N MOUNTAIN AVE',
    'E HELEN ST/N MOUNTAIN AV',
    1,
    null,
    32.237302,
    -110.952448
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] N CHERRY AV / E ENKE DR   (TODO — find in Google Maps)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'N CHERRY AVE / E ENKE DR',
    'N CHERRY AV / E ENKE DR',
    1,
    null,
    32.2299782903585,
    -110.94811946095086
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] N CHERRY AV / E UNIVERSITY BL   (census:N CHERRY AVE & E UNIVERSITY BLVD, TUCSON, AZ, 8571)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'N CHERRY AVE / E UNIVERSITY BLVD',
    'N CHERRY AV / E UNIVERSITY BL',
    1,
    null,
    32.231902,
    -110.948123
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] N MOUNTAIN AV / E SPEEDWAY BL   (census:N MOUNTAIN AVE & E SPEEDWAY BLVD, TUCSON, AZ, 8571)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'N MOUNTAIN AVE / E SPEEDWAY BLVD',
    'N MOUNTAIN AV / E SPEEDWAY BL',
    1,
    null,
    32.235952,
    -110.952376
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;
-- [ 1 incidents] UNIVERSITY/CHERRY   (census:E UNIVERSITY BLVD & CHERRY AVE, TUCSON, AZ, 85719)
insert into geocode_overrides (
    norm_address,
    example_raw,
    incidents,
    label,
    lat,
    lon
  )
values (
    'UNIVERSITY/CHERRY',
    'UNIVERSITY/CHERRY',
    1,
    null,
    32.231731,
    -110.948133
  ) on conflict (norm_address) do
update
set lat = excluded.lat,
  lon = excluded.lon,
  incidents = excluded.incidents,
  example_raw = excluded.example_raw;