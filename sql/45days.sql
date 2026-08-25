CREATE TABLE IF NOT EXISTS raw_tpd_calls_last_45_days (
    objectid bigint PRIMARY KEY,
    payload jsonb NOT NULL,
    pulled_at timestamptz DEFAULT now()
);

SELECT
    payload->'attributes'->>'ADDRESS_PUBLIC' AS address_public,
    payload->'attributes'->>'NHA_NAME' AS neighborhood,
    payload->'attributes'->>'WARD' AS ward,
    payload->'attributes'->>'NatureCodeDesc' AS nature,
    payload->'geometry' AS geometry
FROM raw_tpd_calls_last_45_days
where payload->'attributes'->>'WARD' = '6'
-- LIMIT 10;

select * from raw_tpd_calls_last_45_days