#!/usr/bin/env python3
"""Create the preseason poll Google Form via the Forms API.

Builds the whole form programmatically: title, description, and every question
with its choices generated from team_identity_mapping.csv and the league's real
division structure. Nothing is hand-built in the Forms UI, so a team rename is
a CSV edit plus a re-run rather than twelve dropdown edits.

Usage:
    poll/.venv/bin/python poll/create_form.py            # create
    poll/.venv/bin/python poll/create_form.py --dry-run  # print the plan only

Writes poll/form_metadata.json (form id, URLs, questionId -> key map) and
poll/prefill_links.csv (one pre-filled link per manager).

Re-running creates a SECOND form. It refuses to overwrite existing metadata
unless --force is passed, because the old form id is the only handle on
already-collected responses.
"""

import argparse
import csv
import json
import sys
import urllib.parse

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import poll_common as pc

SEASON = 2026

FORM_TITLE = f"Dynasuiiii {SEASON} Preseason Poll"
FORM_DOCUMENT_TITLE = f"Dynasuiiii {SEASON} Preseason Poll"

FORM_DESCRIPTION = (
    "Our version of the NFLPA Top 100: the league voting on the league, before "
    "a single snap. Answer honestly, results get published on the dashboard "
    "with everyone's picks attributed.\n\n"
    "Your name is pre-selected if you opened this from your personal link. "
    "Leave it as is.\n\n"
    "You can resubmit to change your picks. Only your most recent submission "
    "counts, and resubmitting starts from a blank form, so re-answer everything."
)


def build_requests(managers, divisions):
    """Return (batchUpdate requests, ordered list of question keys).

    Index order matters: each createItem specifies its own location index, so
    the questions are inserted in exactly this sequence.
    """
    all_labels = [m["label"] for m in managers]
    requests = []
    keys = []
    index = 0

    def add_item(key, item):
        nonlocal index
        requests.append({"createItem": {"item": item, "location": {"index": index}}})
        keys.append(key)
        index += 1

    def question_item(title, description, question):
        item = {"title": title, "questionItem": {"question": question}}
        if description:
            item["description"] = description
        return item

    def choice_question(options, choice_type="RADIO", required=True, shuffle=False):
        return {
            "required": required,
            "choiceQuestion": {
                "type": choice_type,
                "options": [{"value": v} for v in options],
                "shuffle": shuffle,
            },
        }

    # --- Identity -----------------------------------------------------------
    # First and required. Every downstream aggregation keys on this, and it is
    # the reason no email address needs collecting: the dropdown IS the identity.
    add_item(
        pc.Q_IDENTITY,
        question_item(
            "Who are you?",
            "Pre-selected from your personal link. Do not change it.",
            choice_question(all_labels, choice_type="DROP_DOWN"),
        ),
    )

    # --- Self assessment ----------------------------------------------------
    add_item(
        pc.Q_SELF_FINISH,
        question_item(
            "Where do you finish in the standings?",
            "Regular season finish, 1st through 12th. Be honest.",
            choice_question(pc.FINISH_OPTIONS, choice_type="DROP_DOWN"),
        ),
    )

    add_item(
        pc.Q_SELF_TIER,
        question_item(
            "How would you describe your own team going into the season?",
            None,
            choice_question(pc.TIER_OPTIONS),
        ),
    )

    # --- League-wide ---------------------------------------------------------
    # Checkbox, so a voter can name several contenders.
    #
    # The pick count is NOT enforced here. Forms API v1 exposes no response
    # validation for choice questions (ChoiceQuestion carries only type,
    # options and shuffle), so a "select exactly N" rule can only be added by
    # hand in the form editor. The ask is therefore stated in the title, and
    # aggregate_responses.py weights each ballot by 1/len(picks) so an
    # eight-team ballot cannot outvote a four-team one regardless.
    add_item(
        pc.Q_CONTENDERS,
        question_item(
            f"Who are the real contenders? Pick {pc.CONTENDERS_PICK_COUNT}.",
            "Teams that can actually win it all this year. You may include yourself.",
            choice_question(all_labels, choice_type="CHECKBOX"),
        ),
    )

    add_item(
        pc.Q_CHAMPION,
        question_item(
            "Who wins the league?",
            "One team. This is the headline number.",
            choice_question(all_labels, choice_type="DROP_DOWN"),
        ),
    )

    # --- Division winners ---------------------------------------------------
    # One question per division, choices limited to that division's four teams.
    # Limiting the options prevents impossible ballots outright rather than
    # discarding them at aggregation time.
    for div in divisions:
        add_item(
            pc.division_key(div["division_id"]),
            question_item(
                f"Who wins the {div['division_name']} division?",
                ", ".join(div["labels"]),
                choice_question(div["labels"], choice_type="DROP_DOWN"),
            ),
        )

    # --- Toilet bowl --------------------------------------------------------
    add_item(
        pc.Q_TOILET_BOWL,
        question_item(
            "Who goes to the toilet bowl?",
            "Last place. One team.",
            choice_question(all_labels, choice_type="DROP_DOWN"),
        ),
    )

    # --- Free text ----------------------------------------------------------
    # Optional on purpose: a required text box is the single biggest driver of
    # abandoned forms, and this one is flavor rather than data.
    add_item(
        pc.Q_BOLD_PREDICTION,
        question_item(
            "One bold prediction for the season.",
            "Optional. It will be published next to your name, so make it count.",
            {"required": False, "textQuestion": {"paragraph": True}},
        ),
    )

    return requests, keys


def prefill_links(responder_uri, identity_question_id, managers):
    """Return [{manager, team, url}] with the identity answer pre-selected.

    Google's pre-fill format is ?usp=pp_url&entry.<questionId>=<value>. The
    value must match the choice string exactly, which is why labels are built
    in one place in poll_common.
    """
    links = []
    for m in managers:
        query = urllib.parse.urlencode(
            {"usp": "pp_url", f"entry.{identity_question_id}": m["label"]}
        )
        links.append(
            {
                "roster_id": m["roster_id"],
                "manager": m["manager"],
                "team": m["team"],
                "url": f"{responder_uri}?{query}",
            }
        )
    return links


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the questions that would be created and exit",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="create a new form even though form_metadata.json already exists",
    )
    args = parser.parse_args()

    managers = pc.load_managers()
    divisions = pc.load_divisions(managers)
    requests, keys = build_requests(managers, divisions)

    print(f"League: {len(managers)} managers, {len(divisions)} divisions")
    for div in divisions:
        print(f"  {div['division_name']}: {', '.join(m for m in div['labels'])}")
    print(f"\nForm: {FORM_TITLE}")
    print(f"Questions ({len(requests)}):")
    for key, req in zip(keys, requests):
        item = req["createItem"]["item"]
        q = item["questionItem"]["question"]
        if "choiceQuestion" in q:
            kind = q["choiceQuestion"]["type"]
            n = len(q["choiceQuestion"]["options"])
            detail = f"{kind}, {n} options"
        else:
            detail = "TEXT (paragraph)"
        req_flag = "required" if q.get("required") else "optional"
        print(f"  [{key}] {item['title']}  -- {detail}, {req_flag}")

    if args.dry_run:
        print("\nDry run: nothing created.")
        return 0

    if pc.FORM_METADATA.exists() and not args.force:
        existing = pc.load_form_metadata()
        print(
            f"\nRefusing to run: {pc.FORM_METADATA.name} already describes form "
            f"{existing.get('form_id')}.\n"
            "Creating another form would orphan any responses already collected.\n"
            "Pass --force if you genuinely want a second form."
        )
        return 1

    creds = pc.get_credentials()
    service = build("forms", "v1", credentials=creds)

    print("\nCreating form...")
    try:
        form = (
            service.forms()
            .create(
                body={
                    "info": {
                        "title": FORM_TITLE,
                        "documentTitle": FORM_DOCUMENT_TITLE,
                    }
                }
            )
            .execute()
        )
    except HttpError as exc:
        if exc.resp.status == 403:
            print(
                "\n403 from forms.create. The Google Forms API is almost certainly "
                "not enabled on this Cloud project.\n"
                "Enable it here, wait a minute, then re-run:\n"
                "  https://console.cloud.google.com/apis/library/forms.googleapis.com"
                "?project=gmail-api-cleaner"
            )
            return 1
        raise

    form_id = form["formId"]
    print(f"  formId: {form_id}")

    # Description and questions both go through batchUpdate: forms.create only
    # accepts info.title and info.documentTitle.
    print("Adding description and questions...")
    body = {
        "requests": [
            {
                "updateFormInfo": {
                    "info": {"description": FORM_DESCRIPTION},
                    "updateMask": "description",
                }
            }
        ]
        + requests
    }
    service.forms().batchUpdate(formId=form_id, body=body).execute()

    # Publish explicitly. All newly created forms carry a publishSettings field,
    # and a form that is not published does not accept responses -- which would
    # mean handing out twelve links to a dead form. isPublished and
    # isAcceptingResponses must BOTH be set in the same call; the API rejects
    # accepting-but-unpublished.
    print("Publishing form and opening it for responses...")
    try:
        service.forms().setPublishSettings(
            formId=form_id,
            body={
                "publishSettings": {
                    "publishState": {
                        "isPublished": True,
                        "isAcceptingResponses": True,
                    }
                },
                "updateMask": "publish_state",
            },
        ).execute()
        published = True
    except HttpError as exc:
        # Not fatal: the form exists and the questions are in place. Worst case
        # the publish toggle has to be flipped once in the editor.
        print(f"  Could not set publish settings ({exc.resp.status}).")
        print("  Open the edit link below and click Publish before sharing.")
        published = False

    # Read the form back to capture the questionIds Google assigned. These are
    # needed for pre-fill URLs and for mapping responses to question keys.
    created = service.forms().get(formId=form_id).execute()
    items = created.get("items", [])
    if len(items) != len(keys):
        print(
            f"  WARNING: created {len(items)} items but expected {len(keys)}. "
            "The questionId map below may be misaligned."
        )

    question_map = {}
    for key, item in zip(keys, items):
        qid = item["questionItem"]["question"]["questionId"]
        question_map[qid] = {"key": key, "title": item["title"]}

    identity_qid = next(
        qid for qid, meta in question_map.items() if meta["key"] == pc.Q_IDENTITY
    )

    responder_uri = created["responderUri"]
    links = prefill_links(responder_uri, identity_qid, managers)

    metadata = {
        "season": SEASON,
        "form_id": form_id,
        "title": FORM_TITLE,
        "published": published,
        "publish_settings": created.get("publishSettings"),
        "responder_uri": responder_uri,
        "edit_uri": f"https://docs.google.com/forms/d/{form_id}/edit",
        "identity_question_id": identity_qid,
        "question_map": question_map,
        "question_order": keys,
        "contenders_pick_count": pc.CONTENDERS_PICK_COUNT,
        "divisions": [
            {
                "division_id": d["division_id"],
                "division_name": d["division_name"],
                "labels": d["labels"],
            }
            for d in divisions
        ],
        "managers": managers,
    }
    pc.FORM_METADATA.write_text(json.dumps(metadata, indent=2) + "\n")

    with pc.PREFILL_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["roster_id", "manager", "team", "url"]
        )
        writer.writeheader()
        writer.writerows(links)

    print(f"\nCreated {len(items)} questions.")
    print(f"  Metadata:      {pc.FORM_METADATA}")
    print(f"  Prefill links: {pc.PREFILL_CSV}")
    print(f"\n  Public form:   {responder_uri}")
    print(f"  Edit form:     {metadata['edit_uri']}")

    state = (created.get("publishSettings") or {}).get("publishState") or {}
    print(f"\n  Published: {state.get('isPublished')} | "
          f"Accepting responses: {state.get('isAcceptingResponses')}")
    if not state.get("isAcceptingResponses"):
        print("  ^ NOT accepting responses yet. Open the edit link and publish "
              "before sharing any link.")

    print("\nSettings the API cannot set. Do these in the form editor:")
    print("  1. Settings -> Responses -> confirm 'Collect email addresses' is Off.")
    print("  2. Settings -> Responses -> optionally turn ON 'Allow response editing'")
    print("     (latest-response-wins dedupe handles resubmits either way).")
    print("  3. Question 4 (contenders): optionally add response validation")
    print(f"     'select exactly {pc.CONTENDERS_PICK_COUNT}'. The API cannot set this; "
          "aggregation weights ballots regardless.")
    print("\nThen verify the whole thing end to end by submitting your own ballot")
    print("from your prefill link and running: poll/.venv/bin/python "
          "poll/fetch_responses.py --show-ballots")

    return 0


if __name__ == "__main__":
    sys.exit(main())
