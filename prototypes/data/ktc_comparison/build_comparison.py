#!/usr/bin/env python3
"""Step 2-3: build per-asset prod-vs-KTC comparison + agreement stats.

Read-only. Reads:
  pipeline/asset_values_cache.csv        (prod: per-asset value_at_trade / value_current)
  data/ktc_history/ktc_history.csv       (KTC daily SF+1QB series)
  data/ktc_history/player_map.csv        (my players -> sleeper_id/slug)
  data/ktc_history/raw/_sleeper_players_nfl.json  (name->sleeper_id fallback)
Writes:
  data/ktc_comparison/asset_value_comparison.csv
Prints agreement stats (correlation, MAD) for the report.

Format: league is Superflex -> primary KTC format = SF.
Trade-date alignment: KTC value on the trade date, else nearest available KTC date <= trade date.
Scale: prod and KTC use different scales; we report raw deltas AND rank-percentile deltas.
"""
import csv, json, re, unicodedata, os, statistics, bisect
from collections import defaultdict

ROOT = "/local/home/lndahayo/projects/trade-analysis-dashboard"
OUT = os.path.join(ROOT, "data/ktc_comparison")
TODAY = "2026-08-10"
PRIMARY_FMT = "SF"

def norm(s):
    if not s: return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.'`]", "", s); s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s); return re.sub(r"\s+", " ", s).strip()

# --- name -> (sleeper_id, ktc_slug) ---
pmap = {norm(r["my_name"]): r for r in csv.DictReader(open(os.path.join(ROOT, "data/ktc_history/player_map.csv")))}
master = json.load(open(os.path.join(ROOT, "data/ktc_history/raw/_sleeper_players_nfl.json")))
master_by_norm = {}
for pid, m in master.items():
    if (m.get("position") or "") in {"QB", "RB", "WR", "TE"}:
        nm = m.get("full_name") or " ".join(x for x in [m.get("first_name"), m.get("last_name")] if x)
        master_by_norm.setdefault(norm(nm), pid)

def resolve(name):
    n = norm(name)
    if n in pmap and pmap[n]["sleeper_id"]:
        return pmap[n]["sleeper_id"], pmap[n]["ktc_slug"]
    if n in master_by_norm:
        pid = master_by_norm[n]
        # is this sleeper_id resolved in player_map (has slug)?
        return pid, ""
    return None, ""

# --- KTC series indexed by (sleeper_id, fmt) -> sorted list of (date, value) ---
ktc = defaultdict(list)
with open(os.path.join(ROOT, "data/ktc_history/ktc_history.csv")) as f:
    for r in csv.DictReader(f):
        ktc[(r["sleeper_id"], r["format"])].append((r["date"], int(r["value"])))
for k in ktc:
    ktc[k].sort()
# also index by slug for players resolved via slug but rostered under a different sleeper_id
ktc_slug = defaultdict(list)
slug_of_sid = {}
for r in csv.DictReader(open(os.path.join(ROOT, "data/ktc_history/player_map.csv"))):
    if r["ktc_slug"] and r["sleeper_id"]:
        slug_of_sid[r["sleeper_id"]] = r["ktc_slug"]

def ktc_on(sid, slug, fmt, date):
    """KTC value on `date` (exact or nearest <= date). Returns (value, used_date) or (None,None)."""
    series = ktc.get((sid, fmt))
    if not series and slug:
        # find any sid mapped to this slug
        for s2, sl in slug_of_sid.items():
            if sl == slug and (s2, fmt) in ktc:
                series = ktc[(s2, fmt)]; break
    if not series:
        return None, None
    dates = [d for d, _ in series]
    i = bisect.bisect_right(dates, date) - 1
    if i < 0:
        # trade predates KTC coverage; use earliest available
        return series[0][1], series[0][0]
    return series[i][1], series[i][0]

# --- prod assets ---
rows_out = []
cache = [r for r in csv.DictReader(open(os.path.join(ROOT, "pipeline/asset_values_cache.csv"))) if r["asset_type"] == "player"]
joined = 0
for r in cache:
    name = r["asset_name"]; date = r["trade_date"]
    sid, slug = resolve(name)
    try: prod_then = float(r["value_at_trade"])
    except: prod_then = None
    try: prod_now = float(r["value_current"])
    except: prod_now = None
    cov = "no_ktc_data"; ktc_then = ktc_then_date = ktc_now = None
    if sid:
        vt, dt = ktc_on(sid, slug, PRIMARY_FMT, date)
        vn, dn = ktc_on(sid, slug, PRIMARY_FMT, TODAY)
        if vt is not None or vn is not None:
            cov = "ok"; joined += 1
            ktc_then, ktc_then_date, ktc_now = vt, dt, vn
    rows_out.append({
        "trade_id": r["trade_id"], "trade_date": date, "player_name": name,
        "sleeper_id": sid or "", "ktc_slug": slug,
        "receiving_team": r["receiving_team"], "giving_team": r["giving_team"],
        "prod_value_at_trade": prod_then, "ktc_value_at_trade": ktc_then,
        "ktc_at_trade_used_date": ktc_then_date or "",
        "delta_at_trade": (None if (prod_then is None or ktc_then is None) else round(ktc_then - prod_then, 2)),
        "prod_value_current": prod_now, "ktc_value_current": ktc_now,
        "delta_current": (None if (prod_now is None or ktc_now is None) else round(ktc_now - prod_now, 2)),
        "ktc_coverage": cov,
    })

os.makedirs(OUT, exist_ok=True)
cols = ["trade_id","trade_date","player_name","sleeper_id","ktc_slug","receiving_team","giving_team",
        "prod_value_at_trade","ktc_value_at_trade","ktc_at_trade_used_date","delta_at_trade",
        "prod_value_current","ktc_value_current","delta_current","ktc_coverage"]
with open(os.path.join(OUT, "asset_value_comparison.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows_out)

# --- agreement stats ---
def pearson(xs, ys):
    n = len(xs)
    if n < 2: return None
    mx, my = sum(xs)/n, sum(ys)/n
    num = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    dx = (sum((x-mx)**2 for x in xs))**0.5; dy = (sum((y-my)**2 for y in ys))**0.5
    return None if dx == 0 or dy == 0 else round(num/(dx*dy), 4)

def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0]*len(v)
        for pos, i in enumerate(order): rk[i] = pos
        return rk
    return pearson(ranks(xs), ranks(ys))

for label, pk, kk in [("at_trade", "prod_value_at_trade", "ktc_value_at_trade"),
                      ("current", "prod_value_current", "ktc_value_current")]:
    pairs = [(r[pk], r[kk]) for r in rows_out if r[kk] is not None and r[pk] is not None]
    xs = [p for p, _ in pairs]; ys = [k for _, k in pairs]
    if pairs:
        deltas = [abs(k-p) for p, k in pairs]
        print(f"[{label}] n={len(pairs)} pearson={pearson(xs,ys)} spearman={spearman(xs,ys)} "
              f"MAD={round(statistics.mean(deltas),1)} medAD={round(statistics.median(deltas),1)}")

total = len(rows_out)
print(f"asset rows: {total}  joined_to_ktc: {joined} ({100*joined/total:.1f}%)  no_ktc_data: {total-joined}")
