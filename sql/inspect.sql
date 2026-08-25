-- ============================================================================
-- inspect.sql  ·  walk every layer of the pipeline and print a sanity summary.
-- Run:  psql postgresql://localhost/tucson_crime -f sql/inspect.sql
-- ============================================================================
\pset border 2
\timing off

\echo '\n========== 1. RAW LAYER (raw_tpd_incidents) =========='
select count(*) as incidents,
       count(distinct source_layer) as source_layers,
       min(pulled_at)::date as first_pull,
       max(pulled_at)::date as last_pull
from raw_tpd_incidents;

\echo '\n-- rows per source layer --'
select source_layer, count(*) as rows
from raw_tpd_incidents
group by 1 order by 1;

\echo '\n-- one raw payload (attributes trimmed) --'
select inci_id,
       payload->'attributes'->>'OFFENSE'    as offense,
       payload->'attributes'->>'STATUTDESC' as statute,
       payload->'geometry'                  as geometry
from raw_tpd_incidents
limit 1;


\echo '\n========== 2. TRANSFORM LAYER (int_incidents) =========='
select count(*)                              as total,
       count(*) filter (where is_bicycle)    as bikes,
       count(*) filter (where lat is not null) as geocoded,
       count(*) filter (where occurred_at is null) as null_dates,
       min(year) as first_year, max(year) as last_year
from int_incidents;

\echo '\n-- 5 cleaned bike rows --'
select occurred_at, ward, neighborhood, address, round(lat::numeric,4) lat, round(lon::numeric,4) lon
from int_incidents
where is_bicycle
order by occurred_at desc
limit 5;


\echo '\n========== 3. REPORTING: mart_bike_crimes (map points) =========='
select count(*) as mappable_points,
       count(distinct ward) as wards,
       min(occurred_at)::date as earliest,
       max(occurred_at)::date as latest
from mart_bike_crimes;

\echo '\n-- thefts by ward --'
select coalesce(ward,'(unknown)') as ward, count(*) as thefts
from mart_bike_crimes
group by 1 order by 2 desc;

\echo '\n-- top 10 neighborhoods --'
select coalesce(nullif(neighborhood,''),'(unknown)') as neighborhood, count(*) as thefts
from mart_bike_crimes
group by 1 order by 2 desc limit 10;


\echo '\n========== 4. REPORTING: mart_bike_stats (trend) =========='
select count(*) as stat_rows,
       min(month) as first_month, max(month) as last_month,
       sum(incidents) as total_incidents
from mart_bike_stats;

\echo '\n-- yearly trend --'
select year, sum(incidents) as thefts
from mart_bike_stats
group by 1 order by 1;

\echo '\n-- last 12 months --'
select to_char(month,'YYYY-MM') as month, sum(incidents) as thefts
from mart_bike_stats
group by 1 order by 1 desc limit 12;

\echo '\nDone.'
