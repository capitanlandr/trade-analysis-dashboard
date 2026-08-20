#!/usr/bin/env python3
"""Step 4-6: recompute trade verdicts + manager rankings under KTC vs prod.

Read-only. Reads:
  pipeline/asset_values_cache.csv          (prod per-asset values, receiving/giving team)
  data/ktc_comparison/asset_value_comparison.csv  (player KTC values, from build_comparison.py)
Writes:
  data/ktc_comparison/trade_verdicts_compare.csv
  data/ktc_comparison/manager_rankings_compare.csv
Prints flip counts + ranking reordering for the report.

Scale handling: prod & KTC use different scales (KTC ~9x prod). To sum a whole
trade side under KTC we put everything on the KTC scale:
  - players  -> actual KTC value (nearest date <= trade date / today)
  - picks+FAAB -> prod value linearly mapped to KTC scale via a fit (ktc ~= a*prod+b)
    estimated from players that have both prod and KTC values.
We also emit a PLAYERS-ONLY verdict as a robustness check.
"""
import csv, os, statistics
from collections import defaultdict

ROOT = "/local/home/lndahayo/projects/trade-analysis-dashboard"
OUT = os.path.join(ROOT, "data/ktc_comparison")

# --- linear fit prod -> KTC from players with both values (current) ---
comp = list(csv.DictReader(open(os.path.join(OUT, "asset_value_comparison.csv"))))
def f(x):
    try: return float(x)
    except: return None
fit_pts = [(f(r["prod_value_current"]), f(r["ktc_value_current"]))
           for r in comp if r["ktc_coverage"] == "ok" and f(r["prod_value_current"]) is not None and f(r["ktc_value_current"]) is not None]
n = len(fit_pts)
mx = sum(p for p, _ in fit_pts)/n; my = sum(k for _, k in fit_pts)/n
b1 = sum((p-mx)*(k-my) for p, k in fit_pts) / sum((p-mx)**2 for p, k in fit_pts)
b0 = my - b1*mx
print(f"prod->KTC linear fit (from {n} players): ktc ~= {b1:.3f}*prod + {b0:.1f}")
def to_ktc_scale(prod_val):
    return b1*prod_val + b0 if prod_val is not None else 0.0

# --- KTC player values keyed by (trade_id, player_name) ---
ktc_then = {}; ktc_now = {}
for r in comp:
    key = (r["trade_id"], r["player_name"])
    ktc_then[key] = f(r["ktc_value_at_trade"])
    ktc_now[key] = f(r["ktc_value_current"])

# --- rebuild trades from asset cache ---
cache = list(csv.DictReader(open(os.path.join(ROOT, "pipeline/asset_values_cache.csv"))))
trades = defaultdict(list)
for r in cache:
    trades[r["trade_id"]].append(r)

def side_totals(assets, when, scaled=True, players_only=False):
    """Return dict team -> (prod_total, ktc_total) for one timepoint ('then'|'now')."""
    prod = defaultdict(float); ktc = defaultdict(float)
    pv = "value_at_trade" if when == "then" else "value_current"
    for a in assets:
        team = a["receiving_team"]
        if not team: continue
        try: pval = float(a[pv])
        except: pval = 0.0
        prod[team] += pval
        if a["asset_type"] == "player":
            kv = (ktc_then if when == "then" else ktc_now).get((a["trade_id"], a["asset_name"]))
            ktc[team] += (kv if kv is not None else (to_ktc_scale(pval) if scaled else 0.0))
        elif not players_only:
            ktc[team] += to_ktc_scale(pval) if scaled else 0.0
    return prod, ktc

def winner(totals):
    teams = list(totals.keys())
    if len(teams) < 2: return None, 0.0
    teams.sort(key=lambda t: -totals[t])
    return teams[0], round(totals[teams[0]] - totals[teams[1]], 1)

verdict_rows = []
flips_then = flips_now = 0
flip_list_then = []; flip_list_now = []
for tid, assets in trades.items():
    if len(set(a["receiving_team"] for a in assets if a["receiving_team"])) < 2:
        continue  # not a clean 2-side comparison
    date = assets[0]["trade_date"]
    for when, flip_counter_name in [("then", "then"), ("now", "now")]:
        prod, ktc = side_totals(assets, when)
        pw, pm = winner(prod); kw, km = winner(ktc)
        _, ktc_po = side_totals(assets, when, players_only=True)
        kw_po, km_po = winner(ktc_po)
        flip = (pw is not None and kw is not None and pw != kw)
        verdict_rows.append({
            "trade_id": tid, "trade_date": date, "timepoint": when,
            "prod_winner": pw or "", "prod_margin": pm,
            "ktc_winner": kw or "", "ktc_margin": km,
            "ktc_playersonly_winner": kw_po or "", "ktc_playersonly_margin": km_po,
            "verdict_flip": "YES" if flip else "no",
        })
        if flip:
            if when == "then": flips_then += 1; flip_list_then.append((tid, date, pw, kw))
            else: flips_now += 1; flip_list_now.append((tid, date, pw, kw))

with open(os.path.join(OUT, "trade_verdicts_compare.csv"), "w", newline="") as fo:
    w = csv.DictWriter(fo, fieldnames=list(verdict_rows[0].keys())); w.writeheader(); w.writerows(verdict_rows)

n_trades = len(set(v["trade_id"] for v in verdict_rows))
print(f"\n=== TRADE VERDICTS ({n_trades} 2+-sided trades) ===")
print(f"at-trade winner flips (prod vs KTC): {flips_then}/{n_trades}")
for tid, d, pw, kw in flip_list_then:
    print(f"  [then] {d} trade {tid}: prod={pw} -> KTC={kw}")
print(f"current winner flips (prod vs KTC): {flips_now}/{n_trades}")
for tid, d, pw, kw in flip_list_now:
    print(f"  [now]  {d} trade {tid}: prod={pw} -> KTC={kw}")

# --- manager rankings: net value gained (current) = received_now - given_now ---
prod_net = defaultdict(float); ktc_net = defaultdict(float)
prod_recv = defaultdict(float); prod_give = defaultdict(float)
ktc_recv = defaultdict(float); ktc_give = defaultdict(float)
tcount = defaultdict(int); trades_seen = defaultdict(set)
for tid, assets in trades.items():
    for a in assets:
        recv = a["receiving_team"]; give = a["giving_team"]
        try: pnow = float(a["value_current"])
        except: pnow = 0.0
        if a["asset_type"] == "player":
            kv = ktc_now.get((tid, a["asset_name"]))
            know = kv if kv is not None else to_ktc_scale(pnow)
        else:
            know = to_ktc_scale(pnow)
        if recv:
            prod_recv[recv] += pnow; ktc_recv[recv] += know; trades_seen[recv].add(tid)
        if give:
            prod_give[give] += pnow; ktc_give[give] += know; trades_seen[give].add(tid)
mgrs = set(prod_recv) | set(prod_give)
for m in mgrs:
    prod_net[m] = prod_recv[m] - prod_give[m]
    ktc_net[m] = ktc_recv[m] - ktc_give[m]

def rank(d):
    order = sorted(d.keys(), key=lambda m: -d[m])
    return {m: i+1 for i, m in enumerate(order)}
pr = rank(prod_net); kr = rank(ktc_net)
mrows = []
for m in sorted(mgrs, key=lambda m: pr[m]):
    mrows.append({"manager": m, "trades": len(trades_seen[m]),
                  "prod_net_value": round(prod_net[m], 1), "prod_rank": pr[m],
                  "ktc_net_value": round(ktc_net[m], 1), "ktc_rank": kr[m],
                  "rank_delta": pr[m] - kr[m]})
with open(os.path.join(OUT, "manager_rankings_compare.csv"), "w", newline="") as fo:
    w = csv.DictWriter(fo, fieldnames=list(mrows[0].keys())); w.writeheader(); w.writerows(mrows)

reorder = [r for r in mrows if r["rank_delta"] != 0]
print(f"\n=== MANAGER RANKINGS (net value gained, current) ===")
print(f"managers: {len(mrows)}   reordered under KTC: {len(reorder)}")
print(f"{'manager':16s} {'prod#':>5} {'ktc#':>5} {'Δ':>3}  {'prod_net':>10} {'ktc_net':>10}")
for r in mrows:
    print(f"{r['manager']:16s} {r['prod_rank']:>5} {r['ktc_rank']:>5} {r['rank_delta']:>+3}  {r['prod_net_value']:>10.1f} {r['ktc_net_value']:>10.1f}")

# Kendall-tau-ish: count of pairwise inversions between prod and KTC ranking
managers = [r["manager"] for r in mrows]
inv = 0; tot = 0
for i in range(len(managers)):
    for j in range(i+1, len(managers)):
        tot += 1
        if (pr[managers[i]]-pr[managers[j]])*(kr[managers[i]]-kr[managers[j]]) < 0:
            inv += 1
print(f"pairwise rank inversions: {inv}/{tot}")
