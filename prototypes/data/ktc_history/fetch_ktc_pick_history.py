#!/usr/bin/env python3
"""Fetch KTC per-PICK historical value series (Early/Mid/Late x 1st-4th, 2026-2028).

Reuses the player fetcher's extraction (KTC pick pages live at the same
/dynasty-rankings/players/<slug> URL and embed the same playerSuperflex.overallValue
series). Read-only, polite, gzip-cached.

Reads:  data/ktc_history/ktc_catalog.json  (pick entries: name/slug/id)
Writes: data/ktc_history/ktc_pick_history.csv  (pick_name, slug, format, date, value)
"""
import json, csv, os, re, time, random
import fetch_ktc_history as fh   # reuse get_html / parse_series / extract_obj

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "ktc_catalog.json")
OUT = os.path.join(HERE, "ktc_pick_history.csv")

PICK_RE = re.compile(r"^\d{4}\s+(Early|Mid|Late)\s+(1st|2nd|3rd|4th)$")


def find_picks(o, acc):
    if isinstance(o, dict):
        name = o.get("playerName") or o.get("name")
        slug = o.get("slug") or o.get("ktc_slug")
        if name and slug and PICK_RE.match(str(name).strip()):
            acc[str(name).strip()] = slug
        for v in o.values():
            find_picks(v, acc)
    elif isinstance(o, list):
        for v in o:
            find_picks(v, acc)


def main():
    cat = json.load(open(CATALOG))
    picks = {}
    find_picks(cat, picks)
    print(f"pick tiers found in catalog: {len(picks)}")
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pick_name", "slug", "format", "date", "value"])
        ok = 0
        for i, (name, slug) in enumerate(sorted(picks.items()), 1):
            try:
                html, cached, code = fh.get_html(slug)
            except Exception as e:
                print(f"[{i}/{len(picks)}] {slug} ERROR {e}"); continue
            if code in (429, 403):
                time.sleep(60); html, cached, code = fh.get_html(slug)
            if not html or code != 200:
                print(f"[{i}/{len(picks)}] {name} HTTP {code} skip"); continue
            series = fh.parse_series(html)
            rc = 0
            for fmt in ("1QB", "SF"):
                for iso, val in series[fmt]:
                    w.writerow([name, slug, fmt, iso, val]); rc += 1
            cur = series["SF"][-1][1] if series["SF"] else "?"
            print(f"[{i}/{len(picks)}] {name:16} SF pts={len(series['SF']):4} current={cur} (cached={cached})")
            ok += 1
            if not cached:
                time.sleep(random.uniform(1.5, 3.0))
    print(f"DONE. picks ok={ok}/{len(picks)} -> {OUT}")


if __name__ == "__main__":
    main()
