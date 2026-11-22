#!/usr/bin/env bash
# Build the pipeline schema using DATABASE_URL from the repo's .env.
# Run after creating the database. Import data separately afterward.
# Re-running rebuilds dependent views and marts, retaining the raw tables.
set -euo pipefail

cd "$(dirname "$0")"

./apply_sql.sh \
  sql/01_raw.sql \
  sql/10_geocode.sql \
  sql/12_geocode_overrides.sql \
  sql/03_transform.sql \
  sql/06_ref_wards.sql \
  sql/07_ingest_log.sql \
  sql/11_reported_2026.sql \
  sql/09_uapd.sql \
  sql/17_ref_neighborhoods.sql \
  sql/04_reporting.sql \
  sql/05_api_grants.sql \
  sql/08_cfs_bike.sql \
  sql/16_ingest_heartbeat.sql \
  sql/14_api_data_sources.sql \
  sql/18_pag_bikeways.sql \
  sql/19_pag_bikemap_and_tugo.sql \
  sql/20_roadway_context.sql \
  sql/21_osm_network.sql
