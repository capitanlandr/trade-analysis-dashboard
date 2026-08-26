#!/usr/bin/env python3
"""
Fetch Season 1 (2024, league Dynasuiiii) raw Sleeper data for the
Dynasty-Value-Over-Time reconstruction, plus drafts for all three seasons
(needed for pick->rookie conversion in the back-cast step).

Polite: small sleeps between calls, single pass, writes a self-contained
JSON dump. Only SLEEPER data is fetched here (KTC history is already on disk).

Chain (verified live 2026-08-25):
  Season 1 (2024): 1101631897148493824  previous_league_id=None  <- true origin
  Season 2 (2025): 1180814327660371968
  Season 3 (2026): 1312166810505719808  (active)
"""
import json, time, urllib.request, os

BASE = "https://api.sleeper.app/v1"
OUT = os.path.join(os.path.dirname(__file__), "season1_sleeper_raw.json")

LEAGUES = {
    "season_1": "1101631897148493824",
    "season_2": "1180814327660371968",
    "season_3": "1312166810505719808",
}


def get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    print(f"  WARN failed {url}: {last}")
    return None


def fetch_league_bundle(name, lid, fetch_txns):
    print(f"== {name} {lid} ==")
    league = get(f"{BASE}/league/{lid}")
    time.sleep(0.4)
    users = get(f"{BASE}/league/{lid}/users") or []
    time.sleep(0.4)
    rosters = get(f"{BASE}/league/{lid}/rosters") or []
    time.sleep(0.4)
    traded_picks = get(f"{BASE}/league/{lid}/traded_picks") or []
    time.sleep(0.4)
    drafts = get(f"{BASE}/league/{lid}/drafts") or []
    time.sleep(0.4)
    draft_details = []
    for d in drafts:
        did = d.get("draft_id")
        det = get(f"{BASE}/draft/{did}")
        time.sleep(0.3)
        picks = get(f"{BASE}/draft/{did}/picks") or []
        time.sleep(0.3)
        traded = get(f"{BASE}/draft/{did}/traded_picks") or []
        time.sleep(0.3)
        draft_details.append({"meta": d, "detail": det, "picks": picks, "traded_picks": traded})
    txns = {}
    if fetch_txns:
        for wk in range(1, 19):
            t = get(f"{BASE}/league/{lid}/transactions/{wk}")
            time.sleep(0.25)
            txns[str(wk)] = t or []
        n = sum(len(v) for v in txns.values())
        print(f"  transactions weeks 1-18: {n} total")
    print(f"  users={len(users)} rosters={len(rosters)} traded_picks={len(traded_picks)} drafts={len(drafts)}")
    return {
        "league": league,
        "users": users,
        "rosters": rosters,
        "traded_picks": traded_picks,
        "drafts": draft_details,
        "transactions": txns,
    }


def main():
    out = {"fetched_utc": None, "leagues": {}}
    # Season 1 needs full transactions. Seasons 2/3 we only need drafts here
    # (their transactions are already cached in the pipeline spine).
    # Fetch full transactions for ALL seasons so the holdings ledger cannot
    # drift on any partial local cache. Only Sleeper data (KTC is on disk).
    out["leagues"]["season_1"] = fetch_league_bundle("season_1", LEAGUES["season_1"], fetch_txns=True)
    out["leagues"]["season_2"] = fetch_league_bundle("season_2", LEAGUES["season_2"], fetch_txns=True)
    out["leagues"]["season_3"] = fetch_league_bundle("season_3", LEAGUES["season_3"], fetch_txns=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
