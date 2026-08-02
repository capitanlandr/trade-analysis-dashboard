#!/usr/bin/env python3
"""Fetch poll responses, dedupe them, and write the dashboard JSON.

Reads every submission via forms.responses.list, keeps only the most recent
response per manager, aggregates the tallies, and writes
dashboard/frontend/public/api-preseason-poll.json in the same shape as the
other api-*.json files the frontend already consumes.

Usage:
    poll/.venv/bin/python poll/fetch_responses.py
    poll/.venv/bin/python poll/fetch_responses.py --dry-run   # no file writes
    poll/.venv/bin/python poll/fetch_responses.py --show-ballots

Safe to run repeatedly. It is a pure read of the form plus a rewrite of one
JSON file, so re-running after new submissions is the intended workflow.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import poll_common as pc


def fetch_all_responses(service, form_id):
    """Return every response, following pagination."""
    responses = []
    page_token = None
    while True:
        kwargs = {"formId": form_id, "pageSize": 100}
        if page_token:
            kwargs["pageToken"] = page_token
        result = service.forms().responses().list(**kwargs).execute()
        responses.extend(result.get("responses", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            return responses


def extract_answers(response, question_map):
    """Flatten one API response into {question_key: value}.

    Single-answer questions yield a string; checkbox questions yield a list.
    Unknown questionIds are ignored, which is what keeps this from crashing if
    a question is later added by hand in the form editor.
    """
    answers = {}
    for qid, answer in (response.get("answers") or {}).items():
        meta = question_map.get(qid)
        if not meta:
            continue
        values = [
            a.get("value", "")
            for a in answer.get("textAnswers", {}).get("answers", [])
        ]
        values = [v for v in values if v]
        if not values:
            continue
        answers[meta["key"]] = values if meta["key"] == pc.Q_CONTENDERS else values[0]
    return answers


def dedupe_latest(responses, question_map):
    """Keep the most recent submission per identity.

    Latest wins, by lastSubmittedTime. This is the whole mechanism behind
    "you can change your picks": people just submit again. Responses with no
    identity answer are dropped and reported, since nothing can be done with
    an unattributed ballot.
    """
    by_identity = {}
    orphans = []

    for response in responses:
        answers = extract_answers(response, question_map)
        identity = answers.get(pc.Q_IDENTITY)
        submitted = response.get("lastSubmittedTime", "")

        if not identity:
            orphans.append(
                {
                    "response_id": response.get("responseId"),
                    "submitted": submitted,
                    "answered": sorted(answers),
                }
            )
            continue

        record = {
            "identity": identity,
            "submitted": submitted,
            "response_id": response.get("responseId"),
            "answers": answers,
        }
        prior = by_identity.get(identity)
        if prior is None or submitted > prior["submitted"]:
            if prior is not None:
                record["superseded"] = prior.get("superseded", 0) + 1
            by_identity[identity] = record
        else:
            by_identity[identity]["superseded"] = (
                by_identity[identity].get("superseded", 0) + 1
            )

    return by_identity, orphans


def tally(counter, total_ballots):
    """Return a sorted, share-annotated tally.

    Every entry carries both the raw count and the share of ballots, per the
    rule that a metric without its denominator is not a metric.
    """
    rows = [
        {
            "label": label,
            "votes": round(votes, 3) if isinstance(votes, float) else votes,
            "share": round(votes / total_ballots, 4) if total_ballots else 0.0,
        }
        for label, votes in counter.items()
    ]
    rows.sort(key=lambda r: (-r["votes"], r["label"]))
    return rows


def aggregate(ballots, metadata):
    """Turn deduped ballots into the published results payload."""
    managers = metadata["managers"]
    label_to_manager = {m["label"]: m for m in managers}
    total = len(ballots)

    champion = Counter()
    toilet = Counter()
    # Contenders are weighted 1/len(picks) per ballot. The form cannot enforce
    # an exact pick count, so weighting is what keeps a voter who checks eight
    # teams from carrying twice the influence of one who checks four.
    contenders_weighted = Counter()
    contenders_raw = Counter()
    division_votes = defaultdict(Counter)
    self_reports = []
    predictions = []

    for record in ballots.values():
        answers = record["answers"]

        if answers.get(pc.Q_CHAMPION):
            champion[answers[pc.Q_CHAMPION]] += 1
        if answers.get(pc.Q_TOILET_BOWL):
            toilet[answers[pc.Q_TOILET_BOWL]] += 1

        picks = answers.get(pc.Q_CONTENDERS) or []
        if picks:
            weight = pc.CONTENDERS_PICK_COUNT / len(picks)
            for pick in picks:
                contenders_weighted[pick] += weight
                contenders_raw[pick] += 1

        for div in metadata["divisions"]:
            key = pc.division_key(div["division_id"])
            if answers.get(key):
                division_votes[div["division_id"]][answers[key]] += 1

        manager = label_to_manager.get(record["identity"], {})
        self_reports.append(
            {
                "roster_id": manager.get("roster_id"),
                "label": record["identity"],
                "manager": manager.get("manager"),
                "team": manager.get("team"),
                "predicted_finish": answers.get(pc.Q_SELF_FINISH),
                "self_tier": answers.get(pc.Q_SELF_TIER),
                "picked_self_as_contender": record["identity"] in picks,
                "picked_self_as_champion": answers.get(pc.Q_CHAMPION)
                == record["identity"],
                "submitted": record["submitted"],
            }
        )

        if answers.get(pc.Q_BOLD_PREDICTION):
            predictions.append(
                {
                    "label": record["identity"],
                    "manager": manager.get("manager"),
                    "prediction": answers[pc.Q_BOLD_PREDICTION],
                }
            )

    self_reports.sort(key=lambda r: r["roster_id"] or 99)

    # Self-perception vs. peer perception: the most interesting number in the
    # whole poll. A manager whose own finish prediction is far rosier than the
    # league's view of them is the story the results page should surface.
    finish_rank = {v: i + 1 for i, v in enumerate(pc.FINISH_OPTIONS)}
    champion_rank = {
        row["label"]: i + 1 for i, row in enumerate(tally(champion, total))
    }
    for row in self_reports:
        own = finish_rank.get(row["predicted_finish"])
        peer = champion_rank.get(row["label"])
        row["own_finish_rank"] = own
        row["peer_champion_rank"] = peer

    responded = {r["label"] for r in self_reports}
    missing = [
        {"roster_id": m["roster_id"], "manager": m["manager"], "label": m["label"]}
        for m in managers
        if m["label"] not in responded
    ]

    return {
        "season": metadata["season"],
        "form_url": metadata["responder_uri"],
        "participation": {
            "responded": total,
            "eligible": len(managers),
            "share": round(total / len(managers), 4) if managers else 0.0,
            "missing": missing,
        },
        "champion": tally(champion, total),
        "toilet_bowl": tally(toilet, total),
        "contenders": {
            "weighted": tally(contenders_weighted, total),
            "raw_mentions": tally(contenders_raw, total),
            "pick_target": pc.CONTENDERS_PICK_COUNT,
            "note": (
                "weighted scales each ballot to "
                f"{pc.CONTENDERS_PICK_COUNT} picks so ballots of different "
                "lengths carry equal weight; raw_mentions is the unadjusted count"
            ),
        },
        "divisions": [
            {
                "division_id": div["division_id"],
                "division_name": div["division_name"],
                "results": tally(division_votes[div["division_id"]], total),
            }
            for div in metadata["divisions"]
        ],
        "self_assessments": self_reports,
        "bold_predictions": predictions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="do not write files")
    parser.add_argument(
        "--show-ballots", action="store_true", help="print each deduped ballot"
    )
    args = parser.parse_args()

    metadata = pc.load_form_metadata()
    question_map = metadata["question_map"]

    creds = pc.get_credentials()
    service = build("forms", "v1", credentials=creds)

    print(f"Form: {metadata['title']} ({metadata['form_id']})")
    try:
        responses = fetch_all_responses(service, metadata["form_id"])
    except HttpError as exc:
        if exc.resp.status == 403:
            print(
                "403 from forms.responses.list. Either the Forms API is not "
                "enabled or the cached token predates the responses.readonly "
                f"scope. Delete {pc.TOKEN_FILE.name} and re-run to re-consent."
            )
            return 1
        raise

    print(f"Raw submissions: {len(responses)}")

    ballots, orphans = dedupe_latest(responses, question_map)
    superseded = sum(r.get("superseded", 0) for r in ballots.values())
    print(f"Unique managers: {len(ballots)} of {len(metadata['managers'])}")
    if superseded:
        print(f"  ({superseded} earlier submission(s) superseded by newer ones)")
    if orphans:
        print(f"  WARNING: {len(orphans)} response(s) with no identity answer, dropped:")
        for o in orphans:
            print(f"    {o['response_id']} submitted {o['submitted']}")

    if args.show_ballots:
        print()
        for record in sorted(ballots.values(), key=lambda r: r["identity"]):
            print(f"{record['identity']}  ({record['submitted']})")
            for key in metadata["question_order"]:
                if key == pc.Q_IDENTITY:
                    continue
                value = record["answers"].get(key)
                if value:
                    if isinstance(value, list):
                        value = ", ".join(value)
                    print(f"    {key}: {value}")

    results = aggregate(ballots, metadata)

    print(f"\nParticipation: {results['participation']['responded']}"
          f"/{results['participation']['eligible']}")
    if results["champion"]:
        top = results["champion"][0]
        print(f"Champion leader: {top['label']} "
              f"({top['votes']} votes, {top['share']:.0%})")
    if results["toilet_bowl"]:
        low = results["toilet_bowl"][0]
        print(f"Toilet bowl leader: {low['label']} "
              f"({low['votes']} votes, {low['share']:.0%})")

    if args.dry_run:
        print("\nDry run: no files written.")
        return 0

    pc.RESPONSES_RAW.write_text(json.dumps(responses, indent=2) + "\n")
    pc.POLL_OUTPUT.write_text(json.dumps(results, indent=2) + "\n")
    print(f"\nWrote {pc.POLL_OUTPUT.relative_to(pc.REPO_ROOT)}")
    print(f"Wrote {pc.RESPONSES_RAW.relative_to(pc.REPO_ROOT)} (raw backup)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
