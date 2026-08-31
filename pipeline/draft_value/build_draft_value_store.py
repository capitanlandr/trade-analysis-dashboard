#!/usr/bin/env python3
"""
Build / refresh the dedicated draft-value store: ONLY the 96 drafted players.

WHY A SEPARATE STORE
--------------------
ktc_history.csv is 51 MB covering 402 scraped players, most irrelevant here, and
it is not something to commit and grow daily. This store holds only the 48+48
players actually drafted in 2025 and 2026, so it is small enough to live in git
and append to forever.

WHY THE ARCHIVE MATTERS (not just size)
---------------------------------------
KTC RETIRES pick assets after a draft. Every 2025 pick slug now 404s, which is
exactly why the 2025 dataset had to fall back to prospect values. When the 2027
draft happens the 2026 tier pages will vanish the same way. Rebuilding purely
from live would silently lose that history. Committing this store means we own it.

SCHEMA (two files, split so the daily file stays tiny)
-----------------------------------------------------
draft_value_picks.csv   96 rows, static. Identity + the two FROZEN anchors:
    baseline  = the pre-draft value the analysis measures against
                2026 -> pick-tier value the day before the draft
                2025 -> the rookie's own prospect value the day before
    anchor    = value the day AFTER the draft, the permanent post-pick start

draft_value_daily.csv   long + append-only: season,pick_label,date,value
    One row per player per day from the day after the draft onward.
    ~91 rows/day (~4 KB/day, ~1.4 MB/year).

APPEND SAFETY
-------------
Verified 2026-08-31: KTC history is IMMUTABLE. 2,162 overlapping dates compared
live vs stored, zero value mismatches. So merging is add-new-dates-only with no
conflict resolution, and a re-run can never rewrite a past number.
"""

import argparse
import csv
import gzip
import importlib.util
import json
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/local/home/lndahayo/projects/trade-analysis-dashboard")
KTC = REPO / "prototypes/data/ktc_history"
OUT = REPO / "pipeline/draft_value"
PICKS_CSV = OUT / "draft_value_picks.csv"
DAILY_CSV = OUT / "draft_value_daily.csv"
STATUS_JSON = OUT / "refresh_status.json"

spec = importlib.util.spec_from_file_location("fk", KTC / "fetch_ktc_history.py")
fk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fk)

FMT = "SF"  # superflex league
SEASONS = {
    2026: {"draft_id": "1312166810505715712", "league": "1312166810505719808",
           "draft_day": "2026-04-27", "baseline_date": "2026-04-26",
           "anchor_date": "2026-04-28", "baseline_kind": "pick_tier",
           "fa_baseline_date": "2026-03-01"},
    2025: {"draft_id": "1180814327660371969", "league": "1180814327660371968",
           "draft_day": "2025-04-30", "baseline_date": "2025-04-29",
           "anchor_date": "2025-05-01", "baseline_kind": "prospect",
           "fa_baseline_date": "2025-03-01"},
}
TIER_SLUGS = {  # 2026 pick tiers, for the pick_tier baseline
    "Early 1st": "2026-early-1st-1527", "Mid 1st": "2026-mid-1st-1528", "Late 1st": "2026-late-1st-1529",
    "Early 2nd": "2026-early-2nd-1530", "Mid 2nd": "2026-mid-2nd-1531", "Late 2nd": "2026-late-2nd-1532",
    "Early 3rd": "2026-early-3rd-1533", "Mid 3rd": "2026-mid-3rd-1534", "Late 3rd": "2026-late-3rd-1535",
    "Early 4th": "2026-early-4th-1536", "Mid 4th": "2026-mid-4th-1537", "Late 4th": "2026-late-4th-1538",
}


def tier_of(slot):
    return "Early" if slot <= 4 else ("Mid" if slot <= 8 else "Late")


def ordinal(rd):
    return {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}[rd]


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def fetch_series(slug, cache_dir: Path, use_cache: bool):
    """Full SF series for a slug. Returns (dict date->value, error_or_None)."""
    cache = cache_dir / f"{slug}.html.gz"
    if use_cache and cache.exists() and cache.stat().st_size > 1000:
        with gzip.open(cache, "rt", encoding="utf-8", errors="replace") as f:
            html = f.read()
    else:
        req = urllib.request.Request(
            f"https://keeptradecut.com/dynasty-rankings/players/{slug}",
            headers={"User-Agent": fk.UA})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                html = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 403):
                time.sleep(60)
                try:
                    with urllib.request.urlopen(req, timeout=90) as r:
                        html = r.read().decode("utf-8", "replace")
                except Exception as e2:  # noqa: BLE001
                    return {}, f"HTTP {e.code} then {type(e2).__name__}"
            else:
                return {}, f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            return {}, type(e).__name__
        cache_dir.mkdir(parents=True, exist_ok=True)
        with gzip.open(cache, "wt", encoding="utf-8") as f:
            f.write(html)
        time.sleep(random.uniform(1.5, 3.0))
    try:
        return dict(fk.parse_series(html).get(FMT) or []), None
    except Exception as e:  # noqa: BLE001
        return {}, f"parse:{type(e).__name__}"


def resolve_slugs():
    slug_by_name, slug_by_sid = {}, {}
    with (KTC / "player_map.csv").open() as f:
        for r in csv.DictReader(f):
            if r.get("ktc_slug"):
                slug_by_name[r["my_name"].strip()] = r["ktc_slug"]
                if r.get("sleeper_id"):
                    slug_by_sid[r["sleeper_id"]] = r["ktc_slug"]
    with (KTC / "ktc_history.csv").open() as f:
        for r in csv.DictReader(f):
            if r.get("ktc_slug"):
                slug_by_name.setdefault(r["player_name"].strip(), r["ktc_slug"])
                if r.get("sleeper_id"):
                    slug_by_sid.setdefault(r["sleeper_id"], r["ktc_slug"])
    return slug_by_name, slug_by_sid


def load_existing_daily():
    seen, rows = set(), []
    if DAILY_CSV.exists():
        with DAILY_CSV.open() as f:
            for r in csv.DictReader(f):
                key = (r["season"], r["pick_label"], r["date"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append(r)
    return seen, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--use-cache", action="store_true",
                    help="reuse gzip cache (dev only; a real refresh must fetch live)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    cache_dir = OUT / "_raw"
    by_name, by_sid = resolve_slugs()
    errors, picks, unresolved = [], [], []

    # 2026 pick-tier baselines
    tier_series = {}
    for tier, slug in TIER_SLUGS.items():
        s, err = fetch_series(slug, cache_dir, args.use_cache)
        if err:
            errors.append(f"tier {tier}: {err}")
        tier_series[tier] = s

    def val_on(series, date):
        c = [d for d in series if d <= date]
        return series[max(c)] if c else None

    seen, daily_rows = load_existing_daily()
    added = 0

    for season, cfg in SEASONS.items():
        meta = get_json(f"https://api.sleeper.app/v1/draft/{cfg['draft_id']}/picks")
        rosters = get_json(f"https://api.sleeper.app/v1/league/{cfg['league']}/rosters")
        users = get_json(f"https://api.sleeper.app/v1/league/{cfg['league']}/users")
        team_of = {r["roster_id"]: next(
            ((u.get("metadata", {}).get("team_name") or u.get("display_name") or "?").strip()
             for u in users if u["user_id"] == r.get("owner_id")), f"roster {r['roster_id']}")
            for r in rosters}

        for p in meta:
            md = p.get("metadata") or {}
            name = f"{md.get('first_name','')} {md.get('last_name','')}".strip()
            sid = str(p.get("player_id"))
            rd, slot = p["round"], p["draft_slot"]
            label = f"{season} Pick {rd}.{slot:02d}"
            slug = by_sid.get(sid) or by_name.get(name)
            row = {
                "season": season, "pick_label": label, "round": rd, "slot": slot,
                "overall": p["pick_no"], "owner_team": team_of.get(p.get("roster_id")),
                "player_name": name, "sleeper_id": sid, "ktc_slug": slug or "",
                "pos": md.get("position") or "", "nfl_team": md.get("team") or "",
                "baseline_kind": cfg["baseline_kind"],
                "fa_baseline_date": cfg["fa_baseline_date"], "fa_baseline_value": "",
                "baseline_date": cfg["baseline_date"], "baseline_value": "",
                "anchor_date": cfg["anchor_date"], "anchor_value": "", "status": "",
            }
            if not slug:
                row["status"] = "no_ktc_slug"
                unresolved.append(f"{label} {name}")
                picks.append(row)
                continue

            series, err = fetch_series(slug, cache_dir, args.use_cache)
            if err:
                row["status"] = f"fetch_failed:{err}"
                errors.append(f"{label} {name}: {err}")
                picks.append(row)
                continue

            # baseline: 2026 uses the pick TIER value, 2025 the player's prospect value
            if cfg["baseline_kind"] == "pick_tier":
                ts = tier_series.get(f"{tier_of(slot)} {ordinal(rd)}", {})
                b = val_on(ts, cfg["baseline_date"])
                fab = val_on(ts, cfg["fa_baseline_date"])
            else:
                b = val_on(series, cfg["baseline_date"])
                fab = val_on(series, cfg["fa_baseline_date"])
            row["fa_baseline_value"] = fab if fab is not None else ""
            row["baseline_value"] = b if b is not None else ""
            a = val_on(series, cfg["anchor_date"])
            row["anchor_value"] = a if a is not None else ""
            row["status"] = "ok" if (b is not None and a is not None) else "partial"
            picks.append(row)

            for d, v in sorted(series.items()):
                if d < cfg["anchor_date"]:
                    continue  # daily series starts the day after the draft
                key = (str(season), label, d)
                if key in seen:
                    continue
                seen.add(key)
                daily_rows.append({"season": str(season), "pick_label": label,
                                   "date": d, "value": v})
                added += 1

    with PICKS_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(picks[0].keys()))
        w.writeheader()
        w.writerows(sorted(picks, key=lambda r: (r["season"], r["overall"])))
    daily_rows.sort(key=lambda r: (r["season"], r["pick_label"], r["date"]))
    with DAILY_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["season", "pick_label", "date", "value"])
        w.writeheader()
        w.writerows(daily_rows)

    ok = sum(1 for p in picks if p["status"] == "ok")
    latest = max((r["date"] for r in daily_rows), default=None)
    status = {
        "last_attempt_utc": datetime.now(timezone.utc).isoformat(),
        "last_success_date": latest,
        "picks_total": len(picks), "picks_ok": ok,
        "rows_added_this_run": added, "rows_total": len(daily_rows),
        "unresolved_players": unresolved,
        "errors": errors,
        "degraded": bool(errors) or ok < len(picks) - len(unresolved),
    }
    STATUS_JSON.write_text(json.dumps(status, indent=2))

    print(f"picks: {len(picks)}  ok: {ok}  unresolved: {len(unresolved)}  errors: {len(errors)}")
    print(f"daily rows: {len(daily_rows)} (+{added} this run), latest date {latest}")
    if unresolved:
        print(f"  unresolved: {unresolved}")
    if errors:
        print(f"  errors: {errors[:6]}")
    print(f"wrote {PICKS_CSV.name}, {DAILY_CSV.name}, {STATUS_JSON.name} in {OUT}")


if __name__ == "__main__":
    main()
