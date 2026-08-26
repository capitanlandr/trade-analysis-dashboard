#!/usr/bin/env python3
"""
Dynasty Value Over Time — DYNASTYPROCESS (DP) edition.

Identical roster+pick day-by-day replay as the KTC reconstruction
(prototypes/data/dynasty_value_over_time/reconstruct.py), with the VALUE JOIN
swapped from KTC to the DP WEEKLY series produced by fetch_dp.py:

  players : dp_players_history.csv  (sleeper_id, date, value_2qb)   value_2qb = Superflex/2QB
  picks   : dp_picks_history.csv    (year, round, tier, date, value)

DP's true cadence is WEEKLY (median 7-day step, one ~63-day offseason gap).
We forward-fill each player's / pick-tier's latest weekly value across the
<=7-day step to render continuous lines; larger gaps are left as line breaks
(honest to the weekly cadence, not fabricated daily points).

value_source provenance:
  players : dp_actual | forward_fill | no_dp(=0)
  picks   : pick_tier (DP tier value, actual or <=7d fill) | dp_unavailable(=0)

Roster/pick HOLDINGS logic is copied verbatim from the KTC reconstruction so
holdings reconcile exactly to the live rosters (validated 0 missing / 0 extra).
"""
import csv, json, os, sys, bisect
from collections import defaultdict
from datetime import date, timedelta, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RAW = os.path.join(ROOT, "pipeline", "season_1", "season1_sleeper_raw.json")
IDENT = os.path.join(ROOT, "pipeline", "team_identity_mapping.csv")
DP_PLAYERS = os.path.join(HERE, "dp_players_history.csv")
DP_PICKS = os.path.join(HERE, "dp_picks_history.csv")

FFILL_DAYS = 7
ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
TIER_OF_SLOT = lambda s: "Early" if s <= 4 else ("Mid" if s <= 8 else "Late")

raw = json.load(open(RAW))
L = {s: raw["leagues"][s] for s in ("season_1", "season_2", "season_3")}


def dmy(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def startup_draft(b):  return max(b["drafts"], key=lambda d: len(d["picks"]))
def rookie_draft(b):   return b["drafts"][0]


SU = startup_draft(L["season_1"])
RD25, RD26 = rookie_draft(L["season_2"]), rookie_draft(L["season_3"])
START = dmy(SU["detail"]["start_time"])
D2025 = dmy(RD25["detail"]["start_time"])
D2026 = dmy(RD26["detail"]["start_time"])
S2R_2025 = {int(k): v for k, v in RD25["detail"]["slot_to_roster_id"].items()}
S2R_2026 = {int(k): v for k, v in RD26["detail"]["slot_to_roster_id"].items()}
R2S_2025 = {v: k for k, v in S2R_2025.items()}
R2S_2026 = {v: k for k, v in S2R_2026.items()}


def league_rosters(sn):
    return {r["roster_id"]: set(str(x) for x in (r.get("players") or []))
            for r in L[sn]["rosters"]}


# ---- derive PI: auction-draft roster_id -> league roster_id (max player overlap)
def derive_permutation():
    st = defaultdict(set)
    for p in SU["picks"]:
        st[p["roster_id"]].add(str(p["player_id"]))
    fin = league_rosters("season_1")
    cand = sorted(((len(st[r] & fin[s]), r, s) for r in range(1, 13) for s in range(1, 13)),
                  reverse=True)
    pi, used_r, used_s = {}, set(), set()
    for ov, r, s in cand:
        if r in used_r or s in used_s:
            continue
        pi[r] = s; used_r.add(r); used_s.add(s)
    assert len(set(pi.values())) == 12, "PI is not a bijection"
    return pi


PI = derive_permutation()

# ---------------------------------------------------------------- DP players
pval = defaultdict(dict)
with open(DP_PLAYERS) as f:
    for row in csv.DictReader(f):
        pval[row["sleeper_id"]][row["date"]] = int(row["value_2qb"])
pdates = {pid: sorted(d) for pid, d in pval.items()}


def raw_player_value(pid, dstr):
    """(value, source) source in {dp_actual, forward_fill, no_dp}"""
    series = pval.get(str(pid))
    if not series:
        return 0, "no_dp"
    v = series.get(dstr)
    if v is not None:
        return v, "dp_actual"
    ds = pdates[str(pid)]
    i = bisect.bisect_right(ds, dstr) - 1
    if i >= 0:
        gap = (date.fromisoformat(dstr) - date.fromisoformat(ds[i])).days
        if 0 <= gap <= FFILL_DAYS:
            return series[ds[i]], "forward_fill"
    return 0, "no_dp"


# ---------------------------------------------------------------- DP picks
pkval = defaultdict(dict)   # (year, tier, round) -> {date: value}
with open(DP_PICKS) as f:
    for row in csv.DictReader(f):
        key = (row["year"], row["tier"], int(row["round"]))
        pkval[key][row["date"]] = int(row["value"])
pkdates = {k: sorted(v) for k, v in pkval.items()}


def pick_tier_value(year, tier, rnd, dstr):
    key = (str(year), tier, rnd)
    series = pkval.get(key)
    if not series:
        return None
    v = series.get(dstr)
    if v is not None:
        return v
    ds = pkdates[key]
    i = bisect.bisect_right(ds, dstr) - 1
    if i >= 0:
        gap = (date.fromisoformat(dstr) - date.fromisoformat(ds[i])).days
        if 0 <= gap <= FFILL_DAYS:
            return series[ds[i]]
    return None


def pick_value(year, rnd, origin, dstr):
    """(value, source, tier) source in {pick_tier, dp_unavailable}"""
    year = int(year)
    slot = R2S_2025[origin] if year == 2025 else R2S_2026[origin]
    tier = TIER_OF_SLOT(slot)
    v = pick_tier_value(year, tier, rnd, dstr)
    if v is not None:
        return v, "pick_tier", tier
    return 0, "dp_unavailable", tier


# ---------------------------------------------------------------- holdings events
def season_txn_events(sn):
    ev = []
    for wk, txns in L[sn]["transactions"].items():
        for t in txns:
            if t.get("status") in (None, "complete"):
                ev.append((t.get("status_updated") or t["created"], t))
    return ev


def rookie_events(sn):
    rd = rookie_draft(L[sn]); dms = rd["detail"]["start_time"]
    return [(dms + p["pick_no"], (p["roster_id"], str(p["player_id"]))) for p in rd["picks"]]


RESET, TXN, ROOK = 0, 1, 2
events = []
s2_open_ms = min(ts for ts, _ in season_txn_events("season_2"))
s3_open_ms = min(ts for ts, _ in season_txn_events("season_3"))

su_open = defaultdict(set)
for p in SU["picks"]:
    su_open[PI[p["roster_id"]]].add(str(p["player_id"]))
events.append((SU["detail"]["start_time"], -1, RESET, dict(su_open)))
events.append((s2_open_ms, -1, RESET, league_rosters("season_1")))
events.append((s3_open_ms, -1, RESET, league_rosters("season_2")))
for sn in ("season_1", "season_2", "season_3"):
    for ts, t in season_txn_events(sn):
        events.append((ts, 1, TXN, t))
for sn in ("season_2", "season_3"):
    for ts, payload in rookie_events(sn):
        events.append((ts, 2, ROOK, payload))
events.sort(key=lambda e: (e[0], e[1]))

# ---------------------------------------------------------------- pick ownership
pick_trade_events = []
for sn in ("season_1", "season_2", "season_3"):
    for wk, txns in L[sn]["transactions"].items():
        for t in txns:
            if t.get("type") == "trade" and t.get("draft_picks") and t.get("status") in (None, "complete"):
                pick_trade_events.append((t.get("status_updated") or t["created"], t))
pick_trade_events.sort(key=lambda e: e[0])

CLASSES = (2025, 2026, 2027, 2028, 2029)


def base_pick_owner():
    return {(y, r, o): o for y in CLASSES for r in (1, 2, 3, 4) for o in range(1, 13)}


def pick_owner_asof(d):
    state = base_pick_owner()
    for ts, t in pick_trade_events:
        if dmy(ts) > d:
            break
        for dp in t.get("draft_picks", []):
            key = (int(dp["season"]), dp["round"], dp["roster_id"])
            if key in state:
                state[key] = dp["owner_id"]
    return state


def class_active(year, d):
    return {
        2025: START <= d < D2025,
        2026: START <= d < D2026,
        2027: d >= START,
        2028: d >= D2025,
        2029: d >= D2026,
    }[year]


# ---------------------------------------------------------------- team names
TEAM = {}
with open(IDENT) as f:
    for row in csv.DictReader(f):
        TEAM[int(row["roster_id"])] = row["current_team_name"].strip()

# DP series end = last DP snapshot date across players+picks
END = date.fromisoformat(max(
    max(v[-1] for v in pdates.values()),
    max(v[-1] for v in pkdates.values()),
))


# ---------------------------------------------------------------- validate holdings
def validate():
    holdings = defaultdict(set)
    for ts, order, kind, payload in events:
        if kind == RESET:
            holdings = {rid: set(s) for rid, s in payload.items()}
        elif kind == TXN:
            for pid, rid in (payload.get("drops") or {}).items():
                holdings.setdefault(rid, set()).discard(str(pid))
            for pid, rid in (payload.get("adds") or {}).items():
                holdings.setdefault(rid, set()).add(str(pid))
        else:
            rid, pid = payload; holdings.setdefault(rid, set()).add(pid)
    live = league_rosters("season_3")
    tm = te = 0
    for rid in range(1, 13):
        tm += len(live[rid] - holdings.get(rid, set()))
        te += len(holdings.get(rid, set()) - live[rid])
    print(f"START={START} D2025={D2025} D2026={D2026} END(DP)={END}")
    print(f"holdings vs live S3-current: missing={tm} extra={te} -> {'PASS' if tm==te==0 else 'CHECK'}")


# ---------------------------------------------------------------- build daily
def build():
    rows = []
    cov = {"player_days": 0, "player_days_valued": 0, "no_dp_player_slots": 0,
           "pick_days": 0, "pick_days_unavailable": 0}
    holdings = defaultdict(set)
    ei = 0
    d = START
    while d <= END:
        dstr = d.isoformat()
        while ei < len(events) and dmy(events[ei][0]) <= d:
            _, _, kind, payload = events[ei]; ei += 1
            if kind == RESET:
                holdings = {rid: set(s) for rid, s in payload.items()}
            elif kind == TXN:
                for pid, rid in (payload.get("drops") or {}).items():
                    holdings.setdefault(rid, set()).discard(str(pid))
                for pid, rid in (payload.get("adds") or {}).items():
                    holdings.setdefault(rid, set()).add(str(pid))
            else:
                rid, pid = payload; holdings.setdefault(rid, set()).add(pid)
        owner = pick_owner_asof(d)
        picks_by = defaultdict(list)
        for (y, r, o), ow in owner.items():
            if class_active(y, d):
                picks_by[ow].append((y, r, o))
        for rid in range(1, 13):
            pv = pvf = 0; n_no = 0
            for pid in holdings.get(rid, ()):
                v, src = raw_player_value(pid, dstr)
                cov["player_days"] += 1
                if src == "no_dp":
                    n_no += 1; cov["no_dp_player_slots"] += 1
                else:
                    cov["player_days_valued"] += 1
                    if src == "forward_fill":
                        pvf += v
                    else:
                        pv += v
            pk_a = pk_u = 0
            for (y, r, o) in picks_by.get(rid, ()):
                v, src, _ = pick_value(y, r, o, dstr)
                cov["pick_days"] += 1
                if src == "pick_tier":
                    pk_a += v
                else:
                    cov["pick_days_unavailable"] += 1
            player_total = pv + pvf
            pick_total = pk_a
            rows.append({
                "date": dstr, "roster_id": rid, "team": TEAM[rid],
                "player_value": player_total, "pick_value": pick_total,
                "total_value": player_total + pick_total,
                "pv_dp_actual": pv, "pv_forward_fill": pvf,
                "pk_pick_tier": pk_a, "pk_dp_unavailable": pk_u,
                "n_players_no_dp": n_no,
            })
        d += timedelta(days=1)
    return rows, cov


FIELDS = ["date", "roster_id", "team", "player_value", "pick_value", "total_value",
          "pv_dp_actual", "pv_forward_fill", "pk_pick_tier", "pk_dp_unavailable",
          "n_players_no_dp"]

if __name__ == "__main__":
    if "--validate" in sys.argv:
        validate(); sys.exit(0)
    validate()
    rows, cov = build()
    out = os.path.join(HERE, "team_value_daily_dp.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)
    ndays = len({r["date"] for r in rows})
    print(f"wrote {out}: {len(rows)} rows, {ndays} distinct days x 12 teams")
    pcov = 100 * cov["player_days_valued"] / max(1, cov["player_days"])
    punav = 100 * cov["pick_days_unavailable"] / max(1, cov["pick_days"])
    print(f"player-slot DP coverage: {pcov:.1f}%  ({cov['no_dp_player_slots']} no-DP slot-days)")
    print(f"pick-slot dp_unavailable share: {punav:.1f}%")
    json.dump(cov, open(os.path.join(HERE, "_coverage_dp.json"), "w"), indent=2)
