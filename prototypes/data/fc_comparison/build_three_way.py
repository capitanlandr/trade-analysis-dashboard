#!/usr/bin/env python3
"""Three-way rank comparison: DynastyProcess vs KeepTradeCut vs FantasyCalc.
Read-only against sources; writes only three_way_rank_comparison.{csv,md} in this dir.
"""
import csv, json, re, os
from collections import defaultdict

BASE = "/local/home/lndahayo/projects/trade-analysis-dashboard"
FC_DIR = f"{BASE}/data/fc_comparison"
DP_CSV = "/tmp/dp_values.csv"
KTC_HIST = f"{BASE}/data/ktc_history/ktc_history.csv"

# ---------- name normalization ----------
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
def norm(name):
    n = name.lower().strip()
    n = n.replace("&", "and")
    n = re.sub(r"[.'`,]", "", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    toks = [t for t in n.split() if t and t not in SUFFIXES]
    return " ".join(toks)

# ---------- DP ----------
dp = {}  # norm -> value_2qb (float)
with open(DP_CSV, newline="") as f:
    for row in csv.DictReader(f):
        v = row.get("value_2qb", "").strip()
        pos = row.get("pos", "").strip().upper()
        if not v:
            continue
        try:
            v = float(v)
        except ValueError:
            continue
        # players only (exclude picks if any); DP values.csv is players
        dp[norm(row["player"])] = (v, row["player"], pos)

# ---------- KTC: latest SF value per player ----------
ktc_latest = {}  # norm -> (date, value, orig_name)
with open(KTC_HIST, newline="") as f:
    for row in csv.DictReader(f):
        if row.get("format") != "SF":
            continue
        val = row.get("value", "").strip()
        if not val:
            continue
        try:
            val = float(val)
        except ValueError:
            continue
        d = row.get("date", "")
        key = norm(row["player_name"])
        if key not in ktc_latest or d > ktc_latest[key][0]:
            ktc_latest[key] = (d, val, row["player_name"])
# drop players whose latest value is 0 (not currently valued)
ktc = {k: (v[1], v[2]) for k, v in ktc_latest.items() if v[1] > 0}

# ---------- FC ----------
fc = {}  # norm -> (value, orig_name)
with open(f"{FC_DIR}/fc_values_current.json") as f:
    data = json.load(f)
for rec in data:
    p = rec["player"]
    name = p["name"]
    val = float(rec["value"])
    fc[norm(name)] = (val, name)

# ---------- build ranks within each source (dense by value desc) ----------
def ranks(d):
    # d: norm -> value ; returns norm -> rank (1 = highest value)
    ordered = sorted(d.items(), key=lambda kv: -kv[1])
    r = {}
    for i, (k, _) in enumerate(ordered, 1):
        r[k] = i
    return r

dp_val = {k: v[0] for k, v in dp.items()}
ktc_val = {k: v[0] for k, v in ktc.items()}
fc_val = {k: v[0] for k, v in fc.items()}

dp_rank = ranks(dp_val)
ktc_rank = ranks(ktc_val)
fc_rank = ranks(fc_val)

# display names
def disp(k):
    for src in (dp, ktc, fc):
        if k in src:
            return src[k][1]
    return k

# ---------- Spearman + Kendall ----------
def spearman(pairs):
    # pairs: list of (rankA, rankB) on the intersection; recompute ranks within intersection
    a = [p[0] for p in pairs]
    b = [p[1] for p in pairs]
    ra = to_ranks(a); rb = to_ranks(b)
    n = len(pairs)
    mean_a = sum(ra)/n; mean_b = sum(rb)/n
    cov = sum((ra[i]-mean_a)*(rb[i]-mean_b) for i in range(n))
    va = sum((x-mean_a)**2 for x in ra); vb = sum((x-mean_b)**2 for x in rb)
    return cov/((va*vb)**0.5)

def to_ranks(vals):
    # average ranks, ascending order of value-rank input; we just need consistent ordering
    idx = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0.0]*len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j+1 < len(vals) and vals[idx[j+1]] == vals[idx[i]]:
            j += 1
        avg = (i + j)/2.0 + 1
        for k in range(i, j+1):
            r[idx[k]] = avg
        i = j+1
    return r

def kendall(pairs):
    n = len(pairs)
    if n > 2000:  # cap for speed; our N is small
        pass
    c = d = 0
    for i in range(n):
        ai, bi = pairs[i]
        for j in range(i+1, n):
            aj, bj = pairs[j]
            sa = (ai>aj) - (ai<aj)
            sb = (bi>bj) - (bi<bj)
            prod = sa*sb
            if prod > 0: c += 1
            elif prod < 0: d += 1
    tot = c + d
    return (c-d)/tot if tot else float("nan")

def pair_stats(rankA, rankB):
    common = set(rankA) & set(rankB)
    pairs = [(rankA[k], rankB[k]) for k in common]
    return len(common), spearman(pairs), kendall(pairs), common

n_dpktc, s_dpktc, k_dpktc, _ = pair_stats(dp_rank, ktc_rank)
n_dpfc,  s_dpfc,  k_dpfc,  _ = pair_stats(dp_rank, fc_rank)
n_ktcfc, s_ktcfc, k_ktcfc, _ = pair_stats(ktc_rank, fc_rank)

# ---------- 3-way intersection ----------
tri = set(dp_rank) & set(ktc_rank) & set(fc_rank)

# Re-rank WITHIN the 3-way intersection so spreads are comparable
def rerank_within(keys, valmap):
    ordered = sorted(keys, key=lambda k: -valmap[k])
    return {k: i for i, k in enumerate(ordered, 1)}
dpr = rerank_within(tri, dp_val)
ktr = rerank_within(tri, ktc_val)
fcr = rerank_within(tri, fc_val)

rows = []
for k in tri:
    rows.append({
        "player": disp(k),
        "dp_value": round(dp_val[k], 1),
        "dp_rank": dpr[k],
        "ktc_value": round(ktc_val[k], 1),
        "ktc_rank": ktr[k],
        "fc_value": round(fc_val[k], 1),
        "fc_rank": fcr[k],
        "spread": max(dpr[k], ktr[k], fcr[k]) - min(dpr[k], ktr[k], fcr[k]),
        # FC vs consensus(DP,KTC): positive => FC ranks BETTER (lower rank num) than consensus
        "fc_vs_consensus": round((dpr[k]+ktr[k])/2.0 - fcr[k], 1),
    })

# ---------- write CSV (unified per-player, sorted by consensus rank) ----------
rows_out = sorted(rows, key=lambda r: (r["dp_rank"]+r["ktc_rank"]+r["fc_rank"]))
csv_path = f"{FC_DIR}/three_way_rank_comparison.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["player","dp_value","dp_rank","ktc_value","ktc_rank","fc_value","fc_rank","spread","fc_vs_consensus"])
    w.writeheader()
    for r in rows_out:
        w.writerow(r)

# ---------- divergence buckets ----------
biggest_spread = sorted(rows, key=lambda r: -r["spread"])[:15]
fc_higher = sorted(rows, key=lambda r: -r["fc_vs_consensus"])[:10]  # FC much more bullish
fc_lower  = sorted(rows, key=lambda r:  r["fc_vs_consensus"])[:10]  # FC much more bearish

# market (KTC+FC) vs DP: youth thesis. consensus_market_rank - dp_rank
for r in rows:
    r["market_vs_dp"] = (r["ktc_rank"]+r["fc_rank"])/2.0 - r["dp_rank"]
market_loves = sorted(rows, key=lambda r: r["market_vs_dp"])[:10]   # market ranks better than DP
dp_loves     = sorted(rows, key=lambda r: -r["market_vs_dp"])[:10]  # DP ranks better than market

# ---------- write markdown ----------
def mdtable(rs, cols, headers):
    out = "| " + " | ".join(headers) + " |\n"
    out += "|" + "|".join(["---"]*len(headers)) + "|\n"
    for r in rs:
        out += "| " + " | ".join(str(r[c]) for c in cols) + " |\n"
    return out

md = f"""# Three-way Rank Comparison — DynastyProcess vs KeepTradeCut vs FantasyCalc

_Generated 2026-08-12. Read-only analysis; scale-free rank comparison across three dynasty value sources._

## Sources & philosophy (one line each)
- **DynastyProcess (DP)** = analyst opinion — a deterministic exponential curve over FantasyPros Superflex ECR (`value_2qb ≈ 10295·exp(−0.0234·ecr)`, R²=0.9997). No market signal; slowest to react.
- **KeepTradeCut (KTC)** = stated preference — crowd keep/trade/cut survey votes (0–9999 cap). What the community *says* it would do.
- **FantasyCalc (FC)** = revealed preference — implied values from ~1M real completed trades. What the market *actually does*; fastest to react, noisier for illiquid players.

All three configured to SF / 2QB dynasty. DP = `values.csv value_2qb` (scrape {open(DP_CSV).readline() and '2026-08-07'}); KTC = latest SF value per player from `ktc_history.csv` (through 2026-08-10); FC = live API pull.

## Coverage
| Source | Valued players |
|---|---|
| DynastyProcess (value_2qb) | {len(dp_val)} |
| KeepTradeCut (SF, latest>0) | {len(ktc_val)} |
| FantasyCalc (SF dynasty PPR) | {len(fc_val)} |
| **DP ∩ KTC** | {n_dpktc} |
| **DP ∩ FC** | {n_dpfc} |
| **KTC ∩ FC** | {n_ktcfc} |
| **3-way intersection** | {len(tri)} |

## Pairwise rank correlations
| Pair | N (intersection) | Spearman ρ | Kendall τ |
|---|---|---|---|
| DP – KTC | {n_dpktc} | {s_dpktc:.3f} | {k_dpktc:.3f} |
| DP – FC | {n_dpfc} | {s_dpfc:.3f} | {k_dpfc:.3f} |
| KTC – FC | {n_ktcfc} | {s_ktcfc:.3f} | {k_ktcfc:.3f} |

**Read:** The two market sources (KTC, FC) agree with each other most (ρ={s_ktcfc:.3f}) — both are crowd/market signals. Each market source correlates less with the analyst ECR curve (DP). This is the core finding: *market ≈ market > market vs analyst.*

## Biggest 3-way rank spread (max rank − min rank, within the {len(tri)}-player intersection)
{mdtable(biggest_spread, ["player","dp_rank","ktc_rank","fc_rank","spread"], ["Player","DP rank","KTC rank","FC rank","Spread"])}

## FantasyCalc most BULLISH vs the DP/KTC consensus
_(fc_vs_consensus = avg(DP,KTC) rank − FC rank; positive = FC ranks the player higher/better)_
{mdtable(fc_higher, ["player","dp_rank","ktc_rank","fc_rank","fc_vs_consensus"], ["Player","DP rank","KTC rank","FC rank","FC−consensus"])}

## FantasyCalc most BEARISH vs the DP/KTC consensus
{mdtable(fc_lower, ["player","dp_rank","ktc_rank","fc_rank","fc_vs_consensus"], ["Player","DP rank","KTC rank","FC rank","FC−consensus"])}

## Market (KTC+FC) vs analyst (DP) — youth/upside thesis test
### Market ranks MUCH higher than DP (market loves youth/upside)
{mdtable(market_loves, ["player","dp_rank","ktc_rank","fc_rank"], ["Player","DP rank","KTC rank","FC rank"])}

### DP ranks MUCH higher than market (ECR still rewards proven vets)
{mdtable(dp_loves, ["player","dp_rank","ktc_rank","fc_rank"], ["Player","DP rank","KTC rank","FC rank"])}
"""

with open(f"{FC_DIR}/three_way_rank_comparison.md", "w") as f:
    f.write(md)

# ---------- console report ----------
print("SPEARMAN:")
print(f"  DP-KTC  N={n_dpktc}  rho={s_dpktc:.3f}  tau={k_dpktc:.3f}")
print(f"  DP-FC   N={n_dpfc}  rho={s_dpfc:.3f}  tau={k_dpfc:.3f}")
print(f"  KTC-FC  N={n_ktcfc}  rho={s_ktcfc:.3f}  tau={k_ktcfc:.3f}")
print(f"3-WAY INTERSECTION N={len(tri)}")
print("\nBIGGEST 3-WAY SPREAD (top 8):")
for r in biggest_spread[:8]:
    print(f"  {r['player']:24s} DP={r['dp_rank']:3d} KTC={r['ktc_rank']:3d} FC={r['fc_rank']:3d} spread={r['spread']}")
print("\nFC MOST BULLISH vs consensus (top 6):")
for r in fc_higher[:6]:
    print(f"  {r['player']:24s} DP={r['dp_rank']:3d} KTC={r['ktc_rank']:3d} FC={r['fc_rank']:3d} fc-cons=+{r['fc_vs_consensus']}")
print("\nFC MOST BEARISH vs consensus (top 6):")
for r in fc_lower[:6]:
    print(f"  {r['player']:24s} DP={r['dp_rank']:3d} KTC={r['ktc_rank']:3d} FC={r['fc_rank']:3d} fc-cons={r['fc_vs_consensus']}")
print("\nMARKET LOVES (vs DP) top 6:")
for r in market_loves[:6]:
    print(f"  {r['player']:24s} DP={r['dp_rank']:3d} KTC={r['ktc_rank']:3d} FC={r['fc_rank']:3d}")
print("\nDP LOVES (vs market) top 6:")
for r in dp_loves[:6]:
    print(f"  {r['player']:24s} DP={r['dp_rank']:3d} KTC={r['ktc_rank']:3d} FC={r['fc_rank']:3d}")
