create or replace view stg_reported_crimes as
select
    esri_oid,

    payload->'attributes'->>'IncidentID' as incident_id,
    payload->'attributes'->>'DateOccurred' as date_occurred,
    payload->'attributes'->>'Year' as year,
    payload->'attributes'->>'Month' as month,
    payload->'attributes'->>'Day' as day,

    payload->'attributes'->>'TimeOccur' as time_occur,

    payload->'attributes'->>'Division' as division,
    payload->'attributes'->>'Ward' as ward,

    payload->'attributes'->>'Offense' as offense,
    payload->'attributes'->>'OffenseDescription' as offense_description,

    payload->'attributes'->>'UCR' as ucr,
    payload->'attributes'->>'UCRDescription' as ucr_description,

    payload->'attributes'->>'CallSource' as call_source,

    pulled_at

from raw_tpd_reported_crimes;