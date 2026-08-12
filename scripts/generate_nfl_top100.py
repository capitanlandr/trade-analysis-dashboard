#!/usr/bin/env python3
"""Fetch the 2026 NFL Top 100 list and cross-reference it against fantasy rosters.

The 2026 NFL Top 100 is revealed one episode at a time (as of Aug 2026 only ranks
25-100 are public; ranks 1-24 roll out through early September). This script ingests
whatever ranks are currently revealed, marks the rest as pending, and cross-references
matched players against the league's fantasy rosters. It is idempotent and safe to run
daily from cron.

Sources (in order):
  1. PRIMARY  — Wikipedia MediaWiki API, page "NFL Top 100 Players of 2026" (prop=wikitext).
  2. FALLBACK — nfl.com official Top 100 landing page (best-effort HTML parse).

On failure or an unreachable/unparseable source, the last good JSON is preserved rather
than being overwritten with an empty/partial-error result.

Output: dashboard/frontend/public/nfl-top-100.json

Usage:
    python3 scripts/generate_nfl_top100.py
"""
import csv
import json
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent
OUT_PATH = REPO / "dashboard" / "frontend" / "public" / "nfl-top-100.json"
TEAMS_PATH = REPO / "dashboard" / "frontend" / "public" / "api-teams.json"
MY_PLAYERS_PATH = REPO / "data" / "ktc_history" / "my_players.json"
PLAYER_MAP_PATH = REPO / "data" / "ktc_history" / "player_map.csv"
# Active season (season_3, 2026) league — mirrors src/config/seasons.ts activeSeason.
ACTIVE_LEAGUE_ID = "1312166810505719808"
ROSTERS_PATH = REPO / "data" / "ktc_history" / "raw" / f"_sleeper_rosters_{ACTIVE_LEAGUE_ID}.json"

TOTAL_RANKS = 100
WIKI_PAGE = "NFL_Top_100_Players_of_2026"
WIKI_URL = (
    "https://en.wikipedia.org/w/api.php?action=parse"
    f"&page={WIKI_PAGE}&prop=wikitext&format=json&formatversion=2"
)
WIKI_HUMAN_URL = "https://en.wikipedia.org/wiki/NFL_Top_100_Players_of_2026"
NFL_URL = "https://www.nfl.com/news/nfl-top-100-players-of-2026"
USER_AGENT = "Mozilla/5.0 (dev-desk NFL-Top100 daily refresh; contact lndahayo)"


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Name normalization — mirror Sleeper's search_full_name convention
# ---------------------------------------------------------------------------
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def normalize_name(name: str) -> str:
    """'Ja'Marr Chase Jr.' -> 'jamarrchase'. Strips accents, punctuation, suffixes."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    # drop trailing generational suffix token(s)
    tokens = re.split(r"\s+", re.sub(r"[.\-']", " ", s).strip())
    while tokens and tokens[-1] in _SUFFIXES:
        tokens.pop()
    joined = "".join(tokens)
    return re.sub(r"[^a-z0-9]", "", joined)


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------
def _get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _strip_wiki_markup(cell: str) -> str:
    """Reduce a wikitext cell to plain text."""
    s = cell
    # [[Link|Display]] -> Display ; [[Link]] -> Link
    s = re.sub(r"\[\[(?:[^\|\]]*\|)?([^\]]+)\]\]", r"\1", s)
    # strip <ref>...</ref> and other tags
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.DOTALL)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    # templates like {{increase}} {{nowrap|..}} -> drop braces content best-effort
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = s.replace("'''", "").replace("''", "")
    return s.strip()


POSITION_MAP = {
    "quarterback": "QB", "running back": "RB", "wide receiver": "WR",
    "tight end": "TE", "cornerback": "CB", "linebacker": "LB",
    "defensive end": "DE", "defensive tackle": "DT", "safety": "S",
    "offensive tackle": "OT", "guard": "G", "center": "C",
    "edge": "EDGE", "fullback": "FB", "kicker": "K", "punter": "P",
    "place kicker": "K", "outside linebacker": "LB",
    "free safety": "S", "strong safety": "S", "nose tackle": "DT",
}


def _norm_pos(pos: str) -> str:
    p = pos.strip().lower()
    return POSITION_MAP.get(p, pos.strip())


def parse_wikitext(wikitext: str):
    """Parse the 'Top 100 Players' sortable table into rows {rank,name,position,nflTeam}."""
    # The players table is the wikitable with a "Rank" header and "Player" column.
    tables = re.findall(r"\{\|[^\n]*\n(.*?)\n\|\}", wikitext, flags=re.DOTALL)
    target = None
    for t in tables:
        header = t[:400]
        if "!Rank" in header and "!Player" in header:
            target = t
            break
    if target is None:
        raise ValueError("Could not locate 'Top 100 Players' table in wikitext")

    # Rows are separated by |- ; the first chunk is the header.
    chunks = re.split(r"\n\|-", target)
    players = []
    for chunk in chunks:
        # cells begin with a leading | ; the header chunk uses ! so it is skipped.
        # collect leading-pipe cells (each starts at line beginning with '|')
        cells = []
        for m in re.finditer(r"(?m)^\|(.*(?:\n(?![|!]).*)*)", chunk):
            cells.append(m.group(1))
        if len(cells) < 3:
            continue
        rank_raw = _strip_wiki_markup(re.sub(r"^.*?\|", "", cells[0]) if "|" in cells[0] and cells[0].strip().startswith("rowspan") else cells[0])
        rank_txt = rank_raw.strip()
        if not re.match(r"^\d+$", rank_txt):
            continue
        rank = int(rank_txt)
        if not (1 <= rank <= TOTAL_RANKS):
            continue
        name = _strip_wiki_markup(cells[1])
        position = _norm_pos(_strip_wiki_markup(cells[2]))
        # NFL team: prefer 2026 team (cells[4]); handle colspan merged cell (cells[3]).
        nfl_team = ""
        # detect colspan="2" on the team cell -> single merged team applies to both years
        team_cells = cells[3:5] if len(cells) >= 5 else cells[3:4]
        # If cells[3] carried a colspan attr, its value is the team for both years.
        c3 = cells[3] if len(cells) > 3 else ""
        if "colspan" in c3.lower():
            nfl_team = _strip_wiki_markup(re.sub(r"^[^|]*\|", "", c3, count=1))
        elif len(cells) >= 5:
            nfl_team = _strip_wiki_markup(cells[4]) or _strip_wiki_markup(cells[3])
        elif len(cells) >= 4:
            nfl_team = _strip_wiki_markup(cells[3])
        if not name:
            continue
        players.append({
            "rank": rank,
            "name": name,
            "position": position,
            "nflTeam": nfl_team,
        })
    # dedupe by rank (keep first), sort by rank
    seen = {}
    for p in players:
        seen.setdefault(p["rank"], p)
    return [seen[k] for k in sorted(seen)]


def fetch_wikipedia():
    log(f"Fetching PRIMARY source (Wikipedia MediaWiki API): {WIKI_URL}")
    raw = _get(WIKI_URL)
    data = json.loads(raw)
    wikitext = data["parse"]["wikitext"]
    players = parse_wikitext(wikitext)
    if not players:
        raise ValueError("Wikipedia parse yielded 0 players")
    return players, "wikipedia", WIKI_HUMAN_URL


def fetch_nfl():
    log(f"Fetching FALLBACK source (NFL.com): {NFL_URL}")
    html = _get(NFL_URL)
    # Best-effort: NFL.com renders entries like "No. 25\n...Player Name" — very brittle.
    # We only extract rank/name pairs; position/team left blank when unknown.
    players = []
    for m in re.finditer(r"(?:No\.?\s*)(\d{1,3})[^A-Za-z]{0,40}?([A-Z][a-zA-Z.'\-]+(?:\s+[A-Z][a-zA-Z.'\-]+){1,3})", html):
        rank = int(m.group(1))
        if 1 <= rank <= TOTAL_RANKS:
            players.append({"rank": rank, "name": m.group(2).strip(),
                            "position": "", "nflTeam": ""})
    seen = {}
    for p in players:
        seen.setdefault(p["rank"], p)
    out = [seen[k] for k in sorted(seen)]
    if not out:
        raise ValueError("NFL.com parse yielded 0 players")
    return out, "nfl.com", NFL_URL


# ---------------------------------------------------------------------------
# Roster cross-reference
# ---------------------------------------------------------------------------
SLEEPER_API = "https://api.sleeper.app/v1"


def _fetch_json(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def load_my_players():
    """sleeper_id -> {name, position, team, search_full_name}.

    Prefers the local cache (fast, offline); falls back to the Sleeper master
    player list so this runs in CI where data/ is not committed.
    """
    if MY_PLAYERS_PATH.exists():
        players = json.loads(MY_PLAYERS_PATH.read_text())
        return {p["sleeper_id"]: p for p in players}

    log("my_players.json not found locally — fetching Sleeper master player list (CI fallback).")
    master = _fetch_json(f"{SLEEPER_API}/players/nfl")
    by_id = {}
    for pid, p in master.items():
        if not isinstance(p, dict):
            continue
        name = p.get("full_name") or " ".join(
            x for x in [p.get("first_name"), p.get("last_name")] if x
        ).strip()
        if not name:
            continue
        by_id[str(pid)] = {
            "sleeper_id": str(pid),
            "name": name,
            "position": p.get("position") or "",
            "team": p.get("team") or "",
            "search_full_name": p.get("search_full_name") or normalize_name(name),
        }
    return by_id


def load_rosters():
    """List of roster dicts for the active league (local cache, else Sleeper API)."""
    if ROSTERS_PATH.exists():
        return json.loads(ROSTERS_PATH.read_text())
    log(f"Roster cache not found — fetching Sleeper rosters for league {ACTIVE_LEAGUE_ID} (CI fallback).")
    return _fetch_json(f"{SLEEPER_API}/league/{ACTIVE_LEAGUE_ID}/rosters")


def load_teams():
    """rosterId -> team dict {teamName, realName/nickname}.

    Prefers the committed api-teams.json; if absent, derives team/manager names
    from the Sleeper league users + rosters so CI still produces labels.
    """
    if TEAMS_PATH.exists():
        return json.loads(TEAMS_PATH.read_text())["data"]["teams"]

    log("api-teams.json not found — deriving team labels from Sleeper users (CI fallback).")
    users = _fetch_json(f"{SLEEPER_API}/league/{ACTIVE_LEAGUE_ID}/users")
    rosters = _fetch_json(f"{SLEEPER_API}/league/{ACTIVE_LEAGUE_ID}/rosters")
    owner_to_user = {u["user_id"]: u for u in users}
    teams = []
    for r in rosters:
        u = owner_to_user.get(r.get("owner_id"), {})
        meta = u.get("metadata") or {}
        team_name = meta.get("team_name") or u.get("display_name") or f"Roster {r['roster_id']}"
        teams.append({
            "rosterId": r["roster_id"],
            "teamName": team_name,
            "realName": u.get("display_name") or "",
            "nickname": u.get("display_name") or "",
        })
    return teams


def load_roster_index():
    """Return (norm_name -> {name, position, team}) and (norm_name -> rosterId)."""
    by_id = load_my_players()

    rosters = load_rosters()
    # sleeper_id -> roster_id (active league)
    pid_to_roster = {}
    for r in rosters:
        rid = r["roster_id"]
        for pid in (r.get("players") or []):
            pid_to_roster[str(pid)] = rid

    teams = load_teams()
    roster_to_team = {t["rosterId"]: t for t in teams}

    # norm_name -> (rosterId, teamName, manager)  using players actually rostered
    norm_to_fantasy = {}
    for pid, rid in pid_to_roster.items():
        p = by_id.get(pid)
        if not p:
            continue
        team = roster_to_team.get(rid)
        if not team:
            continue
        key = p.get("search_full_name") or normalize_name(p["name"])
        norm_to_fantasy[key] = {
            "rosterId": rid,
            "fantasyTeam": team["teamName"],
            "manager": team.get("realName") or team.get("nickname") or "",
            "sleeperName": p["name"],
            "position": p.get("position", ""),
            "nflTeam": p.get("team", ""),
        }
        norm_to_fantasy.setdefault(normalize_name(p["name"]), norm_to_fantasy[key])
    return norm_to_fantasy, roster_to_team


def cross_reference(players, norm_to_fantasy, roster_to_team):
    matched = []
    unmatched = []
    for p in players:
        key = normalize_name(p["name"])
        fant = norm_to_fantasy.get(key)
        if fant:
            matched.append({
                "rank": p["rank"],
                "name": p["name"],
                "position": p["position"] or fant["position"],
                "nflTeam": p["nflTeam"] or fant["nflTeam"],
                "fantasyTeam": fant["fantasyTeam"],
                "manager": fant["manager"],
                "rosterId": fant["rosterId"],
            })
        else:
            unmatched.append({
                "rank": p["rank"],
                "name": p["name"],
                "position": p["position"],
                "nflTeam": p["nflTeam"],
                "reason": "not on any fantasy roster (free agent / undrafted in this league)",
            })
    matched.sort(key=lambda x: x["rank"])
    unmatched.sort(key=lambda x: x["rank"])

    # per-fantasy-team counts of Top-100 players
    counts = {}
    for m in matched:
        rid = m["rosterId"]
        counts.setdefault(rid, 0)
        counts[rid] += 1
    team_counts = []
    for rid, team in roster_to_team.items():
        team_counts.append({
            "rosterId": rid,
            "fantasyTeam": team["teamName"],
            "manager": team.get("realName") or team.get("nickname") or "",
            "top100Count": counts.get(rid, 0),
        })
    team_counts.sort(key=lambda x: (-x["top100Count"], x["fantasyTeam"]))
    return matched, unmatched, team_counts


def build_payload(players, source, source_url):
    revealed_ranks = sorted(p["rank"] for p in players)
    revealed_set = set(revealed_ranks)
    pending_ranks = [r for r in range(1, TOTAL_RANKS + 1) if r not in revealed_set]

    norm_to_fantasy, roster_to_team = load_roster_index()
    matched, unmatched, team_counts = cross_reference(players, norm_to_fantasy, roster_to_team)

    now = datetime.now(timezone.utc).astimezone()
    return {
        "title": "NFL Top 100 Players of 2026",
        "subtitle": "Top-100 players cross-referenced against league fantasy rosters",
        "generatedAt": now.isoformat(),
        "source": source,
        "sourceUrl": source_url,
        "totalRanks": TOTAL_RANKS,
        "revealedCount": len(revealed_ranks),
        "pendingCount": len(pending_ranks),
        "revealedRanks": revealed_ranks,
        "pendingRanks": pending_ranks,
        "leagueId": ACTIVE_LEAGUE_ID,
        "players": players,           # all revealed Top-100 players (rank,name,position,nflTeam)
        "rostered": matched,          # Top-100 players on a fantasy team
        "unmatched": unmatched,       # revealed Top-100 players NOT on any fantasy roster (flagged)
        "teamCounts": team_counts,    # per-fantasy-team Top-100 counts
        "rosteredCount": len(matched),
        "unmatchedCount": len(unmatched),
    }


def main() -> int:
    log("=== NFL Top 100 refresh starting ===")
    players = None
    source = source_url = None
    errors = []
    for fetcher in (fetch_wikipedia, fetch_nfl):
        try:
            players, source, source_url = fetcher()
            log(f"Source OK: {source} — parsed {len(players)} revealed players")
            break
        except Exception as e:  # noqa: BLE001 — we want to try the fallback
            errors.append(f"{fetcher.__name__}: {type(e).__name__}: {e}")
            log(f"Source FAILED — {fetcher.__name__}: {type(e).__name__}: {e}")

    if not players:
        log("ALL SOURCES FAILED. Preserving last good JSON (no overwrite).")
        log("Errors: " + " | ".join(errors))
        if OUT_PATH.exists():
            log(f"Kept existing {OUT_PATH} ({OUT_PATH.stat().st_size} bytes).")
            return 0
        log("No prior JSON exists; nothing written. Exiting non-zero.")
        return 1

    payload = build_payload(players, source, source_url)

    revealed = payload["revealedCount"]
    pending = payload["pendingCount"]
    log(f"Revealed ranks: {revealed}/{TOTAL_RANKS} ; pending (not yet revealed): {pending}")
    log(f"Rostered Top-100 players: {payload['rosteredCount']} ; unmatched (flagged): {payload['unmatchedCount']}")

    # Atomic-ish write: write to temp then replace, so a crash mid-write can't corrupt.
    tmp = OUT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    tmp.replace(OUT_PATH)
    log(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes) from source '{source}' ({source_url}).")
    log("=== NFL Top 100 refresh complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
