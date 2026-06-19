#!/usr/bin/env python3
# Adapted from knowledge-catalog/okf/src/enrichment_agent/sources/bigquery.py +
# sources/base.py  —  Apache-2.0 GoogleCloudPlatform/knowledge-catalog
"""OKF BigQuery source adapter — standalone CLI.

Usage:
  okf_bq.py list     <project.dataset>            [--billing-project P]
  okf_bq.py describe <project.dataset> <id>       [--billing-project P]
  okf_bq.py sample   <project.dataset> <id> [-n N] [--billing-project P]

Requires: google-cloud-bigquery  (pip install google-cloud-bigquery)
Auth:     Application Default Credentials (gcloud auth application-default login)

Output is JSON on stdout.

<id> format for list output: "datasets/<name>" or "tables/<name>" (or "tables/<prefix>*")
"""
from __future__ import annotations

import argparse
import json
import re
import sys

_SHARD_SUFFIX_RE = re.compile(r"^(?P<prefix>.+?_)(?P<shard>\d{6,8})$")


def _require_bq():
    try:
        from google.cloud import bigquery
        return bigquery
    except ImportError:
        print(
            "google-cloud-bigquery is required for the BigQuery adapter.\n"
            "Install: pip install google-cloud-bigquery",
            file=sys.stderr,
        )
        sys.exit(1)


def _schema_to_dict(bigquery, fields) -> list[dict]:
    out = []
    for f in fields:
        entry: dict = {"name": f.name, "type": f.field_type, "mode": f.mode}
        if f.description:
            entry["description"] = f.description
        if f.fields:
            entry["fields"] = _schema_to_dict(bigquery, list(f.fields))
        out.append(entry)
    return out


def cmd_list(dataset: str, billing_project: str | None) -> int:
    bq = _require_bq()
    if "." not in dataset:
        print(f"okf_bq: dataset must be 'project.dataset', got {dataset!r}", file=sys.stderr)
        return 1
    ds_project, ds_id = dataset.split(".", 1)
    client = bq.Client(project=billing_project)
    ds_ref = bq.DatasetReference(ds_project, ds_id)
    ds_uri = (
        f"https://bigquery.googleapis.com/v2/projects/{ds_project}/datasets/{ds_id}"
    )

    concepts = [{
        "id": f"datasets/{ds_id}",
        "type": "BigQuery Dataset",
        "resource": ds_uri,
        "hint": {"dataset_project": ds_project, "dataset_id": ds_id},
    }]

    families: dict[str, list[str]] = {}
    singletons: list[str] = []
    for tbl in client.list_tables(ds_ref):
        m = _SHARD_SUFFIX_RE.match(tbl.table_id)
        if m:
            families.setdefault(m.group("prefix"), []).append(tbl.table_id)
        else:
            singletons.append(tbl.table_id)

    for prefix, shards in sorted(families.items()):
        shards_sorted = sorted(shards)
        tbl_uri = (
            f"https://bigquery.googleapis.com/v2/projects/{ds_project}"
            f"/datasets/{ds_id}/tables/{prefix}*"
        )
        concepts.append({
            "id": f"tables/{prefix}",
            "type": "BigQuery Table",
            "resource": tbl_uri,
            "hint": {
                "wildcard": True,
                "family_prefix": prefix,
                "shard_count": len(shards),
                "first_shard": shards_sorted[0],
                "last_shard": shards_sorted[-1],
            },
        })

    for table_id in sorted(singletons):
        tbl_uri = (
            f"https://bigquery.googleapis.com/v2/projects/{ds_project}"
            f"/datasets/{ds_id}/tables/{table_id}"
        )
        concepts.append({
            "id": f"tables/{table_id}",
            "type": "BigQuery Table",
            "resource": tbl_uri,
            "hint": {"wildcard": False, "table_id": table_id},
        })

    json.dump(concepts, sys.stdout, indent=2)
    print()
    return 0


def cmd_describe(dataset: str, concept_id: str, billing_project: str | None) -> int:
    bq = _require_bq()
    if "." not in dataset:
        print(f"okf_bq: dataset must be 'project.dataset'", file=sys.stderr)
        return 1
    ds_project, ds_id = dataset.split(".", 1)
    client = bq.Client(project=billing_project)
    ds_ref = bq.DatasetReference(ds_project, ds_id)

    parts = concept_id.split("/", 1)
    if len(parts) != 2:
        print(f"okf_bq: concept_id must be 'datasets/...' or 'tables/...'", file=sys.stderr)
        return 1
    kind, name = parts

    if kind == "datasets":
        ds = client.get_dataset(ds_ref)
        data = {
            "dataset_project": ds_project,
            "dataset_id": ds_id,
            "friendly_name": ds.friendly_name,
            "description": ds.description,
            "location": ds.location,
            "labels": dict(ds.labels or {}),
            "created": ds.created.isoformat() if ds.created else None,
            "modified": ds.modified.isoformat() if ds.modified else None,
        }
        json.dump(data, sys.stdout, indent=2)
        print()
        return 0

    if kind == "tables":
        # For shard families, name ends with the family prefix (no shard suffix)
        # Try name as-is first, then look for the latest shard
        table_id = name.rstrip("*")
        m = _SHARD_SUFFIX_RE.match(table_id)
        if not m:
            # Check if it's a shard family prefix
            try:
                tables = [t.table_id for t in client.list_tables(ds_ref)
                          if t.table_id.startswith(table_id)
                          and _SHARD_SUFFIX_RE.match(t.table_id)]
                if tables:
                    table_id = sorted(tables)[-1]  # use last shard
            except Exception:
                pass

        tbl = client.get_table(ds_ref.table(table_id))
        data: dict = {
            "dataset_project": ds_project,
            "dataset_id": ds_id,
            "table_id": table_id,
            "friendly_name": tbl.friendly_name,
            "description": tbl.description,
            "labels": dict(tbl.labels or {}),
            "num_rows": tbl.num_rows,
            "num_bytes": tbl.num_bytes,
            "created": tbl.created.isoformat() if tbl.created else None,
            "modified": tbl.modified.isoformat() if tbl.modified else None,
            "schema": _schema_to_dict(bq, list(tbl.schema or [])),
        }
        if tbl.time_partitioning:
            data["time_partitioning"] = {
                "type": tbl.time_partitioning.type_,
                "field": tbl.time_partitioning.field,
                "expiration_ms": tbl.time_partitioning.expiration_ms,
            }
        if tbl.range_partitioning:
            rp = tbl.range_partitioning
            data["range_partitioning"] = {
                "field": rp.field,
                "range": {"start": rp.range_.start, "end": rp.range_.end, "interval": rp.range_.interval},
            }
        if tbl.clustering_fields:
            data["clustering_fields"] = list(tbl.clustering_fields)
        json.dump(data, sys.stdout, indent=2)
        print()
        return 0

    print(f"okf_bq: unknown concept kind: {kind!r}", file=sys.stderr)
    return 1


def cmd_sample(dataset: str, concept_id: str, n: int, billing_project: str | None) -> int:
    bq = _require_bq()
    if "." not in dataset:
        print(f"okf_bq: dataset must be 'project.dataset'", file=sys.stderr)
        return 1
    ds_project, ds_id = dataset.split(".", 1)
    client = bq.Client(project=billing_project)
    ds_ref = bq.DatasetReference(ds_project, ds_id)

    parts = concept_id.split("/", 1)
    if len(parts) != 2 or parts[0] != "tables":
        print(f"okf_bq: sample only supported for tables/ concepts", file=sys.stderr)
        return 1
    _, name = parts
    table_id = name.rstrip("*")

    # Resolve shard family to latest shard
    m = _SHARD_SUFFIX_RE.match(table_id)
    if not m:
        try:
            shards = [t.table_id for t in client.list_tables(ds_ref)
                      if t.table_id.startswith(table_id)
                      and _SHARD_SUFFIX_RE.match(t.table_id)]
            if shards:
                table_id = sorted(shards)[-1]
        except Exception:
            pass

    table_ref = ds_ref.table(table_id)
    try:
        tbl = client.get_table(table_ref)
        table_type = (getattr(tbl, "table_type", None) or "TABLE").upper()
        if table_type == "TABLE":
            row_iter = client.list_rows(table_ref, max_results=n)
        else:
            sql = (
                f"SELECT * FROM `{ds_project}.{ds_id}.{table_id}` LIMIT {int(n)}"
            )
            row_iter = client.query(sql).result()
        rows = [dict(r.items()) for r in row_iter]
        json.dump(rows, sys.stdout, indent=2, default=str)
        print()
        return 0
    except Exception as e:
        json.dump({"error": str(e)}, sys.stdout)
        print()
        return 1


def main() -> int:
    p = argparse.ArgumentParser(prog="okf_bq.py")
    p.add_argument("--billing-project", default=None, metavar="PROJECT")
    sub = p.add_subparsers(dest="command", required=True)

    ls = sub.add_parser("list")
    ls.add_argument("dataset", metavar="project.dataset")

    desc = sub.add_parser("describe")
    desc.add_argument("dataset", metavar="project.dataset")
    desc.add_argument("concept_id", metavar="id")

    samp = sub.add_parser("sample")
    samp.add_argument("dataset", metavar="project.dataset")
    samp.add_argument("concept_id", metavar="id")
    samp.add_argument("-n", type=int, default=5)

    args = p.parse_args()
    bp = args.billing_project

    if args.command == "list":
        return cmd_list(args.dataset, bp)
    if args.command == "describe":
        return cmd_describe(args.dataset, args.concept_id, bp)
    if args.command == "sample":
        return cmd_sample(args.dataset, args.concept_id, args.n, bp)
    return 1


if __name__ == "__main__":
    sys.exit(main())
