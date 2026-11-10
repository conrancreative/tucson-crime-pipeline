"""Capture every feed advertised by Tugo's public GBFS 3.0 manifest.

Each run stores a complete response snapshot (including empty feeds) in
raw_tugo_gbfs_snapshots. The daily workflow therefore preserves a daily history
while preview_tugo_stations exposes the latest inventory and availability.
"""

import json
import os
import sys
from datetime import datetime, timezone

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
MANIFEST_URL = "https://tucson.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json"


def fetch(session, url):
    response = session.get(url, timeout=45)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or "data" not in payload:
        raise RuntimeError(f"Unexpected GBFS response from {url}")
    return payload


def parse_updated_at(payload):
    value = payload.get("last_updated")
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def collect(session):
    manifest = fetch(session, MANIFEST_URL)
    version = manifest.get("version", "3.0")
    captured_at = datetime.now(timezone.utc)
    results = [(
        "gbfs", MANIFEST_URL, version, parse_updated_at(manifest), captured_at,
        json.dumps(manifest),
    )]
    feeds = manifest.get("data", {}).get("feeds", [])
    if not feeds:
        raise RuntimeError("GBFS manifest did not advertise any feeds")

    for feed in feeds:
        name, url = feed.get("name"), feed.get("url")
        if not name or not url:
            raise RuntimeError(f"Invalid GBFS feed entry: {feed}")
        payload = fetch(session, url)
        results.append((
            name, url, version, parse_updated_at(payload), captured_at,
            json.dumps(payload),
        ))
        print(f"  captured {name}")
    return results


def save(conn, rows):
    cur = conn.cursor()
    try:
        execute_values(cur, """
            insert into raw_tugo_gbfs_snapshots
                (feed_name, feed_url, feed_version, feed_updated_at, captured_at, payload)
            values %s
        """, rows, template="(%s,%s,%s,%s,%s,%s::jsonb)")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def main():
    if not DATABASE_URL:
        sys.exit("DATABASE_URL is required")
    session = requests.Session()
    session.headers.update({"User-Agent": "Tucson bike infrastructure data pipeline"})
    print("Discovering and capturing all Tugo GBFS 3.0 feeds ...")
    rows = collect(session)
    conn = psycopg2.connect(DATABASE_URL)
    try:
        save(conn, rows)
    finally:
        conn.close()
        session.close()
    print(f"Done. Captured {len(rows) - 1} GBFS feeds plus the manifest.")


if __name__ == "__main__":
    main()
