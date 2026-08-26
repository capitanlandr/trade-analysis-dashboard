#!/usr/bin/env python3
"""Render the 12-team dynasty total value over time to a PNG."""
import csv, collections
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DIR = "/local/home/lndahayo/projects/trade-analysis-dashboard/prototypes/data/dynasty_value_over_time"
CSV = f"{DIR}/team_value_daily.csv"
OUT = f"{DIR}/dynasty_value_over_time.png"

series = collections.defaultdict(lambda: ([], []))  # team -> (dates, totals)
final = {}
with open(CSV) as f:
    for r in csv.DictReader(f):
        d = datetime.strptime(r["date"], "%Y-%m-%d")
        team = r["team"]
        tv = float(r["total_value"])
        series[team][0].append(d)
        series[team][1].append(tv)
        final[team] = (d, tv)

# order legend by final value, descending
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

# season boundary markers (rookie draft dates approx)
for yr, dt in [("S2 2025", "2025-08-01"), ("S3 2026", "2026-08-01")]:
    x = datetime.strptime(dt, "%Y-%m-%d")
    ax.axvline(x, color="#484f58", linestyle="--", linewidth=0.9)
    ax.text(x, ax.get_ylim()[1], f" {yr}", color="#6e7681", fontsize=8, va="top")

ax.set_title("Dynasty Team Value Over Time (Superflex, KTC-backed)  —  Season 1 2024 → 2026-08-26",
             color="#e6edf3", fontsize=15, pad=14)
ax.set_ylabel("Total value (roster + picks)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax.grid(True, color="#21262d", linewidth=0.6)
ax.legend(loc="upper left", fontsize=8, ncol=2, framealpha=0.15,
          labelcolor="#e6edf3", title="Team (final value)", title_fontsize=9)
plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
fig.tight_layout()
fig.savefig(OUT, facecolor=fig.get_facecolor(), bbox_inches="tight")
print("wrote", OUT)
