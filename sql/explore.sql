select count(*)
from raw_tpd_reported_crimes;

SELECT
    payload->'attributes'
FROM raw_tpd_reported_crimes
LIMIT 1;

SELECT DISTINCT jsonb_object_keys(payload->'attributes')
FROM raw_tpd_reported_crimes
ORDER BY 1;