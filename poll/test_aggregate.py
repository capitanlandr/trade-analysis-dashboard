#!/usr/bin/env python3
"""Offline check of the dedupe and aggregation logic.

Builds synthetic API responses in the exact shape forms.responses.list returns,
so the two functions that actually decide the published numbers can be verified
without a real form or a network call.

Usage: poll/.venv/bin/python poll/test_aggregate.py
"""

import json
import sys

import poll_common as pc
from create_form import build_requests
from fetch_responses import aggregate, dedupe_latest

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILURES.append(name)


def fake_metadata(managers, divisions, keys):
    """Mimic what create_form.py writes, with synthetic questionIds."""
    question_map = {
        f"qid{i:02d}": {"key": key, "title": key} for i, key in enumerate(keys)
    }
    return {
        "season": 2026,
        "form_id": "FAKE",
        "title": "Fake Poll",
        "responder_uri": "https://forms.gle/fake",
        "question_map": question_map,
        "question_order": keys,
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


def make_response(metadata, response_id, submitted, answers):
    """Build one API-shaped response from {question_key: value}."""
    key_to_qid = {m["key"]: qid for qid, m in metadata["question_map"].items()}
    api_answers = {}
    for key, value in answers.items():
        values = value if isinstance(value, list) else [value]
        api_answers[key_to_qid[key]] = {
            "textAnswers": {"answers": [{"value": v} for v in values]}
        }
    return {
        "responseId": response_id,
        "lastSubmittedTime": submitted,
        "answers": api_answers,
    }


def main():
    managers = pc.load_managers()
    divisions = pc.load_divisions(managers)
    _, keys = build_requests(managers, divisions)
    metadata = fake_metadata(managers, divisions, keys)

    labels = [m["label"] for m in managers]
    landry, grant, brevin, kyle = labels[0], labels[1], labels[2], labels[3]
    div_keys = [pc.division_key(d["division_id"]) for d in divisions]

    def ballot(identity, champion, toilet, contenders, finish, tier, prediction=None):
        answers = {
            pc.Q_IDENTITY: identity,
            pc.Q_CHAMPION: champion,
            pc.Q_TOILET_BOWL: toilet,
            pc.Q_CONTENDERS: contenders,
            pc.Q_SELF_FINISH: finish,
            pc.Q_SELF_TIER: tier,
            div_keys[0]: divisions[0]["labels"][0],
            div_keys[1]: divisions[1]["labels"][0],
            div_keys[2]: divisions[2]["labels"][0],
        }
        if prediction:
            answers[pc.Q_BOLD_PREDICTION] = prediction
        return answers

    responses = [
        # Landry submits, then resubmits with a different champion. Only the
        # later one should count.
        make_response(metadata, "r1", "2026-08-01T10:00:00Z",
                      ballot(landry, grant, kyle, [grant, brevin], "4th", "Contender")),
        make_response(metadata, "r2", "2026-08-02T10:00:00Z",
                      ballot(landry, landry, kyle, [landry, grant, brevin, kyle],
                             "1st", "Title favorite", "I win it all.")),
        # Grant: four picks, the target count.
        make_response(metadata, "r3", "2026-08-01T11:00:00Z",
                      ballot(grant, landry, kyle, [landry, grant, brevin, kyle],
                             "2nd", "Contender")),
        # Brevin: eight picks. Weighting must stop this ballot outvoting Grant's.
        make_response(metadata, "r4", "2026-08-01T12:00:00Z",
                      ballot(brevin, brevin, kyle, labels[:8], "3rd", "Playoff team")),
        # Unattributed: no identity answer, must be dropped not crash.
        make_response(metadata, "r5", "2026-08-01T13:00:00Z",
                      {pc.Q_CHAMPION: kyle}),
    ]

    print("dedupe_latest:")
    ballots, orphans = dedupe_latest(responses, metadata["question_map"])
    check("3 unique managers from 5 submissions", len(ballots) == 3, f"got {len(ballots)}")
    check("1 unattributed response dropped", len(orphans) == 1, f"got {len(orphans)}")
    check("latest submission wins",
          ballots[landry]["answers"][pc.Q_CHAMPION] == landry,
          f"got {ballots[landry]['answers'][pc.Q_CHAMPION]}")
    check("superseded count recorded", ballots[landry].get("superseded") == 1,
          f"got {ballots[landry].get('superseded')}")

    print("\naggregate:")
    results = aggregate(ballots, metadata)

    check("participation counts deduped ballots",
          results["participation"]["responded"] == 3)
    check("9 managers listed missing",
          len(results["participation"]["missing"]) == 9,
          f"got {len(results['participation']['missing'])}")

    champ = {r["label"]: r["votes"] for r in results["champion"]}
    check("champion tally correct",
          champ.get(landry) == 2 and champ.get(brevin) == 1, json.dumps(champ))
    # share is rounded to 4 decimals for display, so compare at that precision.
    check("champion share uses ballot denominator",
          results["champion"][0]["share"] == round(2 / 3, 4),
          str(results["champion"][0]["share"]))

    check("toilet bowl unanimous",
          results["toilet_bowl"][0]["label"] == kyle
          and results["toilet_bowl"][0]["votes"] == 3)

    weighted = {r["label"]: r["votes"] for r in results["contenders"]["weighted"]}
    raw = {r["label"]: r["votes"] for r in results["contenders"]["raw_mentions"]}
    # Landry and Grant each picked 4 (weight 1.0 per pick); Brevin picked 8
    # (weight 0.5). Grant appears on all three ballots: 1.0 + 1.0 + 0.5 = 2.5.
    check("weighted contenders scale by ballot length",
          abs(weighted.get(grant, 0) - 2.5) < 1e-6, str(weighted.get(grant)))
    check("raw mentions unadjusted", raw.get(grant) == 3, str(raw.get(grant)))
    # Every ballot totals exactly the pick target once weighted.
    total_weight = sum(weighted.values())
    check("weighted total equals ballots x pick target",
          abs(total_weight - 3 * pc.CONTENDERS_PICK_COUNT) < 1e-6,
          f"got {total_weight}")

    check("all 3 divisions reported", len(results["divisions"]) == 3)
    check("division winner tallied",
          results["divisions"][0]["results"][0]["votes"] == 3)

    check("self assessments sorted by roster_id",
          [r["roster_id"] for r in results["self_assessments"]] == [1, 2, 3])
    check("self-pick detected",
          results["self_assessments"][0]["picked_self_as_champion"] is True)
    check("peer rank computed",
          results["self_assessments"][0]["peer_champion_rank"] == 1,
          str(results["self_assessments"][0]["peer_champion_rank"]))
    check("only submitted predictions included",
          len(results["bold_predictions"]) == 1,
          str(len(results["bold_predictions"])))

    print("\nJSON serializable:")
    try:
        json.dumps(results)
        print("  PASS  results encode cleanly")
    except (TypeError, ValueError) as exc:
        print(f"  FAIL  {exc}")
        FAILURES.append("json")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {', '.join(FAILURES)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
