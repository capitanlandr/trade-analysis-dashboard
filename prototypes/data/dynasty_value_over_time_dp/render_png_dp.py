#!/usr/bin/env python3
"""Render the 12-team dynasty total value over time (DynastyProcess-backed) to a PNG."""
import csv, collections
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DIR = "/local/home/lndahayo/projects/trade-analysis-dashboard/prototypes/data/dynasty_value_over_time_dp"
CSV = f"{DIR}/team_value_daily_dp.csv"
OUT = f"{DIR}/dynasty_value_over_time_dp.png"

# read per (date, team) totals, then mask whole-slate-zero days as gaps (NaN) so
# offseason DP coverage holes render as line breaks, not fabricated zeros.
by_date = collections.defaultdict(dict)   # date -> {team: total}
final = {}
with open(CSV) as f:
    for r in csv.DictReader(f):
        by_date[r["date"]][r["team"]] = float(r["total_value"])

all_dates = sorted(by_date)
teams_all = sorted({t for d in by_date.values() for t in d})
series = collections.defaultdict(lambda: ([], []))
for ds in all_dates:
    d = datetime.strptime(ds, "%Y-%m-%d")
    slate = by_date[ds]
    slate_zero = max(slate.values()) == 0
    for team in teams_all:
        tv = slate.get(team, 0.0)
        series[team][0].append(d)
        series[team][1].append(float("nan") if slate_zero else tv)
        if not slate_zero:
            final[team] = (d, tv)

order = sorted(final, key=lambda t: final[t][1], reverse=True)

plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
                     "text.color": "#e6edf3", "axes.labelcolor": "#e6edf3",
                     "xtick.color": "#9da7b3", "ytick.color": "#9da7b3",
                     "axes.edgecolor": "#30363d"})
fig, ax = plt.subplots(figsize=(15, 8.2), dpi=130)

cmap = plt.get_cmap("tab20")
for i, team in enumerate(order):
    dates, totals = series[team]
    ax.plot(dates, totals, linewidth=1.8, color=cmap(i % 20),
            label=f"{team}  ({final[team][1]:,.0f})")

for yr, dt in [("2025 rookie draft", "2025-04-30"), ("2026 rookie draft", "2026-04-27")]:
    x = datetime.strptime(dt, "%Y-%m-%d")
    ax.axvline(x, color="#484f58", linestyle="--", linewidth=0.9)
    ax.text(x, ax.get_ylim()[1], f" {yr}", color="#6e7681", fontsize=8, va="top")

last_label = order and series[order[0]][0][-1].strftime("%Y-%m-%d")
ax.set_title(f"Dynasty Team Value Over Time (Superflex, DynastyProcess value_2qb, weekly)  —  Season 1 2024 → {last_label}",
             color="#e6edf3", fontsize=14, pad=14)
ax.set_ylabel("Total value (roster + picks), DP value_2qb")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax.grid(True, color="#21262d", linewidth=0.6)
ax.legend(loc="upper left", fontsize=8, ncol=2, framealpha=0.15,
          labelcolor="#e6edf3", title="Team (final value)", title_fontsize=9)
plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
fig.tight_layout()
fig.savefig(OUT, facecolor=fig.get_facecolor(), bbox_inches="tight")
print("wrote", OUT)
