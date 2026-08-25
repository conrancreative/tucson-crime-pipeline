#!/usr/bin/env bash
# Apply one or more .sql files to the database in .env's DATABASE_URL.
# Usage: ./apply_sql.sh sql/03_transform.sql sql/04_reporting.sql
# The connection string is read from .env (gitignored) so no password is typed.
set -euo pipefail

if [ ! -f .env ]; then echo "No .env found in $(pwd)"; exit 1; fi
set -a; source .env; set +a
if [ -z "${DATABASE_URL:-}" ]; then echo "DATABASE_URL not set in .env"; exit 1; fi

echo "Target: ${DATABASE_URL%%:*}://…@${DATABASE_URL##*@}"   # host only, hides password
for f in "$@"; do
  echo ">> applying $f"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"
done
echo "Done."
