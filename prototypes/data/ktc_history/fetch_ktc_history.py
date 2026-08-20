#!/usr/bin/env python3
"""Fetch KTC per-player historical value series (method 2a: embedded JSON).

Read-only against KTC. Polite: single-threaded, randomized delay, normal UA,
raw responses cached (gzipped) so re-runs never re-hit the site, back off on 429/403.

Reads:  data/ktc_history/player_map.csv (resolved rows only)
Writes: data/ktc_history/raw/players/<slug>.html.gz   (raw cache)
        data/ktc_history/ktc_history.csv               (tidy: player_name,sleeper_id,ktc_slug,format,date,value)
        data/ktc_history/_fetch_log.json               (per-player status)
"""
import json, csv, os, re, gzip, time, random, sys
import urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAWDIR = os.path.join(HERE, "raw", "players")
os.makedirs(RAWDIR, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def extract_obj(html, varname):
    m = re.search(r"var\s+%s\s*=\s*\{" % varname, html)
    if not m:
        return None
    i = m.end() - 1
    depth = 0; instr = False; esc = False
    for j in range(i, len(html)):
        c = html[j]
        if esc: esc = False; continue
        if c == '\\': esc = True; continue
        if c == '"': instr = not instr; continue
        if instr: continue
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return html[i:j + 1]
    return None

def yymmdd_to_iso(d):
    d = str(d)
    if len(d) != 6:
        return None
    return f"20{d[0:2]}-{d[2:4]}-{d[4:6]}"

def get_html(slug):
    """Return raw HTML, using gzip cache if present."""
    cache = os.path.join(RAWDIR, slug + ".html.gz")
    if os.path.exists(cache) and os.path.getsize(cache) > 1000:
        with gzip.open(cache, "rt", encoding="utf-8", errors="replace") as f:
            return f.read(), True, 200
    url = f"https://keeptradecut.com/dynasty-rankings/players/{slug}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read().decode("utf-8", "replace"); code = r.status
    except urllib.error.HTTPError as e:
        return None, False, e.code
    with gzip.open(cache, "wt", encoding="utf-8") as f:
        f.write(data)
    return data, False, code

def parse_series(html):
    """Return {'1QB': [(iso,val)...], 'SF': [...]}."""
    out = {}
    for fmt, var in [("1QB", "playerOneQB"), ("SF", "playerSuperflex")]:
        s = extract_obj(html, var)
        if not s:
            out[fmt] = []
            continue
        try:
            obj = json.loads(s)
        except Exception:
            out[fmt] = []
            continue
        ov = obj.get("overallValue") or []
        pts = []
        for p in ov:
            iso = yymmdd_to_iso(p.get("d"))
            v = p.get("v")
            if iso is not None and isinstance(v, (int, float)):
                pts.append((iso, int(v)))
        out[fmt] = pts
    return out

def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "player_map.csv"))))
    resolved = [r for r in rows if r.get("ktc_slug")]
    print(f"resolved players to fetch: {len(resolved)}")

    out_csv = os.path.join(HERE, "ktc_history.csv")
    fetch_log = {}
    n_new = 0
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["player_name", "sleeper_id", "ktc_slug", "format", "date", "value"])
        for idx, r in enumerate(resolved, 1):
            slug = r["ktc_slug"]; name = r["my_name"]; sid = r["sleeper_id"]
            try:
                html, cached, code = get_html(slug)
            except Exception as e:
                print(f"[{idx}/{len(resolved)}] {slug} ERROR {e}")
                fetch_log[slug] = {"status": "error", "detail": str(e)}
                continue
            if code in (429, 403):
                print(f"[{idx}] HTTP {code} on {slug} — backing off 60s then retry once")
                time.sleep(60)
                html, cached, code = get_html(slug)
            if not html or code != 200:
                print(f"[{idx}/{len(resolved)}] {slug} HTTP {code} — skip")
                fetch_log[slug] = {"status": f"http_{code}"}
                continue
            series = parse_series(html)
            rc = 0
            for fmt in ("1QB", "SF"):
                for iso, val in series[fmt]:
                    w.writerow([name, sid, slug, fmt, iso, val])
                    rc += 1
            fetch_log[slug] = {"status": "ok", "cached": cached,
                               "n_1qb": len(series["1QB"]), "n_sf": len(series["SF"])}
            if not cached:
                n_new += 1
                time.sleep(random.uniform(1.5, 3.0))
            if idx % 25 == 0 or cached is False:
                print(f"[{idx}/{len(resolved)}] {slug}: 1QB={len(series['1QB'])} SF={len(series['SF'])} (cached={cached}) rows={rc}")
    json.dump(fetch_log, open(os.path.join(HERE, "_fetch_log.json"), "w"), indent=2)
    ok = sum(1 for v in fetch_log.values() if v.get("status") == "ok")
    print(f"DONE. players ok={ok}/{len(resolved)}  newly fetched (non-cached)={n_new}")

if __name__ == "__main__":
    main()
