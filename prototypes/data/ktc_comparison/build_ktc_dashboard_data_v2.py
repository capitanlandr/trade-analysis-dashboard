#!/usr/bin/env python3
"""KTC dashboard rebuild v2 — resolves drafted picks to the player they became.

Mirrors the prod methodology (stage3): a pick is tracked at pick value until the
draft, then it becomes the drafted player and uses that player's value. Here every
value comes from KeepTradeCut:

  - asset resolves to a PLAYER (real player, or a drafted pick -> Player:X in the
    pipeline cache)         -> that player's real KTC SF value (at trade date / today)
  - undrafted future pick   -> KTC pick-tier history; generic "YYYY Round N" -> "YYYY Mid Nth"
  - FAAB                     -> dollar amount unchanged

Sources of truth:
  - dashboard/frontend/public/api-*.json.ktc-backup   (prod STRUCTURE: teams/sides/asset names/pick_label)
  - pipeline/asset_values_cache.csv                   (per-asset RESOLUTION: Player:X vs pick tier)
  - data/ktc_history/ktc_history.csv                  (player KTC SF series)
  - data/ktc_history/ktc_pick_history.csv             (pick-tier KTC SF series)

Backups: the *.ktc-backup files are the untouched prod originals (already present); we
overwrite the live api-*.json (currently the buggy scaled KTC variant) with the corrected KTC data.
"""
import csv, json, os, re, bisect, unicodedata
from collections import defaultdict

R = "/local/home/lndahayo/projects/trade-analysis-dashboard"
PUB = f"{R}/dashboard/frontend/public"
FMT = "SF"
CAP = 9999
ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}

# ---------- identity / KTC player series (same norm as v1) ----------
def norm(s):
    if not s: return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.'`]", "", s); s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s); return re.sub(r"\s+", " ", s).strip()

pmap = {norm(r["my_name"]): r for r in csv.DictReader(open(f"{R}/data/ktc_history/player_map.csv"))}
slug_sid = {r["ktc_slug"]: r["sleeper_id"] for r in csv.DictReader(open(f"{R}/data/ktc_history/player_map.csv")) if r.get("ktc_slug") and r.get("sleeper_id")}
master = json.load(open(f"{R}/data/ktc_history/raw/_sleeper_players_nfl.json"))
master_by_norm = {}
for pid, m in master.items():
    if (m.get("position") or "") in {"QB", "RB", "WR", "TE"}:
        nm = m.get("full_name") or " ".join(x for x in [m.get("first_name"), m.get("last_name")] if x)
        master_by_norm.setdefault(norm(nm), pid)

pser = defaultdict(list)   # sleeper_id -> [(date,val)]
with open(f"{R}/data/ktc_history/ktc_history.csv") as f:
    for r in csv.DictReader(f):
        if r["format"] == FMT:
            pser[r["sleeper_id"]].append((r["date"], int(r["value"])))
for k in pser: pser[k].sort()

TODAY = max((d for s in pser.values() for d, _ in s), default="2026-08-11")

def series_on(series, date):
    if not series: return None
    dates = [d for d, _ in series]
    i = bisect.bisect_right(dates, date) - 1
    return series[0][1] if i < 0 else series[i][1]

def player_ktc(name, date):
    n = norm(name)
    sid = None; slug = ""
    if n in pmap and pmap[n].get("sleeper_id"):
        sid = pmap[n]["sleeper_id"]; slug = pmap[n].get("ktc_slug", "")
    elif n in master_by_norm:
        sid = master_by_norm[n]
    series = pser.get(sid) if sid else None
    if not series and slug and slug in slug_sid:
        series = pser.get(slug_sid[slug])
    return (series_on(series, date), sid is not None and bool(series))

# ---------- KTC pick-tier series ----------
tser = defaultdict(list)   # "2027 Mid 1st" -> [(date,val)]
with open(f"{R}/data/ktc_history/ktc_pick_history.csv") as f:
    for r in csv.DictReader(f):
        if r["format"] == FMT:
            tser[r["pick_name"]].append((r["date"], int(r["value"])))
for k in tser: tser[k].sort()

def pick_tier_ktc(year, round_num, date):
    tier = f"{year} Mid {ORD.get(round_num, '4th')}"     # generic Round N -> Mid Nth (per user)
    v = series_on(tser.get(tier, []), date)
    if v is None:                                        # fall back to any tier that year/round
        for t in (f"{year} Early {ORD.get(round_num)}", f"{year} Late {ORD.get(round_num)}"):
            v = series_on(tser.get(t, []), date)
            if v is not None: break
    return v

# ---------- cache resolution index ----------
def meta_get(s, key):
    try:
        return (eval(s) if s and s.strip().startswith("{") else {}).get(key)
    except Exception:
        return None

cache_rows = list(csv.DictReader(open(f"{R}/pipeline/asset_values_cache.csv")))
# key: (trade_id, asset_name, pick_label or "") -> row ; also fallback (trade_id, name)-> queue
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

def asset_ktc(tid, a):
    """Return (value_then, value_now, covered_by_real_ktc)."""
    name = a["name"]; typ = a.get("type"); pl = a.get("pick_label")
    td = None  # trade date filled by caller
    return name, typ, pl

# ---------- rebuild trades ----------
src = json.load(open(f"{PUB}/api-trades.json.ktc-backup"))
trades = src["data"]["trades"]
cov = miss = pick_player = pick_tier = 0

def value_asset(tid, td, a):
    global cov, miss, pick_player, pick_tier
    name = a["name"]; typ = a.get("type"); pl = a.get("pick_label")
    row = resolve_cache(tid, name, pl)
    src_now = (row or {}).get("value_source_current", "") or ""
    # FAAB -> dollars unchanged
    if typ == "faab" or name.strip().endswith("FAAB") or src_now == "FAAB":
        dollars = 0
        m = re.search(r"\$?(\d+)", name)
        if m: dollars = int(m.group(1))
        return float(dollars), float(dollars)
    # resolved to a player (real player asset OR drafted pick -> Player:X)
    player_name = None
    if typ == "player":
        player_name = name
    elif src_now.startswith("Player:"):
        player_name = meta_get((row or {}).get("metadata"), "player") or src_now.split("Player:", 1)[1].split(" (")[0].strip()
    if player_name:
        vnow, ok1 = player_ktc(player_name, TODAY)
        vthen, ok0 = player_ktc(player_name, td)
        if vnow is not None:
            cov += 1; pick_player += (typ != "player")
            return float(vthen if vthen is not None else vnow), float(vnow)
        miss += 1  # player with no KTC -> fall through to 0-safe below
    # undrafted future pick -> KTC tier
    if typ == "draft_pick" or "Round" in name:
        ym = YEAR_RE.search(name); rm = ROUND_RE.search(name)
        if ym and rm:
            year = ym.group(1); rnd = int(rm.group(1))
            vnow = pick_tier_ktc(year, rnd, TODAY)
            vthen = pick_tier_ktc(year, rnd, td)
            if vnow is not None:
                pick_tier += 1
                return float(vthen if vthen is not None else vnow), float(vnow)
    # last resort: keep prod value (rare)
    return float(a.get("value_then") or 0), float(a.get("value_now") or 0)

for t in trades:
    tid = str(t.get("tradeId")); td = t["tradeDate"]
    for side in ("teamAAssets", "teamBAssets"):
        for a in t.get(side, []):
            vt, vn = value_asset(tid, td, a)
            a["value_then"] = round(min(vt, CAP), 1)
            a["value_now"] = round(min(vn, CAP), 1)
    aThen = sum(a["value_then"] for a in t.get("teamAAssets", []))
    aNow = sum(a["value_now"] for a in t.get("teamAAssets", []))
    bThen = sum(a["value_then"] for a in t.get("teamBAssets", []))
    bNow = sum(a["value_now"] for a in t.get("teamBAssets", []))
    t["teamAValueThen"], t["teamAValueNow"] = round(aThen, 1), round(aNow, 1)
    t["teamBValueThen"], t["teamBValueNow"] = round(bThen, 1), round(bNow, 1)
    t["teamAValueChange"] = round(aNow - aThen, 1); t["teamBValueChange"] = round(bNow - bThen, 1)
    t["winnerAtTrade"] = t["teamA"] if aThen > bThen else t["teamB"]
    t["marginAtTrade"] = round(abs(aThen - bThen), 1)
    t["winnerCurrent"] = t["teamA"] if aNow > bNow else t["teamB"]
    t["marginCurrent"] = round(abs(aNow - bNow), 1)
    sA, sB = aNow - aThen, bNow - bThen
    t["swingWinner"] = t["teamA"] if sA > sB else t["teamB"]
    t["swingMargin"] = round(abs(sA - sB), 1)

src["data"]["metadata"]["source"] = "KTC_SF_values v2 (picks resolved: drafted->player, undrafted->KTC tier)"
src["data"]["metadata"]["valueModel"] = "players & drafted picks = real KTC SF history; undrafted picks = KTC Mid-tier history; FAAB = $"

def backup_write(fname, obj):
    p = f"{PUB}/{fname}"
    if os.path.exists(p) and not os.path.exists(p + ".ktc-backup"):
        import shutil; shutil.copy2(p, p + ".ktc-backup")
    json.dump(obj, open(p, "w"), indent=2)

backup_write("api-trades.json", src)

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
backup_write("api-teams.json", teams_src)

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
backup_write("api-stats-summary.json", stats_src)

# ---------- trade metrics (formulas identical to v1) ----------
import math
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
metrics_src["metadata"]["description"] = "KTC-based advanced trade metrics v2 (picks resolved to players)"
metrics_src["metadata"]["total_trades"] = len(trades)
metrics_src["managers"] = mgrs
backup_write("api-trade-metrics.json", metrics_src)

print(f"Rebuilt on KTC scale v2. trades={len(trades)}")
print(f"  player-resolved assets: {cov} (of which drafted-picks->player: {pick_player})")
print(f"  undrafted picks -> KTC tier: {pick_tier}   players w/o KTC (kept prod): {miss}")
print(f"  TODAY={TODAY}")
mx = max(a["value_now"] for t in trades for a in t["teamAAssets"]+t["teamBAssets"])
print(f"  max asset value_now after cap: {mx}")
