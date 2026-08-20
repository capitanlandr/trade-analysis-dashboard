#!/usr/bin/env python3
"""Regenerate the dashboard's 4 value-bearing JSON files using KTC player values.

Read-only against prod. Rebuilds, on a single consistent KTC scale:
  api-trades.json         (per-asset values -> KTC; team totals/winners/margins recomputed)
  api-teams.json          (tradeCount, winRate, avgMargin, totalValueGained recomputed)
  api-stats-summary.json  (overview + teamRankings + recentActivity recomputed)
  api-trade-metrics.json  (sharpe / significance / opponent-adjusted; formulas copied
                           verbatim from pipeline/scripts/generate_trade_metrics.py)

Scale model (documented in report/CHANGELOG):
  - player asset value  -> actual KTC SF value at trade date (nearest <= date) and current (2026-08-10)
  - draft_pick / faab   -> prod value * proportional factor (kept on the KTC scale;
                           2.539 for 'then', 2.766 for 'now', value-weighted through origin)
  - players with no KTC data (retired/deep-bench) fall back to the proportional factor too,
    so no side silently drops value.

Backs up each target to <file>.ktc-backup before overwriting.
"""
import csv, json, os, math, shutil, unicodedata, re, bisect
from collections import defaultdict

ROOT = "/local/home/lndahayo/projects/trade-analysis-dashboard"
PUB = os.path.join(ROOT, "dashboard/frontend/public")
TODAY = "2026-08-10"
FMT = "SF"
FACTOR_THEN = 2.539
FACTOR_NOW = 2.766

# ---- identity + KTC series (same logic as build_comparison.py) ----
def norm(s):
    if not s: return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.'`]", "", s); s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s); return re.sub(r"\s+", " ", s).strip()

pmap = {norm(r["my_name"]): r for r in csv.DictReader(open(os.path.join(ROOT, "data/ktc_history/player_map.csv")))}
master = json.load(open(os.path.join(ROOT, "data/ktc_history/raw/_sleeper_players_nfl.json")))
master_by_norm = {}
for pid, m in master.items():
    if (m.get("position") or "") in {"QB", "RB", "WR", "TE"}:
        nm = m.get("full_name") or " ".join(x for x in [m.get("first_name"), m.get("last_name")] if x)
        master_by_norm.setdefault(norm(nm), pid)

ktc = defaultdict(list)
with open(os.path.join(ROOT, "data/ktc_history/ktc_history.csv")) as f:
    for r in csv.DictReader(f):
        if r["format"] == FMT:
            ktc[r["sleeper_id"]].append((r["date"], int(r["value"])))
for k in ktc: ktc[k].sort()
slug_sid = {r["ktc_slug"]: r["sleeper_id"] for r in csv.DictReader(open(os.path.join(ROOT, "data/ktc_history/player_map.csv"))) if r["ktc_slug"] and r["sleeper_id"]}

def resolve_sid(name):
    n = norm(name)
    if n in pmap and pmap[n]["sleeper_id"]: return pmap[n]["sleeper_id"], pmap[n]["ktc_slug"]
    if n in master_by_norm: return master_by_norm[n], ""
    return None, ""

def ktc_on(sid, slug, date):
    series = ktc.get(sid)
    if not series and slug and slug in slug_sid: series = ktc.get(slug_sid[slug])
    if not series: return None
    dates = [d for d, _ in series]
    i = bisect.bisect_right(dates, date) - 1
    return series[0][1] if i < 0 else series[i][1]

def ktc_player_value(name, when, trade_date, prod_val):
    """KTC value for a player; fall back to proportional prod scaling if no KTC data."""
    sid, slug = resolve_sid(name)
    v = ktc_on(sid, slug, trade_date if when == "then" else TODAY) if sid else None
    if v is not None: return float(v), True
    factor = FACTOR_THEN if when == "then" else FACTOR_NOW
    return round((prod_val or 0) * factor, 1), False

def scaled_nonplayer(prod_val, when):
    factor = FACTOR_THEN if when == "then" else FACTOR_NOW
    return round((prod_val or 0) * factor, 1)

# ---- rebuild trades ----
src = json.load(open(os.path.join(PUB, "api-trades.json")))
trades = src["data"]["trades"]
covered = missing = 0

def side_value(assets, when, trade_date):
    tot = 0.0
    for a in assets:
        pv = a.get("value_then" if when == "then" else "value_now") or 0
        if a.get("type") == "player":
            v, ok = ktc_player_value(a["name"], when, trade_date, pv)
            globals()['_ok'] = ok
            tot += v
        else:
            tot += scaled_nonplayer(pv, when)
    return tot

for t in trades:
    td = t["tradeDate"]
    # rewrite asset-level values so the UI drill-down also shows KTC numbers
    for side in ("teamAAssets", "teamBAssets"):
        for a in t.get(side, []):
            for when, key in (("then", "value_then"), ("now", "value_now")):
                pv = a.get(key) or 0
                if a.get("type") == "player":
                    v, ok = ktc_player_value(a["name"], when, td, pv)
                    a[key] = v
                    if when == "now":
                        if ok: covered += 1
                        else: missing += 1
                else:
                    a[key] = scaled_nonplayer(pv, when)
    aThen = sum(a["value_then"] for a in t.get("teamAAssets", []))
    aNow = sum(a["value_now"] for a in t.get("teamAAssets", []))
    bThen = sum(a["value_then"] for a in t.get("teamBAssets", []))
    bNow = sum(a["value_now"] for a in t.get("teamBAssets", []))
    t["teamAValueThen"], t["teamAValueNow"] = round(aThen, 1), round(aNow, 1)
    t["teamBValueThen"], t["teamBValueNow"] = round(bThen, 1), round(bNow, 1)
    t["teamAValueChange"] = round(aNow - aThen, 1)
    t["teamBValueChange"] = round(bNow - bThen, 1)
    # winner = who RECEIVED more value. teamA received teamAAssets.
    t["winnerAtTrade"] = t["teamA"] if aThen > bThen else t["teamB"]
    t["marginAtTrade"] = round(abs(aThen - bThen), 1)
    t["winnerCurrent"] = t["teamA"] if aNow > bNow else t["teamB"]
    t["marginCurrent"] = round(abs(aNow - bNow), 1)
    # swing = who improved more since the trade
    swingA = aNow - aThen; swingB = bNow - bThen
    t["swingWinner"] = t["teamA"] if swingA > swingB else t["teamB"]
    t["swingMargin"] = round(abs(swingA - swingB), 1)

src["data"]["metadata"]["source"] = "KTC_SF_values (local KTC variant)"
src["data"]["metadata"]["valueModel"] = f"players=KTC {FMT}; picks/faab=prod x{FACTOR_NOW}"

# ---- backup + write api-trades.json ----
def backup_write(fname, obj):
    p = os.path.join(PUB, fname)
    if os.path.exists(p) and not os.path.exists(p + ".ktc-backup"):
        shutil.copy2(p, p + ".ktc-backup")
    json.dump(obj, open(p, "w"), indent=2)

backup_write("api-trades.json", src)

# ---- teams (per-manager rollup) ----
mgr = defaultdict(lambda: {"tradeCount": 0, "wins": 0, "margins": [], "valueGained": 0.0})
# identity from existing teams file
teams_src = json.load(open(os.path.join(PUB, "api-teams.json")))
identity = {tt["sleeperUsername"]: tt for tt in teams_src["data"]["teams"]}
for t in trades:
    for team, recv_assets, val_now_side, other_now in [
        (t["teamA"], "teamAAssets", t["teamAValueNow"], t["teamBValueNow"]),
        (t["teamB"], "teamBAssets", t["teamBValueNow"], t["teamAValueNow"]),
    ]:
        m = mgr[team]; m["tradeCount"] += 1
        adv = val_now_side - other_now
        m["margins"].append(adv)
        if adv > 0: m["wins"] += 1
        m["valueGained"] += adv
teams_out = []
for tt in teams_src["data"]["teams"]:
    u = tt["sleeperUsername"]; m = mgr.get(u)
    new = dict(tt)
    if m and m["tradeCount"]:
        new["tradeCount"] = m["tradeCount"]
        new["winRate"] = round(m["wins"] / m["tradeCount"] * 100, 2)
        new["avgMargin"] = round(sum(m["margins"]) / len(m["margins"]), 3)
        new["totalValueGained"] = round(m["valueGained"], 1)
    else:
        new["tradeCount"] = 0; new["winRate"] = 0; new["avgMargin"] = 0; new["totalValueGained"] = 0.0
    teams_out.append(new)
teams_out.sort(key=lambda x: -x["totalValueGained"])
teams_src["data"]["teams"] = teams_out
backup_write("api-teams.json", teams_src)

# ---- stats summary ----
stats_src = json.load(open(os.path.join(PUB, "api-stats-summary.json")))
ov = stats_src["data"]["overview"]
all_margins = [abs(t["marginCurrent"]) for t in trades]
ov["totalTrades"] = len(trades)
ov["totalTradeValue"] = round(sum(t["teamAValueNow"] + t["teamBValueNow"] for t in trades), 1)
ov["avgTradeMargin"] = round(sum(all_margins) / len(all_margins), 1) if all_margins else 0
# most active trader / biggest winner from teams_out
ov["mostActiveTrader"] = max(teams_out, key=lambda x: x["tradeCount"])["sleeperUsername"]
ov["biggestWinner"] = teams_out[0]["sleeperUsername"]
ov["blockbusterCount"] = sum(1 for t in trades if (t["teamAValueNow"] + t["teamBValueNow"]) > 15000)
stats_src["data"]["teamRankings"] = {
    "byValueGained": [{"manager": x["sleeperUsername"], "realName": x.get("realName"), "value": x["totalValueGained"]} for x in teams_out],
    "byWinRate": [{"manager": x["sleeperUsername"], "realName": x.get("realName"), "value": x["winRate"]} for x in sorted(teams_out, key=lambda y: -y["winRate"])],
    "byTradeCount": [{"manager": x["sleeperUsername"], "realName": x.get("realName"), "value": x["tradeCount"]} for x in sorted(teams_out, key=lambda y: -y["tradeCount"])],
}
# recentActivity: most recent 10 trades (already in file shape) -> refresh from rebuilt trades
recent = sorted(trades, key=lambda t: t["tradeDate"], reverse=True)[:10]
stats_src["data"]["recentActivity"] = recent
backup_write("api-stats-summary.json", stats_src)

# ---- trade metrics (formulas copied from generate_trade_metrics.py) ----
def binom_pmf(n, k, p=0.5):
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
def p_high(n, k): return sum(binom_pmf(n, i) for i in range(k, n + 1))
def p_low(n, k): return sum(binom_pmf(n, i) for i in range(0, k + 1))
team_names = {u: identity[u].get("realName", u) for u in identity}
mt = defaultdict(list); mo = defaultdict(lambda: defaultdict(list))
for t in trades:
    ta, tb = t["teamA"], t["teamB"]
    adv = t["teamAValueNow"] - t["teamBValueNow"]
    mt[ta].append(adv); mt[tb].append(-adv)
    mo[ta][tb].append(adv); mo[tb][ta].append(-adv)
mgrs = []
for manager, advs in mt.items():
    n = len(advs); mean = sum(advs)/n
    std = (sum((a-mean)**2 for a in advs)/n) ** 0.5
    sharpe = mean/std if std > 0 else 0
    wins = sum(1 for a in advs if a > 0); wr = wins/n*100
    if wins >= n/2: pv = p_high(n, wins); direction = "winning"
    else: pv = p_low(n, wins); direction = "losing"
    sig = "significant" if pv < 0.05 else "approaching" if pv < 0.10 else "not_significant"
    if n < 5: sv = "insufficient_data"
    elif sharpe > 0.5 and n >= 10: sv = "elite"
    elif sharpe > 0.3 and n >= 10: sv = "skilled"
    elif sharpe > 0: sv = "positive_noisy"
    else: sv = "losing"
    opp = []
    for o, oa in mo[manager].items():
        opp.append({"opponent": o, "opponent_name": team_names.get(o, o), "net_advantage": round(sum(oa), 1),
                    "trade_count": len(oa), "avg_per_trade": round(sum(oa)/len(oa), 1)})
    opp.sort(key=lambda x: -x["net_advantage"])
    tot = sum(advs)
    top_pct = round(opp[0]["net_advantage"]/tot*100, 1) if opp and tot != 0 else 0
    mgrs.append({"username": manager, "real_name": team_names.get(manager, manager), "trades": n,
                 "net_advantage": round(tot, 1),
                 "sharpe": {"value": round(sharpe, 3), "mean": round(mean, 1), "std_dev": round(std, 1), "verdict": sv},
                 "significance": {"wins": wins, "win_rate": round(wr, 1), "p_value": round(pv, 4), "direction": direction, "verdict": sig},
                 "opponent_adjusted": {"unique_opponents": len(opp), "positive_matchups": sum(1 for o in opp if o["net_advantage"] > 0),
                                       "top_opponent_concentration_pct": top_pct, "opponents": opp}})
mgrs.sort(key=lambda x: -x["net_advantage"])
metrics_src = json.load(open(os.path.join(PUB, "api-trade-metrics.json")))
metrics_src["metadata"]["description"] = "KTC-based advanced trade metrics (local KTC variant)"
metrics_src["metadata"]["total_trades"] = len(trades)
metrics_src["managers"] = mgrs
backup_write("api-trade-metrics.json", metrics_src)

print(f"Rebuilt 4 JSON files on KTC scale.")
print(f"  trades: {len(trades)}  player-asset-now covered by KTC: {covered}  fallback-scaled: {missing}")
print(f"  managers: {len(teams_out)}")
print("  top-3 by KTC value gained:", [(x['sleeperUsername'], x['totalValueGained']) for x in teams_out[:3]])
