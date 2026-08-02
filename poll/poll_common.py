"""Shared plumbing for the preseason poll scripts.

Holds the three things create_form.py and fetch_responses.py both need:
OAuth credentials, the league roster loaded from source of truth, and the
canonical question keys.

League data is read from files already in the repo rather than hardcoded, so
a team rename or a division shuffle only has to be fixed in one place:
  team_identity_mapping.csv  -> roster_id, manager name, current team name
  pipeline/standings_data.json -> division names and membership
"""

import csv
import json
import os
import pathlib

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

POLL_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = POLL_DIR.parent

IDENTITY_CSV = REPO_ROOT / "team_identity_mapping.csv"
STANDINGS_JSON = REPO_ROOT / "pipeline" / "standings_data.json"

# The OAuth client is shared with the Gmail tooling one directory up. Reused
# deliberately: a second client would mean a second consent screen to maintain.
CLIENT_SECRETS = REPO_ROOT.parent / "credentials.json"

# Separate token file from the Gmail token.pickle. Different scopes, and mixing
# them would force a re-consent every time either script ran.
TOKEN_FILE = POLL_DIR / "token.json"

FORM_METADATA = POLL_DIR / "form_metadata.json"
PREFILL_CSV = POLL_DIR / "prefill_links.csv"

# Where the dashboard reads its static JSON from.
PUBLIC_DATA = REPO_ROOT / "dashboard" / "frontend" / "public"
POLL_OUTPUT = PUBLIC_DATA / "api-preseason-poll.json"
RESPONSES_RAW = POLL_DIR / "responses_raw.json"

# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------

# forms.body      -> create the form and add questions (create_form.py)
# responses.readonly -> read submissions (fetch_responses.py)
# Both scripts request both scopes so one consent covers both and the token
# does not have to be regenerated when switching between them.
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
]


def get_credentials():
    """Return authorized credentials, running the consent flow if needed.

    Opens a browser on first run and caches the result in poll/token.json.
    Refreshes silently after that.
    """
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
            return creds
        except Exception as exc:  # refresh token revoked or scopes changed
            print(f"  Token refresh failed ({exc}); re-running consent flow.")

    if not CLIENT_SECRETS.exists():
        raise SystemExit(
            f"OAuth client secrets not found at {CLIENT_SECRETS}\n"
            "Download the desktop client JSON from the Google Cloud console."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json())
    os.chmod(TOKEN_FILE, 0o600)
    print(f"  Token saved to {TOKEN_FILE}")
    return creds


# ---------------------------------------------------------------------------
# League data
# ---------------------------------------------------------------------------


def load_managers():
    """Return [{roster_id, manager, team, label}] ordered by roster_id.

    `label` is the exact string used as a Google Forms choice value and as the
    key in every stored result. Parentheses rather than a dash separator so the
    string survives copy/paste and CSV round-trips without ambiguity.
    """
    managers = []
    with IDENTITY_CSV.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            manager = row["nickname"].strip() or row["real_name"].strip()
            team = row["current_team_name"].strip()
            managers.append(
                {
                    "roster_id": int(row["roster_id"]),
                    "sleeper_username": row["sleeper_username"].strip(),
                    "manager": manager,
                    "team": team,
                    "label": f"{manager} ({team})",
                }
            )

    managers.sort(key=lambda m: m["roster_id"])
    if len(managers) != 12:
        raise SystemExit(f"Expected 12 managers in {IDENTITY_CSV}, found {len(managers)}")
    return managers


def load_divisions(managers):
    """Return [{division_id, division_name, roster_ids, labels}].

    Division membership comes from the pipeline's standings output, which is
    generated from the Sleeper API, so it reflects the real league setup.
    """
    by_roster = {m["roster_id"]: m for m in managers}

    with STANDINGS_JSON.open(encoding="utf-8") as fh:
        standings = json.load(fh)

    divisions = []
    for div in standings["divisions"]:
        roster_ids = [t["roster_id"] for t in div["teams"]]
        missing = [r for r in roster_ids if r not in by_roster]
        if missing:
            raise SystemExit(
                f"Division {div['division_name']} references unknown roster_id(s) {missing}. "
                f"Reconcile {IDENTITY_CSV.name} with {STANDINGS_JSON.name}."
            )
        divisions.append(
            {
                "division_id": div["division_id"],
                "division_name": div["division_name"],
                "roster_ids": roster_ids,
                "labels": [by_roster[r]["label"] for r in roster_ids],
            }
        )

    divisions.sort(key=lambda d: d["division_id"])
    covered = sorted(r for d in divisions for r in d["roster_ids"])
    if covered != sorted(by_roster):
        raise SystemExit("Divisions do not cover all 12 rosters exactly once.")
    return divisions


# ---------------------------------------------------------------------------
# Question keys
# ---------------------------------------------------------------------------

# Stable identifiers used in form_metadata.json and in the published results
# JSON. Google's own questionId values are assigned at creation time and would
# change if the form were ever rebuilt, so results are keyed on these instead.
Q_IDENTITY = "identity"
Q_SELF_FINISH = "self_finish"
Q_SELF_TIER = "self_tier"
Q_CONTENDERS = "contenders"
Q_CHAMPION = "champion"
Q_TOILET_BOWL = "toilet_bowl"
Q_BOLD_PREDICTION = "bold_prediction"


def division_key(division_id):
    return f"division_winner_{division_id}"


FINISH_OPTIONS = [
    "1st", "2nd", "3rd", "4th", "5th", "6th",
    "7th", "8th", "9th", "10th", "11th", "12th",
]

TIER_OPTIONS = [
    "Title favorite",
    "Contender",
    "Playoff team",
    "Fringe playoff team",
    "Rebuilding",
    "Full teardown",
]

CONTENDERS_PICK_COUNT = 4


def load_form_metadata():
    if not FORM_METADATA.exists():
        raise SystemExit(
            f"{FORM_METADATA} not found. Run create_form.py first."
        )
    with FORM_METADATA.open(encoding="utf-8") as fh:
        return json.load(fh)
