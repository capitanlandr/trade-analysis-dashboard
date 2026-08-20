#!/usr/bin/env python3
"""Generate survey-results.json from the Dynasuiiii Preseason Predictions Survey xlsx.

Reads the Google Form responses export and produces a static analysis JSON that the
Survey Results dashboard page renders. No runtime xlsx dependency: run this once
(or whenever the responses change) to regenerate public/survey-results.json.

Usage:
    python3 scripts/generate_survey_results.py [path/to/survey.xlsx] [path/to/out.json]
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

DEFAULT_XLSX = "/Users/lndahayo/Documents/Commish Tiers/Dynasuiiii Preseason Predictions Survey (Responses).xlsx"
DEFAULT_OUT = str(Path(__file__).resolve().parent.parent / "public" / "survey-results.json")

ORDINALS = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4}
DIV_RE = re.compile(r"^Division \d+ — (.+?) Standings \[(.+)\]$")


def team_short(name: str) -> str:
    """'Kyle (Lisan al-Caleb)' -> 'Kyle'."""
    return name.split(" (")[0].strip()


def counts_to_list(counter, total):
    """Ordered list of {label, count, pct} descending by count."""
    out = []
    for label, count in counter.most_common():
        out.append({
            "label": label,
            "count": int(count),
            "pct": round(100.0 * count / total, 1) if total else 0.0,
        })
    return out


def main():
    xlsx = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XLSX
    out_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT

    df = pd.read_excel(xlsx, sheet_name="Form Responses 1")
    n = len(df)

    cols = list(df.columns)
    division_cols = [c for c in cols if DIV_RE.match(str(c))]
    pick_cols = [c for c in cols if c not in division_cols and c not in ("Timestamp", "Email Address")]

    # --- Division standings predictions -------------------------------------
    # Group teams by division, compute predicted-finish distribution + avg rank.
    divisions = defaultdict(list)
    for c in division_cols:
        m = DIV_RE.match(str(c))
        div_name, team = m.group(1), m.group(2)
        col = df[c].dropna().astype(str).str.strip()
        placements = Counter(col.tolist())
        ranks = [ORDINALS[v] for v in col.tolist() if v in ORDINALS]
        avg_rank = round(sum(ranks) / len(ranks), 2) if ranks else None
        first_place = int(placements.get("1st", 0))
        responses = len(col)
        divisions[div_name].append({
            "team": team,
            "team_short": team_short(team),
            "avg_predicted_rank": avg_rank,
            "first_place_votes": first_place,
            "first_place_pct": round(100.0 * first_place / responses, 1) if responses else 0.0,
            "placements": [
                {"place": p, "count": int(placements.get(p, 0))}
                for p in ("1st", "2nd", "3rd", "4th")
            ],
            "responses": responses,
        })

    division_list = []
    for div_name, teams in divisions.items():
        teams_sorted = sorted(
            teams,
            key=lambda t: (t["avg_predicted_rank"] if t["avg_predicted_rank"] is not None else 99),
        )
        for i, t in enumerate(teams_sorted, 1):
            t["consensus_seed"] = i
        favorite = teams_sorted[0]
        division_list.append({
            "division": div_name,
            "teams": teams_sorted,
            "consensus_favorite": favorite["team_short"],
        })

    # --- Pick questions -----------------------------------------------------
    pick_questions = []
    for c in pick_cols:
        series = df[c].dropna().astype(str).str.strip()
        multi = series.str.contains(",").any()
        if multi:
            counter = Counter()
            for val in series:
                for part in val.split(","):
                    p = part.strip()
                    if p:
                        counter[p] += 1
            note = "Multi-select — respondents could choose more than one; percentages are of respondents."
        else:
            counter = Counter(series.tolist())
            note = None
        total = len(series)
        results = counts_to_list(counter, total)
        pick_questions.append({
            "question": str(c),
            "multi_select": bool(multi),
            "note": note,
            "responses": int(total),
            "top_answer": results[0]["label"] if results else None,
            "top_pct": results[0]["pct"] if results else None,
            "results": results,
        })

    # --- Headline insights --------------------------------------------------
    insights = []
    champ = next((q for q in pick_questions if "win the championship" in q["question"].lower()), None)
    if champ and champ["results"]:
        top = champ["results"][0]
        insights.append(
            f"Championship favorite: {top['label']} — {top['count']} of {champ['responses']} votes ({top['pct']}%)."
        )
    miss = next((q for q in pick_questions if "most likely to miss" in q["question"].lower()), None)
    if miss and miss["results"]:
        top = miss["results"][0]
        insights.append(
            f"Most-picked to fall out of the playoffs: {top['label']} ({top['count']}/{miss['responses']}, {top['pct']}%)."
        )
    rise = next((q for q in pick_questions if "most likely to make" in q["question"].lower()), None)
    if rise and rise["results"]:
        top = rise["results"][0]
        insights.append(
            f"Most-picked breakout (missed playoffs → makes them): {top['label']} ({top['count']}/{rise['responses']}, {top['pct']}%)."
        )
    for d in division_list:
        fav = d["teams"][0]
        insights.append(
            f"{d['division']} division consensus favorite: {fav['team_short']} "
            f"(avg predicted finish {fav['avg_predicted_rank']}, {fav['first_place_votes']} first-place votes)."
        )

    data = {
        "title": "Preseason Predictions Survey",
        "subtitle": "Dynasuiiii league members' preseason predictions",
        "total_responses": int(n),
        "divisions": division_list,
        "pick_questions": pick_questions,
        "insights": insights,
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out_path}: {n} responses, {len(division_list)} divisions, {len(pick_questions)} pick questions.")


if __name__ == "__main__":
    main()
