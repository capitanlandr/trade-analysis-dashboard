#!/usr/bin/env python3
"""
Generate the Draft Pick Value tab's JSON from the committed store.

Runs in CI next to scripts/generate_nfl_top100.py: a plain Python script that
writes into dashboard/frontend/public/ before the Vite build.

READS   pipeline/draft_value/draft_value_picks.csv   (96 rows, frozen baselines)
        pipeline/draft_value/draft_value_daily.csv   (append-only daily series)
        pipeline/draft_value/refresh_status.json     (health of the last refresh)
WRITES  dashboard/frontend/public/ktc-analysis.json        (2026)
        dashboard/frontend/public/ktc-analysis-2025.json   (2025)

FAIL-SOFT BY DESIGN
-------------------
This never fetches anything, so it cannot fail on a network problem. If the
upstream refresh degraded, refresh_status.json says so and that gets stamped into
each JSON's meta.refresh_status. The page renders a stale-data banner from it, so
a silent failure is impossible: the tab reports that it is serving old numbers
rather than quietly looking current.

METRICS (unchanged from the verified analysis)
---------------------------------------------
abs_pct     raw change, baseline -> latest
rel_delta   change in SHARE of class total. Scale-free: shares sum to 100%, so a
            class-wide move cancels out. This is the headline, NOT a cohort-median
            deflator, which is invalid across the draft boundary because the
            cohort changes identity (pick expectations before, players after).
rank_*      curve-invariant, survives any valuation-source swap.
"""

import csv
import json
import statistics as st
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STORE = REPO / "pipeline/draft_value"
PUBLIC = REPO / "dashboard/frontend/public"
FLAT = 5.0

SEASON_CFG = {
    2026: {"out": "ktc-analysis.json", "draft_day": "2026-04-27",
           "fa_from": "2026-03-01",
           "gap_note": ("KTC publishes near-daily including draft day, so this baseline really is "
                        "the day before the draft and free agency is isolated as its own segment. "
                        "Baseline is the PICK-TIER value (KTC prices picks Early/Mid/Late per "
                        "round), so all four picks in a tier share one pre-draft number.")},
    2025: {"out": "ktc-analysis-2025.json", "draft_day": "2025-04-30",
           "fa_from": "2025-03-01",
           "gap_note": ("2025 baseline is each ROOKIE'S OWN pre-draft prospect value: KTC retires "
                        "pick assets after a draft so no 2025 tier history exists. Better "
                        "resolution (per-player, not per-tier) but it asks a slightly different "
                        "question: did the PLAYER beat his prospect price, not did the PICK beat "
                        "its slot price.")},
}


def verdict(p):
    if p is None:
        return None
    return "APPRECIATED" if p > FLAT else ("DECLINED" if p < -FLAT else "FLAT")


def pct(a, b):
    return round((b / a - 1) * 100, 2) if a and b else None


def load_store():
    picks = list(csv.DictReader((STORE / "draft_value_picks.csv").open()))
    daily = {}
    with (STORE / "draft_value_daily.csv").open() as f:
        for r in csv.DictReader(f):
            daily.setdefault((r["season"], r["pick_label"]), {})[r["date"]] = float(r["value"])
    status = {}
    p = STORE / "refresh_status.json"
    if p.exists():
        status = json.loads(p.read_text())
    return picks, daily, status


def at(series, target):
    c = [d for d in series if d <= target]
    return series[max(c)] if c else None


def build(season, picks, daily, status):
    cfg = SEASON_CFG[season]
    rows = []
    excluded = []
    for p in picks:
        if int(p["season"]) != season:
            continue
        key = (str(season), p["pick_label"])
        series = daily.get(key, {})
        try:
            base = float(p["baseline_value"]) if p["baseline_value"] else None
        except ValueError:
            base = None
        latest = max(series.values(), default=None) if False else (
            series[max(series)] if series else None)
        if base is None or latest is None:
            excluded.append(f"{p['pick_label']} {p['player_name']}")
            continue
        rows.append({
            "pick_label": p["pick_label"], "ktc_tier": p["baseline_kind"],
            "round": int(p["round"]), "slot": int(p["slot"]), "overall": int(p["overall"]),
            "owner_team": p["owner_team"],
            "player": {"name": p["player_name"], "sleeper_id": p["sleeper_id"],
                       "pos": p["pos"], "nfl_team": p["nfl_team"]},
            "pre_draft_pick_value": base, "latest_player_value": latest,
            "_series": series,
            "_anchor": float(p["anchor_value"]) if p["anchor_value"] else None,
            # FA baseline is a FROZEN pre-draft anchor in the store, not in the
            # daily series (which deliberately starts the day after the draft).
            "_fa_from": float(p["fa_baseline_value"]) if p.get("fa_baseline_value") else None,
        })
    if not rows:
        raise SystemExit(f"no usable rows for {season}")

    T_pre = sum(r["pre_draft_pick_value"] for r in rows)
    T_now = sum(r["latest_player_value"] for r in rows)
    for r in rows:
        r["share_pct_pre"] = round(r["pre_draft_pick_value"] / T_pre * 100, 4)
        r["share_pct_latest"] = round(r["latest_player_value"] / T_now * 100, 4)
        r["abs_delta"] = round(r["latest_player_value"] - r["pre_draft_pick_value"], 1)
        r["abs_pct"] = pct(r["pre_draft_pick_value"], r["latest_player_value"])
        r["rel_delta"] = pct(r["share_pct_pre"], r["share_pct_latest"])
        # free-agency window ends at the baseline (day before the draft);
        # the draft window runs baseline -> day-after anchor
        r["fa_window_pct"] = pct(r["_fa_from"], r["pre_draft_pick_value"])
        r["draft_window_pct"] = pct(r["pre_draft_pick_value"], r["_anchor"])
        r["verdict_absolute"] = verdict(r["abs_pct"])
        r["verdict_relative"] = verdict(r["rel_delta"])
        r["divergence"] = bool(r["verdict_absolute"] != r["verdict_relative"])
    for stage, k in (("pre", "pre_draft_pick_value"), ("latest", "latest_player_value")):
        for i, r in enumerate(sorted(rows, key=lambda x: -x[k]), 1):
            r[f"rank_{stage}"] = i
    for r in rows:
        r["rank_change"] = r["rank_pre"] - r["rank_latest"]

    all_dates = sorted({d for r in rows for d in r["_series"]})
    marks = [all_dates[0], all_dates[len(all_dates) // 3],
             all_dates[2 * len(all_dates) // 3], all_dates[-1]]
    for r in rows:
        r["series"] = [{"date": d, "value": at(r["_series"], d), "kind": "player"} for d in marks]
        del r["_series"], r["_anchor"], r["_fa_from"]

    per_round = []
    for rd in (1, 2, 3, 4):
        g = [r for r in rows if r["round"] == rd]
        if not g:
            continue
        def med(k):
            v = [x[k] for x in g if x.get(k) is not None]
            return round(st.median(v), 2) if v else None
        def mean(k):
            v = [x[k] for x in g if x.get(k) is not None]
            return round(st.mean(v), 2) if v else None
        per_round.append({
            "round": rd, "count": len(g),
            "mean_abs_pct": mean("abs_pct"), "median_abs_pct": med("abs_pct"),
            "mean_rel_delta": mean("rel_delta"), "median_rel_delta": med("rel_delta"),
            "median_fa_window_pct": med("fa_window_pct"),
            "median_draft_window_pct": med("draft_window_pct"),
            "class_share_pre_pct": round(sum(x["share_pct_pre"] for x in g), 2),
            "class_share_latest_pct": round(sum(x["share_pct_latest"] for x in g), 2),
            "share_appreciating": round(
                sum(1 for x in g if x["verdict_relative"] == "APPRECIATED") / len(g), 3),
            "dips": bool(med("abs_pct") is not None and med("abs_pct") < -FLAT),
        })

    fa = [r["fa_window_pct"] for r in rows if r["fa_window_pct"] is not None]
    dr = [r["draft_window_pct"] for r in rows if r["draft_window_pct"] is not None]
    r1 = per_round[0]
    baseline_date = next(p["baseline_date"] for p in picks if int(p["season"]) == season)
    anchor_date = next(p["anchor_date"] for p in picks if int(p["season"]) == season)
    latest_date = all_dates[-1]

    out = {
        "meta": {
            "season": season, "source": "KeepTradeCut", "format": "SF", "is_fixture": False,
            "value_column": "KTC Superflex",
            "draft_day": cfg["draft_day"], "draft_started_utc": cfg["draft_day"] + "T00:00:00Z",
            "baseline_date": baseline_date, "baseline_days_before_draft": 1,
            "baseline_predates_free_agency": False,
            "baseline_kind": rows[0]["ktc_tier"],
            "pre_draft_snapshot": {"date": baseline_date, "sha": "ktc-store"},
            "post_draft_snapshot": {"date": anchor_date, "sha": "ktc-store"},
            "latest": latest_date,
            "gap_note": cfg["gap_note"],
            "picks_excluded_no_ktc_data": excluded,
            "picks_shown": len(rows),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "refresh_status": {
                "degraded": bool(status.get("degraded")),
                "data_age_days": status.get("data_age_days"),
                "last_attempt_utc": status.get("last_attempt_utc"),
                "last_success_date": status.get("last_success_date"),
                "errors": status.get("errors", [])[:5],
                "data_through": latest_date,
            },
        },
        "picks": rows, "per_round": per_round, "per_position": [],
        "round1_dips": bool(r1["dips"]),
        "round1_note": (
            f"Round 1 moved {r1['median_abs_pct']}% (median) off its pre-draft value and holds "
            f"{r1['class_share_latest_pct']}% of class value vs {r1['class_share_pre_pct']}% before "
            f"the draft. Share is the number that matters: it is scale-free, so a class-wide move "
            f"cancels out."),
        "window_split": {
            "fa_window": {"from": next(x["fa_baseline_date"] for x in picks if int(x["season"])==season), "to": baseline_date,
                          "median_pct": round(st.median(fa), 2), "mean_pct": round(st.mean(fa), 2),
                          "min_pct": round(min(fa), 2), "max_pct": round(max(fa), 2)},
            "draft_window": {"from": baseline_date, "to": anchor_date,
                             "median_pct": round(st.median(dr), 2), "mean_pct": round(st.mean(dr), 2),
                             "min_pct": round(min(dr), 2), "max_pct": round(max(dr), 2)},
            "ratio_draft_over_fa": round(abs(st.median(dr)) / max(abs(st.median(fa)), 1e-9), 1),
            "verdict": (
                f"Free agency moved value by a median of {st.median(fa):+.2f}%. The draft moved it "
                f"{st.median(dr):+.2f}%."
                + ("" if season == 2026 else
                   " NOTE: the 2025 baseline is PROSPECT value, so the first window is pre-draft "
                   "hype building toward the NFL draft, not free agency repricing picks. Not "
                   "comparable to the 2026 panel.")),
        },
        "class_index_series": [
            {"date": d,
             "cohort_index": round(st.median([x["series"][i]["value"] for x in rows
                                              if x["series"][i]["value"] is not None]), 1),
             "class_total": round(sum(x["series"][i]["value"] for x in rows
                                      if x["series"][i]["value"] is not None), 1)}
            for i, d in enumerate(marks)
        ],
    }
    (PUBLIC / cfg["out"]).write_text(json.dumps(out, indent=2))
    return out


def main():
    picks, daily, status = load_store()
    print(f"store: {len(picks)} picks, {len(daily)} series, "
          f"degraded={status.get('degraded')} through {status.get('last_success_date')}")

    # Derive staleness from the DATA, not just the builder's own flag. If the
    # refresh crashed hard it may never have written refresh_status.json, leaving
    # a stale-but-clean flag from the last good run. Comparing the newest date in
    # the store against today catches that case too, so a silent stale tab is
    # impossible regardless of how the upstream step failed.
    newest = max((d for s2 in daily.values() for d in s2), default=None)
    if newest:
        age = (datetime.now(timezone.utc).date() - date.fromisoformat(newest)).days
        status["data_age_days"] = age
        if age > 2:
            status["degraded"] = True
            status.setdefault("errors", []).append(
                f"store data is {age} days old (newest {newest}); refresh likely failed")
            print(f"  WARNING: data is {age} days stale -> degraded=True")

    for season in (2026, 2025):
        o = build(season, picks, daily, status)
        m, ws = o["meta"], o["window_split"]
        print(f"\n{season} -> {SEASON_CFG[season]['out']}")
        print(f"  picks {m['picks_shown']}, excluded {len(m['picks_excluded_no_ktc_data'])}, "
              f"baseline {m['baseline_date']} ({m['baseline_kind']}), through {m['latest']}")
        print(f"  FA {ws['fa_window']['median_pct']:+}%  DRAFT {ws['draft_window']['median_pct']:+}%"
              f"  ratio {ws['ratio_draft_over_fa']}x")
        print(f"  {'Rnd':>3}{'n':>4}{'absMed':>9}{'relMed':>9}{'shPre':>8}{'shNow':>8}")
        for r in o["per_round"]:
            print(f"  {r['round']:>3}{r['count']:>4}{r['median_abs_pct']:>9}"
                  f"{r['median_rel_delta']:>9}{r['class_share_pre_pct']:>8}"
                  f"{r['class_share_latest_pct']:>8}")


if __name__ == "__main__":
    main()
