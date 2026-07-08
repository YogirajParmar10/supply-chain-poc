"""
Load MES data from PostgreSQL into ServiceNow via the REST Table API.

Reads machine_downtime from the local database and inserts it into the
custom table u_machine_downtime. Safe to re-run: existing records (matched
on the business key) are skipped.

Required .env additions:
    SN_INSTANCE=https://dev404273.service-now.com
    SN_USER=admin
    SN_PASSWORD=<instance admin password>

Usage:
    python -m scripts.load_servicenow             # load everything
    python -m scripts.load_servicenow --limit 10  # only first N rows per table
"""

import argparse
import os
import sys

import requests
from sqlalchemy import text

from generator.utils.db import get_engine

PAGE_SIZE = 1000

# (postgres table, servicenow table, business key, postgres column -> u_ field)
LOADS = [
    (
        "machine_downtime",
        "u_machine_downtime",
        "u_downtime_id",
        {
            "downtime_id": "u_downtime_id",
            "plant_id": "u_plant_id",
            "machine_name": "u_machine_name",
            "start_time": "u_start_time",
            "end_time": "u_end_time",
            "reason": "u_reason",
        },
    ),
]


def get_session() -> tuple[requests.Session, str]:
    instance = os.getenv("SN_INSTANCE", "").rstrip("/")
    user = os.getenv("SN_USER")
    password = os.getenv("SN_PASSWORD")
    if not (instance and user and password):
        sys.exit("Set SN_INSTANCE, SN_USER and SN_PASSWORD in .env")

    session = requests.Session()
    session.auth = (user, password)
    session.headers.update({"Accept": "application/json"})
    return session, instance


def fetch_existing_keys(session: requests.Session, instance: str, table: str, key_field: str) -> set[str]:
    keys: set[str] = set()
    offset = 0
    while True:
        response = session.get(
            f"{instance}/api/now/table/{table}",
            params={
                "sysparm_fields": key_field,
                "sysparm_limit": PAGE_SIZE,
                "sysparm_offset": offset,
            },
            timeout=60,
        )
        response.raise_for_status()
        page = response.json()["result"]
        keys.update(row[key_field] for row in page if row.get(key_field))
        if len(page) < PAGE_SIZE:
            return keys
        offset += PAGE_SIZE


def load_table(session, instance, pg_table, sn_table, key_field, mapping, limit=None) -> None:
    existing = fetch_existing_keys(session, instance, sn_table, key_field)
    print(f"{sn_table}: {len(existing)} records already present")

    columns = ", ".join(mapping)
    query = f"SELECT {columns} FROM {pg_table} ORDER BY {next(iter(mapping))}"
    if limit:
        query += f" LIMIT {int(limit)}"
    with get_engine().connect() as conn:
        rows = conn.execute(text(query)).mappings().all()

    inserted = skipped = failed = 0
    for row in rows:
        payload = {
            sn_field: "" if row[pg_col] is None else str(row[pg_col])
            for pg_col, sn_field in mapping.items()
        }
        if payload[key_field] and payload[key_field] in existing:
            skipped += 1
            continue

        response = session.post(f"{instance}/api/now/table/{sn_table}", json=payload, timeout=60)
        if response.ok:
            inserted += 1
        else:
            failed += 1
            print(f"  FAILED {payload.get(key_field)}: {response.status_code} {response.text[:200]}")

    print(f"{sn_table}: inserted {inserted}, skipped {skipped}, failed {failed} (source rows: {len(rows)})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load MES data into ServiceNow")
    parser.add_argument("--limit", type=int, default=None, help="max rows per table")
    args = parser.parse_args()

    session, instance = get_session()
    for pg_table, sn_table, key_field, mapping in LOADS:
        load_table(session, instance, pg_table, sn_table, key_field, mapping, limit=args.limit)


if __name__ == "__main__":
    main()
