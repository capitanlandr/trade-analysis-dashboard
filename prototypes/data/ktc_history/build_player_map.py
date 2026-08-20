#!/usr/bin/env python3
"""Resolve my players (Sleeper rosters) -> KTC slugs.

Read-only. Reads:
  data/ktc_history/my_players.json     (my players)
  data/ktc_history/ktc_catalog.json    (KTC 500-player catalog w/ slug+playerID)
  data/ktc_history/manual_overrides.csv (name-variant / hard misses)
Writes:
  data/ktc_history/player_map.csv
  data/ktc_history/_unresolved.json
"""
import json, re, csv, unicodedata, os
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))

def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.'`]", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def main():
    mine = json.load(open(os.path.join(HERE, "my_players.json")))
    cat = json.load(open(os.path.join(HERE, "ktc_catalog.json")))

    overrides = {}
    ov_path = os.path.join(HERE, "manual_overrides.csv")
    if os.path.exists(ov_path):
        for row in csv.DictReader(open(ov_path)):
            overrides[str(row["sleeper_id"])] = row

    by_name, by_name_pos = {}, {}
    for c in cat:
        n = norm(c["playerName"]); p = c.get("position")
        by_name.setdefault(n, []).append(c)
        by_name_pos.setdefault((n, p), []).append(c)

    rows, resolved, unresolved = [], 0, []
    for m in mine:
        sid = str(m["sleeper_id"]); nm = norm(m["name"]); pos = m.get("position")
        match = None; method = None; score = 1.0
        if sid in overrides and overrides[sid].get("ktc_slug"):
            o = overrides[sid]
            match = {"slug": o["ktc_slug"], "playerID": o.get("ktc_playerID", ""), "playerName": o.get("ktc_name", "")}
            method = "manual_override"
        elif (nm, pos) in by_name_pos and len(by_name_pos[(nm, pos)]) == 1:
            match = by_name_pos[(nm, pos)][0]; method = "exact_name_pos"
        elif nm in by_name and len(by_name[nm]) == 1:
            match = by_name[nm][0]; method = "exact_name"
        elif (nm, pos) in by_name_pos:
            match = by_name_pos[(nm, pos)][0]; method = "exact_name_pos_multi"
        else:
            best = None; bs = 0
            for c in cat:
                if c.get("position") != pos:
                    continue
                r = SequenceMatcher(None, nm, norm(c["playerName"])).ratio()
                if r > bs:
                    bs = r; best = c
            if best and bs >= 0.88:
                match = best; method = "fuzzy_pos"; score = round(bs, 3)

        if match:
            resolved += 1
            rows.append({"sleeper_id": sid, "my_name": m["name"], "position": pos, "team": m.get("team"),
                         "ktc_slug": match["slug"], "ktc_playerID": match.get("playerID", ""),
                         "ktc_name": match.get("playerName", ""), "match_method": method, "match_score": score})
        else:
            unresolved.append(m)
            rows.append({"sleeper_id": sid, "my_name": m["name"], "position": pos, "team": m.get("team"),
                         "ktc_slug": "", "ktc_playerID": "", "ktc_name": "", "match_method": "UNRESOLVED", "match_score": 0})

    with open(os.path.join(HERE, "player_map.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sleeper_id", "my_name", "position", "team", "ktc_slug",
                                          "ktc_playerID", "ktc_name", "match_method", "match_score"])
        w.writeheader(); w.writerows(rows)
    json.dump(unresolved, open(os.path.join(HERE, "_unresolved.json"), "w"), indent=2)

    from collections import Counter
    print(f"RESOLVED {resolved} / {len(mine)}  ({100*resolved/len(mine):.1f}%)")
    print("by method:", dict(Counter(r["match_method"] for r in rows)))
    print(f"UNRESOLVED {len(unresolved)}:")
    for u in unresolved:
        print(f"  - {u['name']} ({u['position']}, {u.get('team')})  sleeper={u['sleeper_id']}")

if __name__ == "__main__":
    main()
