-- ============================================================================
-- scratch.sql  ·  playground for ad-hoc queries in VSCode / SQLTools
-- ----------------------------------------------------------------------------
-- HOW TO RUN in VSCode (after connecting the "tucson crime" connection):
--   * Click the "▶ Run on active connection" CodeLens above any statement, OR
--   * Put the cursor in a statement and press  Cmd+E Cmd+E  (run current), OR
--   * Select several statements and press      Cmd+E Cmd+E  (run selection).
-- Results open in a SQLTools results tab you can sort/filter/export.
-- ============================================================================


-- ---- REPORTING LAYER (what the website will read) --------------------------

-- Latest bike thefts, map-ready
select occurred_at, ward, neighborhood, address, lat, lon
from mart_bike_crimes
order by occurred_at desc
limit 50;

-- Thefts by ward
select ward, count(*) as thefts
from mart_bike_crimes
group by ward
order by thefts desc;

-- Yearly trend
select year, sum(incidents) as thefts
from mart_bike_stats
group by year
order by year;

-- Hotspot neighborhoods
select neighborhood, count(*) as thefts
from mart_bike_crimes
where neighborhood <> ''
group by neighborhood
order by thefts desc
limit 15;

-- Hour-of-day pattern (when do bikes get stolen?)
select extract(hour from occurred_at)::int as hour, count(*) as thefts
from mart_bike_crimes
group by hour
order by hour;


-- ---- TRANSFORM LAYER (cleaned, before filtering) ---------------------------

select occurred_at, offense_code, offense_description, ward, lat, lon, source_layer
from int_incidents
where is_bicycle
order by occurred_at desc
limit 20;


-- ---- RAW LAYER (original ArcGIS payload) -----------------------------------

-- Peek at a full raw feature
select inci_id, source_layer, jsonb_pretty(payload)
from raw_tpd_incidents
limit 1;

-- What attribute fields does the source provide?
select distinct jsonb_object_keys(payload->'attributes') as field
from raw_tpd_incidents
order by field;
