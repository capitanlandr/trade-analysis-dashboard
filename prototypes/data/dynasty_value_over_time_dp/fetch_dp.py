#!/usr/bin/env python3
"""
Fetch DynastyProcess (DP) values.csv WEEKLY snapshots from git history and build
compact history CSVs for the dynasty-value-over-time DP reconstruction.

DP has no daily feed, but the git commit history of files/values.csv yields a real
WEEKLY series. We:
  1. page the GitHub commits API for the files/values.csv path,
  2. extract each commit SHA + author date,
  3. keep the LATEST commit per ISO week within 2024-08-14..today,
  4. fetch values.csv at each SHA via raw.githubusercontent.com (cached to raw_dp/),
  5. crosswalk fp_id -> fantasypros_id -> sleeper_id (db_playerids.csv),
  6. emit:
       dp_players_history.csv : sleeper_id, date, value_2qb   (per weekly snapshot)
       dp_picks_history.csv   : year, round, tier, date, value (aggregated DP slots)
       _dp_fetch_meta.json    : snapshot dates, coverage, cadence stats

DP labels picks per exact slot ("2024 Pick 1.01"). We aggregate to the KTC tier
scheme: Early=slots 1-4, Mid=5-8, Late=9-12 (per round), averaging the DP slot
values in each tier. value is value_2qb (league is Superflex/2QB).
"""
import csv, json, os, sys, time, urllib.request, urllib.error
from collections import defaultdict
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw_dp")
os.makedirs(RAW, exist_ok=True)

REPO = "dynastyprocess/data"
VALUES_PATH = "files/values.csv"
IDS_PATH = "files/db_playerids.csv"
WINDOW_START = date(2024, 8, 14)
WINDOW_END = date.today()

UA = {"User-Agent": "dynasty-dp-reconstruct/1.0"}


def http_get(url, binary=False, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < retries - 1:
                wait = 30 * (attempt + 1)
                print(f"  rate/limit {e.code}, sleeping {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise


def list_commits():
    """All commits touching VALUES_PATH, newest-first, paginated."""
    commits = []
    page = 1
    while True:
        url = (f"https://api.github.com/repos/{REPO}/commits"
               f"?path={VALUES_PATH}&per_page=100&page={page}&since=2024-08-01T00:00:00Z")
        chunk = json.loads(http_get(url))
        if not chunk:
            break
        for c in chunk:
            sha = c["sha"]
            ds = c["commit"]["author"]["date"]  # ISO 8601 Z
            d = datetime.fromisoformat(ds.replace("Z", "+00:00")).astimezone(timezone.utc).date()
            commits.append((d, sha))
        if len(chunk) < 100:
            break
        page += 1
    return commits


def weekly_pick(commits):
    """Keep the LATEST commit per ISO (year, week) within the window."""
    in_win = [(d, sha) for d, sha in commits if WINDOW_START <= d <= WINDOW_END]
    by_week = {}
    for d, sha in in_win:
        iso = d.isocalendar()
        key = (iso[0], iso[1])
        # commits come newest-first, but be explicit: keep max date per week
        if key not in by_week or d > by_week[key][0]:
            by_week[key] = (d, sha)
    snaps = sorted(by_week.values())  # ascending by date
    return snaps


def load_crosswalk():
    """fantasypros_id -> sleeper_id from current db_playerids.csv."""
    txt = http_get(f"https://raw.githubusercontent.com/{REPO}/master/{IDS_PATH}")
    fp2sleeper = {}
    rdr = csv.DictReader(txt.splitlines())
    for row in rdr:
        fp = (row.get("fantasypros_id") or "").strip()
        sl = (row.get("sleeper_id") or "").strip()
        if fp and sl:
            fp2sleeper[fp] = sl
    return fp2sleeper


def fetch_snapshot(sha):
    cache = os.path.join(RAW, f"values_{sha[:12]}.csv")
    if os.path.exists(cache) and os.path.getsize(cache) > 0:
        with open(cache, encoding="utf-8") as f:
            return f.read()
    txt = http_get(f"https://raw.githubusercontent.com/{REPO}/{sha}/{VALUES_PATH}")
    with open(cache, "w", encoding="utf-8") as f:
        f.write(txt)
    return txt


TIER_OF_SLOT = lambda s: "Early" if s <= 4 else ("Mid" if s <= 8 else "Late")
_ORD2RND = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4}
_TIERWORD = {"early": "Early", "mid": "Mid", "late": "Late"}


def parse_pick_row(player):
    """DP labels picks two ways:
      exact-slot : '2026 Pick 1.07'   -> (year, round, tier via slot)
      tier-named : '2027 Early 1st'   -> (year, round, tier directly)
    Return (year:int, round:int, tier:str) or None if not parseable."""
    parts = player.strip().split()
    if len(parts) < 2 or not parts[0].isdigit():
        return None
    year = int(parts[0])
    # exact-slot form: a token like "1.07"
    for tok in parts:
        if "." in tok:
            a, b = tok.split(".", 1)
            if a.isdigit() and b.isdigit():
                return (year, int(a), TIER_OF_SLOT(int(b)))
    # tier-named form: "<tierword> <ordinal>"
    low = [p.lower() for p in parts]
    tier = rnd = None
    for w in low:
        if w in _TIERWORD:
            tier = _TIERWORD[w]
        if w in _ORD2RND:
            rnd = _ORD2RND[w]
    if tier and rnd:
        return (year, rnd, tier)
    return None


def main():
    print("listing commits for", VALUES_PATH, flush=True)
    commits = list_commits()
    print(f"  {len(commits)} commits touching {VALUES_PATH} since 2024-08", flush=True)
    snaps = weekly_pick(commits)
    print(f"  {len(snaps)} weekly snapshots in window "
          f"{WINDOW_START}..{WINDOW_END}", flush=True)
    if not snaps:
        print("NO SNAPSHOTS - abort", flush=True)
        sys.exit(1)

    fp2sleeper = load_crosswalk()
    print(f"  crosswalk: {len(fp2sleeper)} fp->sleeper entries", flush=True)

    players_rows = []      # sleeper_id, date, value_2qb
    pick_slot_vals = defaultdict(dict)   # (year, round, tier, date) -> [values]
    pick_tmp = defaultdict(lambda: defaultdict(list))  # date -> (year,round,tier)->[vals]

    fp_seen = 0
    fp_mapped = 0
    dates_done = []
    for i, (d, sha) in enumerate(snaps):
        dstr = d.isoformat()
        txt = fetch_snapshot(sha)
        rdr = csv.DictReader(txt.splitlines())
        cols = rdr.fieldnames or []
        # column resolve (schema stable, but be defensive)
        vcol = "value_2qb" if "value_2qb" in cols else ("value_sf" if "value_sf" in cols else None)
        fpcol = "fp_id" if "fp_id" in cols else None
        pcol = "player" if "player" in cols else ("name" if "name" in cols else None)
        poscol = "pos" if "pos" in cols else ("position" if "position" in cols else None)
        if vcol is None or pcol is None:
            print(f"  [{dstr}] MISSING value/player cols {cols[:6]} - skip", flush=True)
            continue
        n_players = n_picks = 0
        for row in rdr:
            val = (row.get(vcol) or "").strip()
            if not val:
                continue
            try:
                v = int(round(float(val)))
            except ValueError:
                continue
            pos = (row.get(poscol) or "").strip().upper() if poscol else ""
            player = (row.get(pcol) or "").strip()
            fp = (row.get(fpcol) or "").strip() if fpcol else ""
            parsed_pick = parse_pick_row(player)
            is_pick = (pos == "PICK") or parsed_pick is not None
            if is_pick:
                if parsed_pick is None:
                    continue
                year, rnd, tier = parsed_pick
                pick_tmp[dstr][(year, rnd, tier)].append(v)
                n_picks += 1
            else:
                if not fp:
                    continue
                fp_seen += 1
                sl = fp2sleeper.get(fp)
                if not sl:
                    continue
                fp_mapped += 1
                players_rows.append((sl, dstr, v))
                n_players += 1
        dates_done.append(dstr)
        print(f"  [{i+1}/{len(snaps)}] {dstr} sha={sha[:8]} "
              f"players={n_players} picks={n_picks}", flush=True)

    # aggregate picks: mean of DP slot values in each (year, round, tier) on each date
    picks_rows = []
    for dstr, byk in pick_tmp.items():
        for (year, rnd, tier), vals in byk.items():
            if vals:
                picks_rows.append((year, rnd, tier, dstr, int(round(sum(vals) / len(vals)))))

    # write players history
    pout = os.path.join(HERE, "dp_players_history.csv")
    with open(pout, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sleeper_id", "date", "value_2qb"])
        w.writerows(sorted(players_rows, key=lambda r: (r[1], r[0])))

    # write picks history
    pkout = os.path.join(HERE, "dp_picks_history.csv")
    with open(pkout, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "round", "tier", "date", "value"])
        w.writerows(sorted(picks_rows, key=lambda r: (r[3], r[0], r[1], r[2])))

    # cadence stats
    dseq = sorted(set(dates_done))
    gaps = []
    for a, b in zip(dseq, dseq[1:]):
        gaps.append((date.fromisoformat(b) - date.fromisoformat(a)).days)
    gaps_sorted = sorted(gaps)
    median_gap = gaps_sorted[len(gaps_sorted) // 2] if gaps_sorted else None
    meta = {
        "n_snapshots": len(dseq),
        "date_range": [dseq[0], dseq[-1]] if dseq else None,
        "median_gap_days": median_gap,
        "max_gap_days": max(gaps) if gaps else None,
        "gaps": gaps,
        "snapshot_dates": dseq,
        "fp_seen": fp_seen,
        "fp_mapped": fp_mapped,
        "fp_map_coverage_pct": round(100 * fp_mapped / max(1, fp_seen), 2),
        "n_player_rows": len(players_rows),
        "n_pick_rows": len(picks_rows),
        "crosswalk_size": len(fp2sleeper),
    }
    json.dump(meta, open(os.path.join(HERE, "_dp_fetch_meta.json"), "w"), indent=2)
    print(f"\nwrote {pout} ({len(players_rows)} rows)")
    print(f"wrote {pkout} ({len(picks_rows)} rows)")
    print(f"snapshots={len(dseq)} range={meta['date_range']} "
          f"median_gap={median_gap}d max_gap={meta['max_gap_days']}d "
          f"fp_map_cov={meta['fp_map_coverage_pct']}%")


if __name__ == "__main__":
    main()
