#!/usr/bin/env python3
"""FantasyCalc dashboard rebuild — adaptation of build_ktc_dashboard_data_v2.py.

Every value comes from FantasyCalc (revealed preference: ~1M+ real completed trades):
  - asset resolves to a PLAYER (real player, or a drafted pick -> Player:X in the
    pipeline cache)          -> that player's FC dynasty SF value
  - undrafted future pick     -> FC pick pseudo-player ("YYYY Nth (Mid)" -> "YYYY Nth")
  - FAAB                       -> dollar amount unchanged

CRITICAL: FantasyCalc exposes NO historical time series (no per-date values). So the
at-trade "then" value cannot be sourced historically -> value_then = value_now (current
FC value) for EVERY asset, and this is flagged in metadata.note. Winners/margins are
recomputed on current FC values. FC values are their own scale (~10k top, uncapped) so
NO 9999 cap is applied.

Sources of truth:
  - dashboard/frontend/public/api-*.json.ktc-backup   (prod STRUCTURE: teams/sides/asset names/pick_label)
  - pipeline/asset_values_cache.csv                   (per-asset RESOLUTION: Player:X vs pick tier)
  - data/fc_comparison/fc_values_current.json         (FantasyCalc current values, incl. pick pseudo-players)

Output: writes the 4 api-*.json into OUT_DIR (default data/fc_comparison/out) — NEVER the
live public dir that serves the KTC tunnel.
"""
import csv, json, os, re, unicodedata, math
from collections import defaultdict

R = "/local/home/lndahayo/projects/trade-analysis-dashboard"
PUB = f"{R}/dashboard/frontend/public"           # read .ktc-backup structure ONLY (never written)
OUT = os.environ.get("FC_OUT", f"{R}/data/fc_comparison/out")
os.makedirs(OUT, exist_ok=True)
ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}

# ---------- identity normalization (same as KTC builder) ----------
def norm(s):
    if not s: return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.'`]", "", s); s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s); return re.sub(r"\s+", " ", s).strip()

# ---------- FantasyCalc value maps ----------
fc = json.load(open(f"{R}/data/fc_comparison/fc_values_current.json"))
fc_player = {}   # norm(name) -> value  (excludes pick pseudo-players)
fc_pick = {}     # exact FC name -> value  (pick pseudo-players)
PICK_RE = re.compile(r"^20\d\d\s+(Pick|Round|1st|2nd|3rd|4th)\b")  # year-anchored so "Pickens" isn't caught
for r in fc:
    nm = r["player"]["name"]; v = float(r["value"])
    if PICK_RE.search(nm):
        fc_pick[nm] = v
    else:
        fc_player.setdefault(norm(nm), v)

def player_fc(name):
    return fc_player.get(norm(name))

def pick_tier_fc(year, round_num):
    o = ORD.get(round_num, "4th")
    for cand in (f"{year} {o} (Mid)", f"{year} {o}", f"{year} {o} (Early)", f"{year} {o} (Late)"):
        if cand in fc_pick:
            return fc_pick[cand]
    return None

# ---------- cache resolution index (same as KTC builder) ----------
def meta_get(s, key):
    try:
        return (eval(s) if s and s.strip().startswith("{") else {}).get(key)
    except Exception:
        return None

cache_rows = list(csv.DictReader(open(f"{R}/pipeline/asset_values_cache.csv")))
cidx = {}
cqueue = defaultdict(list)
for r in cache_rows:
    pl = meta_get(r.get("metadata"), "pick_label") or meta_get(r.get("metadata"), "pick_position") or ""
    cidx[(r["trade_id"], r["asset_name"], pl)] = r
    cqueue[(r["trade_id"], r["asset_name"])].append(r)

def resolve_cache(tid, name, pick_label):
    if (tid, name, pick_label or "") in cidx:
        return cidx[(tid, name, pick_label or "")]
    q = cqueue.get((tid, name))
    return q[0] if q else None

YEAR_RE = re.compile(r"(20\d\d)")
ROUND_RE = re.compile(r"Round\s*(\d)")

# ---------- match stats ----------
stats = defaultdict(int)
unmatched_players = []

def value_asset(tid, a):
    """Return current FC value for an asset (then == now; no history)."""
    name = a["name"]; typ = a.get("type"); pl = a.get("pick_label")
    row = resolve_cache(tid, name, pl)
    src_now = (row or {}).get("value_source_current", "") or ""
    # FAAB -> dollars unchanged
    if typ == "faab" or name.strip().endswith("FAAB") or src_now == "FAAB":
        m = re.search(r"\$?(\d+)", name)
        stats["faab"] += 1
        return float(m.group(1)) if m else 0.0
    # resolved to a player (real player asset OR drafted pick -> Player:X)
    player_name = None
    if typ == "player":
        player_name = name
    elif src_now.startswith("Player:"):
        player_name = meta_get((row or {}).get("metadata"), "player") or src_now.split("Player:", 1)[1].split(" (")[0].strip()
    if player_name is not None:
        v = player_fc(player_name)
        if v is not None:
            if typ == "player":
                stats["players_matched"] += 1
            else:
                stats["drafted_pick_to_player"] += 1
            return v
        # player not in FC -> record and fall through
        if typ == "player":
            stats["players_unmatched"] += 1
        else:
            stats["drafted_pick_unmatched"] += 1
        unmatched_players.append(player_name)
    # undrafted future pick -> FC pick tier
    if typ == "draft_pick" or "Round" in name:
        ym = YEAR_RE.search(name); rm = ROUND_RE.search(name)
        if ym and rm:
            v = pick_tier_fc(ym.group(1), int(rm.group(1)))
            if v is not None:
                stats["undrafted_pick_tier"] += 1
                return v
        stats["pick_unmatched"] += 1
        unmatched_players.append(f"[pick] {name}")
    # last resort: keep prod value
    stats["fallback_prod"] += 1
    return float(a.get("value_now") or a.get("value_then") or 0)

NOTE = ("FantasyCalc has no historical series; at-trade (\"then\") values use current FC "
        "value for every asset. Winners/margins recomputed on current FC values. FC scale "
        "is uncapped (~10k top); no 9999 cap applied.")

# ---------- rebuild trades ----------
src = json.load(open(f"{PUB}/api-trades.json.ktc-backup"))
trades = src["data"]["trades"]

for t in trades:
    tid = str(t.get("tradeId"))
    for side in ("teamAAssets", "teamBAssets"):
        for a in t.get(side, []):
            v = round(value_asset(tid, a), 1)
            a["value_then"] = v          # no history -> then == now
            a["value_now"] = v
    aVal = sum(a["value_now"] for a in t.get("teamAAssets", []))
    bVal = sum(a["value_now"] for a in t.get("teamBAssets", []))
    t["teamAValueThen"], t["teamAValueNow"] = round(aVal, 1), round(aVal, 1)
    t["teamBValueThen"], t["teamBValueNow"] = round(bVal, 1), round(bVal, 1)
    t["teamAValueChange"] = 0.0; t["teamBValueChange"] = 0.0
    t["winnerAtTrade"] = t["teamA"] if aVal > bVal else t["teamB"]
    t["marginAtTrade"] = round(abs(aVal - bVal), 1)
    t["winnerCurrent"] = t["winnerAtTrade"]
    t["marginCurrent"] = t["marginAtTrade"]
    t["swingWinner"] = t["teamA"]        # no swing without history
    t["swingMargin"] = 0.0

src["data"]["metadata"]["source"] = "FantasyCalc dynasty SF values (revealed preference; ~1M+ real trades)"
src["data"]["metadata"]["valueModel"] = "players & drafted picks = current FC value; undrafted picks = FC Mid-tier pseudo-player; FAAB = $"
src["data"]["metadata"]["note"] = NOTE

def write(fname, obj):
    json.dump(obj, open(f"{OUT}/{fname}", "w"), indent=2)

write("api-trades.json", src)

# ---------- teams rollup ----------
teams_src = json.load(open(f"{PUB}/api-teams.json.ktc-backup"))
mgr = defaultdict(lambda: {"tradeCount": 0, "wins": 0, "margins": [], "valueGained": 0.0})
for t in trades:
    for team, vnow, other in [(t["teamA"], t["teamAValueNow"], t["teamBValueNow"]),
                               (t["teamB"], t["teamBValueNow"], t["teamAValueNow"])]:
        m = mgr[team]; m["tradeCount"] += 1; adv = vnow - other
        m["margins"].append(adv); m["valueGained"] += adv
        if adv > 0: m["wins"] += 1
teams_out = []
for tt in teams_src["data"]["teams"]:
    u = tt["sleeperUsername"]; m = mgr.get(u); new = dict(tt)
    if m and m["tradeCount"]:
        new["tradeCount"] = m["tradeCount"]; new["winRate"] = round(m["wins"]/m["tradeCount"]*100, 2)
        new["avgMargin"] = round(sum(m["margins"])/len(m["margins"]), 3); new["totalValueGained"] = round(m["valueGained"], 1)
    else:
        new.update(tradeCount=0, winRate=0, avgMargin=0, totalValueGained=0.0)
    teams_out.append(new)
teams_out.sort(key=lambda x: -x["totalValueGained"])
teams_src["data"]["teams"] = teams_out
teams_src["data"].setdefault("metadata", {})
teams_src["data"]["metadata"]["note"] = NOTE
write("api-teams.json", teams_src)

# ---------- stats summary ----------
stats_src = json.load(open(f"{PUB}/api-stats-summary.json.ktc-backup"))
ov = stats_src["data"]["overview"]
margins = [abs(t["marginCurrent"]) for t in trades]
ov["totalTrades"] = len(trades)
ov["totalTradeValue"] = round(sum(t["teamAValueNow"] + t["teamBValueNow"] for t in trades), 1)
ov["avgTradeMargin"] = round(sum(margins)/len(margins), 1) if margins else 0
ov["mostActiveTrader"] = max(teams_out, key=lambda x: x["tradeCount"])["sleeperUsername"]
ov["biggestWinner"] = teams_out[0]["sleeperUsername"]
ov["blockbusterCount"] = sum(1 for t in trades if (t["teamAValueNow"] + t["teamBValueNow"]) > 15000)
stats_src["data"]["teamRankings"] = {
    "byValueGained": [{"manager": x["sleeperUsername"], "realName": x.get("realName"), "value": x["totalValueGained"]} for x in teams_out],
    "byWinRate": [{"manager": x["sleeperUsername"], "realName": x.get("realName"), "value": x["winRate"]} for x in sorted(teams_out, key=lambda y: -y["winRate"])],
    "byTradeCount": [{"manager": x["sleeperUsername"], "realName": x.get("realName"), "value": x["tradeCount"]} for x in sorted(teams_out, key=lambda y: -y["tradeCount"])],
}
stats_src["data"]["recentActivity"] = sorted(trades, key=lambda t: t["tradeDate"], reverse=True)[:10]
stats_src["data"].setdefault("metadata", {})
stats_src["data"]["metadata"]["note"] = NOTE
write("api-stats-summary.json", stats_src)

# ---------- trade metrics (formulas identical to KTC v1/v2) ----------
def binom_pmf(n, k, p=0.5): return math.comb(n, k)*(p**k)*((1-p)**(n-k))
def p_high(n, k): return sum(binom_pmf(n, i) for i in range(k, n+1))
def p_low(n, k): return sum(binom_pmf(n, i) for i in range(0, k+1))
identity = {tt["sleeperUsername"]: tt for tt in teams_src["data"]["teams"]}
names = {u: identity[u].get("realName", u) for u in identity}
mt = defaultdict(list); mo = defaultdict(lambda: defaultdict(list))
for t in trades:
    adv = t["teamAValueNow"] - t["teamBValueNow"]
    mt[t["teamA"]].append(adv); mt[t["teamB"]].append(-adv)
    mo[t["teamA"]][t["teamB"]].append(adv); mo[t["teamB"]][t["teamA"]].append(-adv)
mgrs = []
for manager, advs in mt.items():
    n = len(advs); mean = sum(advs)/n
    std = (sum((a-mean)**2 for a in advs)/n) ** 0.5
    sharpe = mean/std if std > 0 else 0
    wins = sum(1 for a in advs if a > 0); wr = wins/n*100
    if wins >= n/2: pv = p_high(n, wins); direction = "winning"
    else: pv = p_low(n, wins); direction = "losing"
    sig = "significant" if pv < 0.05 else "approaching" if pv < 0.10 else "not_significant"
    sv = ("insufficient_data" if n < 5 else "elite" if sharpe > 0.5 and n >= 10 else
          "skilled" if sharpe > 0.3 and n >= 10 else "positive_noisy" if sharpe > 0 else "losing")
    opp = []
    for o, oa in mo[manager].items():
        opp.append({"opponent": o, "opponent_name": names.get(o, o), "net_advantage": round(sum(oa), 1),
                    "trade_count": len(oa), "avg_per_trade": round(sum(oa)/len(oa), 1)})
    opp.sort(key=lambda x: -x["net_advantage"])
    tot = sum(advs); top = round(opp[0]["net_advantage"]/tot*100, 1) if opp and tot != 0 else 0
    mgrs.append({"username": manager, "real_name": names.get(manager, manager), "trades": n, "net_advantage": round(tot, 1),
                 "sharpe": {"value": round(sharpe, 3), "mean": round(mean, 1), "std_dev": round(std, 1), "verdict": sv},
                 "significance": {"wins": wins, "win_rate": round(wr, 1), "p_value": round(pv, 4), "direction": direction, "verdict": sig},
                 "opponent_adjusted": {"unique_opponents": len(opp), "positive_matchups": sum(1 for o in opp if o["net_advantage"] > 0),
                                       "top_opponent_concentration_pct": top, "opponents": opp}})
mgrs.sort(key=lambda x: -x["net_advantage"])
metrics_src = json.load(open(f"{PUB}/api-trade-metrics.json.ktc-backup"))
metrics_src["metadata"]["description"] = "FantasyCalc-based advanced trade metrics (current values; no historical then)"
metrics_src["metadata"]["total_trades"] = len(trades)
metrics_src["metadata"]["note"] = NOTE
metrics_src["managers"] = mgrs
write("api-trade-metrics.json", metrics_src)

# ---------- report ----------
print(f"Rebuilt on FantasyCalc scale. trades={len(trades)}  OUT={OUT}")
print(f"  players matched:            {stats['players_matched']}")
print(f"  players unmatched:          {stats['players_unmatched']}")
print(f"  drafted picks -> player:    {stats['drafted_pick_to_player']}")
print(f"  drafted picks unmatched:    {stats['drafted_pick_unmatched']}")
print(f"  undrafted picks -> FC tier: {stats['undrafted_pick_tier']}")
print(f"  picks unmatched:            {stats['pick_unmatched']}")
print(f"  FAAB:                       {stats['faab']}")
print(f"  fallback to prod value:     {stats['fallback_prod']}")
if unmatched_players:
    print("  UNMATCHED:", sorted(set(unmatched_players)))
mx = max(a["value_now"] for t in trades for a in t["teamAAssets"]+t["teamBAssets"])
print(f"  max asset value_now: {mx}")
print(f"  metadata.note: {NOTE}")
