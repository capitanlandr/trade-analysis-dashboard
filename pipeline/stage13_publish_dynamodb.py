#!/usr/bin/env python3
"""
Stage 13: Publish Dashboard JSON to DynamoDB
============================================

Publishes the JSON artifacts that stages 8-12 already wrote to
dashboard/frontend/public/ into the DynamoDB table that backs the Lambda API.

WHY THIS EXISTS
---------------
The Lambda API was originally fed by `enrichment_lambda`, which *reimplemented*
the pipeline's valuation logic (DynastyProcess historical-commit lookups, pick
tier tables, trade analysis) in a second 2,500-line codebase. The two copies
drifted: enrichment_lambda has zero references to the 2026 pick cutover date the
pipeline applies in three places, and `ingestion_lambda` hardcoded a 12-team name
list that still contained six renamed teams. That is why the Lambda-served site
showed fewer trades and stale team names than the static site.

This stage replaces both of those Lambdas with a pure serializer. It performs no
Sleeper calls, no GitHub lookups, and no valuation math, so it cannot drift from
the pipeline: whatever stages 1-12 computed is exactly what lands in DynamoDB.

DESIGN RULE (important -- do not relax this)
--------------------------------------------
This stage MUST NOT compute domain values. It may only:
  1. copy an artifact's bytes under a key, and
  2. filter a flat, season-tagged list and recompute envelope counts that are
     pure functions of the filtered list (totalTrades, dateRange).

If you need a per-season view of an artifact whose body is an *aggregate*
(waiver manager_activity, churn_metrics, trade metrics), do NOT aggregate here.
Change the upstream stage to emit a per-season file and publish that file. The
moment this stage starts aggregating, it becomes a second source of truth and
the original bug returns.

TABLE SCHEMA
------------
    PK = SEASON#{all|season_2|season_3}
    SK = ENRICHED_{TYPE}#LATEST
    Data = the artifact JSON, serialized as a string

`dashboard_api/app.py` returns `json.loads(item['Data'])` verbatim, so an item
published here is byte-equivalent to the static JSON the frontend reads today.
That equivalence is what makes VITE_USE_LAMBDA_API a safe one-line cutover.

SEASON FAN-OUT
--------------
PK=SEASON#all is the parity contract: the frontend never sends ?season=, so the
API defaults to 'all', and 'all' must reproduce the static files exactly.

Per-season keys are additive, and enable the multi-season goal (browse a finished
season while a new one is live):
  - TRADES     -> all + every season present in trades[].season (clean filter)
  - STANDINGS  -> all + the season its metadata.season year maps to
    PLAYOFF       (these are single-season snapshots, so the same bytes are
    DRAFTORDER     correct under both keys -- no recompute at all)
  - TEAMS      -> all only (current roster identity, not season-scoped)
    STATS         (aggregate bodies; see the design rule above)
    WAIVERS

Publishing STANDINGS/PLAYOFF/DRAFTORDER under their declared season is what
backfills the SEASON#season_2 items that previously 404'd.

USAGE
-----
    python3 stage13_publish_dynamodb.py --dry-run
    python3 stage13_publish_dynamodb.py --endpoint-url http://localhost:8000
    python3 stage13_publish_dynamodb.py --verify-only

Local development uses DynamoDB Local (no Docker required):
    java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -inMemory -port 8000
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import boto3

# Resolve paths relative to this file so the stage runs from any cwd. The other
# stages are invoked with cwd=pipeline/, but update_dashboard.py and CI differ.
PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parent
PUBLIC_DIR = REPO_ROOT / "dashboard" / "frontend" / "public"
SEASONS_YAML = PIPELINE_DIR / "config" / "seasons.yaml"

TABLE_NAME = os.environ.get("TABLE_NAME", "fantasy-dashboard-data")

# DynamoDB rejects any item over 400KB. waiver-wire-page.json is the only
# artifact in the same order of magnitude (295KB serialized compact), so this is
# a real guard rail rather than a theoretical one.
MAX_ITEM_BYTES = 400 * 1024
# Warn well before the hard failure so a growing artifact is caught in a normal
# run rather than on the day it crosses the limit.
WARN_ITEM_BYTES = 300 * 1024

# Fan-out mode per artifact. See SEASON FAN-OUT above.
#   "trades"   -- filter the flat trades list by season
#   "snapshot" -- single-season artifact; same bytes under 'all' + its own season
#   "all"      -- aggregate body; 'all' only
ARTIFACTS: List[Tuple[str, str, str]] = [
    ("ENRICHED_TRADES", "api-trades.json", "trades"),
    ("ENRICHED_TEAMS", "api-teams.json", "all"),
    ("ENRICHED_STATS", "api-stats-summary.json", "all"),
    ("ENRICHED_STANDINGS", "api-standings.json", "snapshot"),
    ("ENRICHED_PLAYOFF", "api-playoff-scenarios.json", "snapshot"),
    ("ENRICHED_DRAFTORDER", "api-draft-order.json", "snapshot"),
    ("ENRICHED_WAIVERS", "waiver-wire-page.json", "all"),
    # Added June 2026, five months after the Lambda's original seven routes, and
    # consumed by a raw fetch() that bypassed api-client.ts -- so it was invisible
    # to VITE_USE_LAMBDA_API and stayed static even in Lambda mode. Publishing it
    # here plus routing it through the client closes the last static fetch.
    ("ENRICHED_METRICS", "api-trade-metrics.json", "all"),
]


def log(msg: str) -> None:
    print(f"   {msg}", flush=True)


def utc_timestamp() -> str:
    """ISO-8601 UTC with a trailing Z, matching dashboard_api's wire format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_year_to_season() -> Dict[str, str]:
    """Map NFL year -> season key from seasons.yaml.

    Used to place single-season snapshots. The snapshots identify themselves by
    NFL year ("2025"), while the table is keyed by season slug ("season_2"), and
    seasons.yaml is the only source of truth that joins the two. Deriving this
    rather than hardcoding it is what keeps the 2026 rollover from silently
    filing new standings under the previous season.
    """
    import yaml  # local import: only this function needs it

    with open(SEASONS_YAML) as fh:
        cfg = yaml.safe_load(fh)

    mapping = {}
    for key, info in (cfg.get("seasons") or {}).items():
        year = info.get("year")
        if year is not None:
            mapping[str(year)] = key
    return mapping


def read_artifact(filename: str) -> Optional[Any]:
    path = PUBLIC_DIR / filename
    if not path.exists():
        log(f"WARNING: {filename} not found at {path} -- skipping")
        return None
    with open(path) as fh:
        return json.load(fh)


def declared_year(payload: Any) -> Optional[str]:
    """Extract the NFL year a snapshot artifact declares.

    Looks in metadata.season first (standings, playoffs) then at the top level
    (draft order uses a bare `season` key), since the three snapshot artifacts
    were written by different stages and never agreed on a location.
    """
    if not isinstance(payload, dict):
        return None
    md = payload.get("metadata")
    if isinstance(md, dict) and md.get("season") is not None:
        return str(md["season"])
    if payload.get("season") is not None:
        return str(payload["season"])
    return None


def split_trades(payload: Any) -> Dict[str, Any]:
    """Split the trades artifact into per-season payloads plus 'all'.

    Only counts that are pure functions of the filtered list are recomputed.
    Valuations, winners, and margins are copied untouched -- they were computed
    by stage 3/4 against historical value snapshots and must never be recomputed
    here (that duplication is precisely what this stage exists to remove).
    """
    result = {"all": payload}

    inner = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(inner, dict) or not isinstance(inner.get("trades"), list):
        log("WARNING: trades artifact is not {data:{trades:[...]}} -- 'all' only")
        return result

    trades = inner["trades"]
    seasons = sorted({t.get("season") for t in trades if t.get("season")})

    for season in seasons:
        subset = [t for t in trades if t.get("season") == season]
        dates = sorted(t["tradeDate"] for t in subset if t.get("tradeDate"))

        md = dict(inner.get("metadata") or {})
        md["totalTrades"] = len(subset)
        md["seasonsIncluded"] = [season]
        md["tradesBySeason"] = {season: len(subset)}
        if dates:
            md["dateRange"] = {"earliest": dates[0], "latest": dates[-1]}
        # Record the narrowing so a consumer can tell a season view from the
        # combined view without diffing trade counts.
        md["seasonFilter"] = season

        result[season] = {
            **{k: v for k, v in payload.items() if k != "data"},
            "data": {**inner, "trades": subset, "metadata": md},
        }

    return result


def build_items(year_to_season: Dict[str, str]) -> List[Dict[str, str]]:
    """Build every DynamoDB item to publish. No AWS calls, no mutation."""
    items: List[Dict[str, str]] = []
    published_at = utc_timestamp()

    def add(season: str, sk: str, payload: Any, note: str) -> None:
        # separators: compact serialization. json.loads on the other side is
        # whitespace-insensitive, so this only buys headroom against the 400KB cap.
        data = json.dumps(payload, separators=(",", ":"), default=str)
        size = len(data.encode("utf-8"))
        if size > MAX_ITEM_BYTES:
            raise SystemExit(
                f"ERROR: SEASON#{season} / {sk}#LATEST is {size/1024:.1f}KB, over "
                f"DynamoDB's {MAX_ITEM_BYTES/1024:.0f}KB item limit. Split the "
                f"artifact upstream or store it in S3 with a pointer item."
            )
        if size > WARN_ITEM_BYTES:
            log(f"WARNING: SEASON#{season}/{sk} is {size/1024:.1f}KB, approaching the 400KB cap")

        items.append({
            "PK": f"SEASON#{season}",
            "SK": f"{sk}#LATEST",
            "Data": data,
            "PublishedAt": published_at,
            "Source": "pipeline/stage13_publish_dynamodb.py",
        })
        log(f"SEASON#{season:<9} {sk+'#LATEST':<26} {size/1024:7.1f}KB  {note}")

    for sk, filename, mode in ARTIFACTS:
        payload = read_artifact(filename)
        if payload is None:
            continue

        if mode == "trades":
            for season, season_payload in split_trades(payload).items():
                count = len(season_payload["data"]["trades"]) if season != "all" else \
                    len(payload["data"]["trades"])
                add(season, sk, season_payload, f"{filename} ({count} trades)")

        elif mode == "snapshot":
            add("all", sk, payload, filename)
            year = declared_year(payload)
            season = year_to_season.get(year) if year else None
            if season:
                # Identical bytes under a second key -- a snapshot belongs to
                # exactly one season, so no filtering is possible or needed.
                add(season, sk, payload, f"{filename} (year {year})")
            else:
                log(f"WARNING: {filename} declares season={year!r}, which is not in "
                    f"seasons.yaml -- published under 'all' only")

        else:  # "all"
            add("all", sk, payload, filename)

    return items


def get_table(endpoint_url: Optional[str]):
    kwargs = {}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
        # DynamoDB Local partitions stored data by BOTH access key and region, so
        # a table created under one pair is invisible to a client using another --
        # it surfaces as a bare "Cannot do operations on a non-existent table"
        # even though list-tables just showed it. Pin both explicitly here.
        #
        # This matters because a developer shell may export AWS_PROFILE and
        # AWS_REGION (AWS_REGION outranks AWS_DEFAULT_REGION), which silently
        # sends the CLI and this script to two different local partitions.
        # Run local commands with `env -u AWS_PROFILE -u AWS_REGION`.
        kwargs.setdefault("region_name", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        kwargs.setdefault("aws_access_key_id", os.environ.get("AWS_ACCESS_KEY_ID", "local"))
        kwargs.setdefault("aws_secret_access_key", os.environ.get("AWS_SECRET_ACCESS_KEY", "local"))
    return boto3.resource("dynamodb", **kwargs).Table(TABLE_NAME)


def verify(table, items: List[Dict[str, str]]) -> int:
    """Read back every published key and confirm Data round-trips to equal JSON.

    Compares parsed objects rather than raw strings: the assertion that matters
    is that the API hands the frontend the same *data*, and key order is not
    part of that contract.
    """
    failures = 0
    for item in items:
        got = table.get_item(Key={"PK": item["PK"], "SK": item["SK"]}).get("Item")
        if not got:
            log(f"FAIL {item['PK']} / {item['SK']}: not found after write")
            failures += 1
            continue
        if json.loads(got["Data"]) != json.loads(item["Data"]):
            log(f"FAIL {item['PK']} / {item['SK']}: Data does not match what was written")
            failures += 1
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="build and size every item, write nothing")
    ap.add_argument("--endpoint-url",
                    help="DynamoDB endpoint (e.g. http://localhost:8000 for DynamoDB Local)")
    ap.add_argument("--verify-only", action="store_true",
                    help="verify already-published items without writing")
    args = ap.parse_args()

    print("=" * 78)
    print("Stage 13: Publish Dashboard JSON to DynamoDB")
    print("=" * 78)
    log(f"source    : {PUBLIC_DIR}")
    log(f"table     : {TABLE_NAME}")
    log(f"endpoint  : {args.endpoint_url or '(default AWS endpoint)'}")
    print()

    year_to_season = load_year_to_season()
    log(f"year -> season: {year_to_season}")
    print()

    items = build_items(year_to_season)
    print()
    total_kb = sum(len(i["Data"].encode()) for i in items) / 1024
    log(f"{len(items)} items, {total_kb:.1f}KB total")

    if args.dry_run:
        print()
        log("DRY RUN -- nothing written")
        return 0

    table = get_table(args.endpoint_url)

    if not args.verify_only:
        print()
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
        log(f"wrote {len(items)} items")

    print()
    failures = verify(table, items)
    if failures:
        log(f"VERIFY FAILED: {failures} of {len(items)} items")
        return 1
    log(f"VERIFY OK: {len(items)}/{len(items)} items round-trip correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
