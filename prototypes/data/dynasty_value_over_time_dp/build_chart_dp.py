#!/usr/bin/env python3
"""Build a standalone interactive HTML chart from team_value_daily_dp.csv.

Mirrors the KTC chart (prototypes/data/dynasty_value_over_time/build_chart.py):
12 lines of Superflex total dynasty value (players + picks), one per team,
click-to-isolate legend, hover-highlight, ranked tooltip, Total/Players/Picks
toggle, season-boundary markers, light/dark. VALUE SOURCE is DynastyProcess
value_2qb (weekly git-history snapshots, <=7-day forward-fill).
"""
import csv, json, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "team_value_daily_dp.csv"))))

dates = sorted({r["date"] for r in rows})
teams = {}
for r in rows:
    teams.setdefault(int(r["roster_id"]), r["team"])
order = sorted(teams)

series_total = {rid: [None] * len(dates) for rid in order}
series_players = {rid: [None] * len(dates) for rid in order}
series_picks = {rid: [None] * len(dates) for rid in order}
idx = {d: i for i, d in enumerate(dates)}
for r in rows:
    rid = int(r["roster_id"]); i = idx[r["date"]]
    series_total[rid][i] = int(r["total_value"])
    series_players[rid][i] = int(r["player_value"])
    series_picks[rid][i] = int(r["pick_value"])

# DP coverage gaps: on days where the ENTIRE 12-team slate has 0 total value, the
# weekly DP snapshot gap exceeded the <=7d fill window (offseason hole / pre-first
# snapshot). Render those as line breaks (None), not fabricated zeros — matching the
# KTC chart's spanGaps convention. Intra-team real zeros (a team with no DP-valued
# asset while others do) are left as 0 and NOT hidden.
day_slate_zero = []
for i in range(len(dates)):
    mx = max((series_total[rid][i] or 0) for rid in order)
    day_slate_zero.append(mx == 0)
gap_days = sum(day_slate_zero)
for i, isgap in enumerate(day_slate_zero):
    if isgap:
        for rid in order:
            series_total[rid][i] = None
            series_players[rid][i] = None
            series_picks[rid][i] = None

PALETTE = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#3fae5a",
           "#9085e9", "#1f97a6", "#e0514a", "#b06ae0", "#7f8f0f", "#c56ba6"]

datasets = [{
    "roster_id": rid, "label": teams[rid],
    "color": PALETTE[i % len(PALETTE)],
    "total": series_total[rid], "players": series_players[rid], "picks": series_picks[rid],
} for i, rid in enumerate(order)]

payload = {
    "dates": dates,
    "datasets": datasets,
    "boundaries": [
        {"date": "2024-08-14", "label": "S1 startup draft"},
        {"date": "2025-04-30", "label": "2025 rookie draft"},
        {"date": "2026-04-27", "label": "2026 rookie draft"},
    ],
}

first, last = dates[0], dates[-1]

HTML = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Dynasty Value Over Time — Dynasuiiii (12 teams, Superflex, DynastyProcess-backed)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
<style>
:root{ --surface:#1a1a19; --panel:#232322; --ink:#ffffff; --ink2:#c3c2b7; --muted:#87867e; --grid:#33322f; }
:root[data-theme="light"]{ --surface:#fcfcfb; --panel:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --muted:#8a897f; --grid:#e7e6e1; }
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
.wrap{max-width:1180px;margin:0 auto;padding:24px 20px 48px;}
h1{font-size:20px;margin:0 0 2px;}
.sub{color:var(--ink2);font-size:13px;margin:0 0 16px;}
.card{background:var(--panel);border:1px solid var(--grid);border-radius:12px;padding:16px 16px 8px;}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px;}
.toolbar .spacer{flex:1}
button{background:transparent;color:var(--ink2);border:1px solid var(--grid);border-radius:8px;padding:6px 10px;cursor:pointer;font-size:12px;}
button:hover{color:var(--ink);border-color:var(--muted);}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin:14px 2px 2px;}
.legend .item{display:flex;align-items:center;gap:7px;cursor:pointer;padding:3px 6px;border-radius:7px;font-size:12.5px;color:var(--ink2);user-select:none;}
.legend .item:hover{background:rgba(127,127,127,.12);color:var(--ink);}
.legend .item.off{opacity:.38;}
.legend .swatch{width:11px;height:11px;border-radius:3px;flex:none;}
.chartbox{position:relative;height:520px;}
.note{color:var(--muted);font-size:12px;margin-top:14px;}
.note code{color:var(--ink2);}
</style>
</head>
<body>
<div class="wrap">
  <h1>Dynasty Value Over Time — “Dynasuiiii” (DynastyProcess)</h1>
  <p class="sub">12 teams · Superflex value (roster players + draft picks) · DynastyProcess <code>value_2qb</code>–backed · weekly cadence · Season 1 startup (__FIRST__) → latest DP snapshot (__LAST__)</p>
  <div class="card">
    <div class="toolbar">
      <button id="metricTotal" class="on">Total value</button>
      <button id="metricPlayers">Players only</button>
      <button id="metricPicks">Picks only</button>
      <span class="spacer"></span>
      <button id="allOn">Show all</button>
      <button id="soloHint" title="Click a legend team to isolate it">Click a team to isolate</button>
      <button id="themeToggle">Toggle light/dark</button>
    </div>
    <div class="chartbox"><canvas id="chart"></canvas></div>
    <div class="legend" id="legend"></div>
    <p class="note">Value source: DynastyProcess Superflex <code>value_2qb</code>, taken from the WEEKLY git-history snapshots of <code>files/values.csv</code> (median 7-day step; one ~63-day offseason gap left as a line break, not fabricated). Each player's latest weekly value is forward-filled ≤7 days to render continuous lines (<code>dp_actual</code> / <code>forward_fill</code>); players outside DP's dynasty universe count 0 (<code>no_dp</code>). Pick values are DP per-slot picks aggregated to Early/Mid/Late tiers (<code>pick_tier</code>); classes DP does not publish (2028–2029, and pre-coverage windows of 2026/2027) are <code>dp_unavailable</code> = 0, never fabricated. Boundary markers = rookie drafts. Full method & coverage in RESULTS_dp.md.</p>
  </div>
</div>
<script>
const DATA = __PAYLOAD__;
const css = k => getComputedStyle(document.documentElement).getPropertyValue(k).trim();
let metric = "total";

function buildDatasets(){
  return DATA.datasets.map((d,i)=>({
    label:d.label, roster_id:d.roster_id,
    data:d[metric], borderColor:d.color, backgroundColor:d.color,
    borderWidth:2, pointRadius:0, pointHoverRadius:5, tension:0.12,
    spanGaps:true, _base:d.color,
  }));
}
const boundaryAnns = {};
DATA.boundaries.forEach((b,i)=>{ boundaryAnns["b"+i]={type:"line",xMin:b.date,xMax:b.date,
  borderColor:"rgba(140,140,140,.55)",borderWidth:1,borderDash:[4,4],
  label:{display:true,content:b.label,position:"start",rotation:-90,color:css('--muted'),
    font:{size:10},backgroundColor:"transparent"}}; });

const ctx = document.getElementById('chart');
const chart = new Chart(ctx,{
  type:"line",
  data:{labels:DATA.dates, datasets:buildDatasets()},
  options:{
    responsive:true, maintainAspectRatio:false, animation:false,
    interaction:{mode:"index", intersect:false},
    scales:{
      x:{type:"time", time:{unit:"month"}, grid:{color:css('--grid')},
         ticks:{color:css('--ink2'), maxRotation:0, autoSkip:true, maxTicksLimit:14}},
      y:{grid:{color:css('--grid')}, ticks:{color:css('--ink2'),
         callback:v=>(v/1000)+"k"}, title:{display:true,text:"DynastyProcess Superflex value_2qb",color:css('--muted')}}
    },
    plugins:{
      legend:{display:false},
      annotation:{annotations:boundaryAnns},
      tooltip:{
        backgroundColor:css('--panel'), titleColor:css('--ink'), bodyColor:css('--ink2'),
        borderColor:css('--grid'), borderWidth:1, padding:10, itemSort:(a,b)=>b.raw-a.raw,
        callbacks:{ label:c=>` ${c.dataset.label}: ${Number(c.raw).toLocaleString()}` }
      }
    }
  }
});

const legend = document.getElementById('legend');
let soloed = null;
DATA.datasets.forEach((d,i)=>{
  const item=document.createElement('div'); item.className='item'; item.dataset.i=i;
  item.innerHTML=`<span class="swatch" style="background:${d.color}"></span>${d.label}`;
  item.onclick=()=>{
    if(soloed===i){ soloed=null; chart.data.datasets.forEach((ds,k)=>{chart.setDatasetVisibility(k,true);}); }
    else { soloed=i; chart.data.datasets.forEach((ds,k)=>{chart.setDatasetVisibility(k,k===i);}); }
    syncLegend(); chart.update();
  };
  item.onmouseenter=()=>{ if(soloed===null){ chart.data.datasets.forEach((ds,k)=>{ds.borderColor=(k===i)?ds._base:"rgba(130,130,130,.18)";}); chart.update(); } };
  item.onmouseleave=()=>{ if(soloed===null){ chart.data.datasets.forEach(ds=>ds.borderColor=ds._base); chart.update(); } };
  legend.appendChild(item);
});
function syncLegend(){ [...legend.children].forEach((el,k)=>{
  const vis = chart.isDatasetVisible(k); el.classList.toggle('off', !vis);
}); }

document.getElementById('allOn').onclick=()=>{ soloed=null;
  chart.data.datasets.forEach((ds,k)=>{chart.setDatasetVisibility(k,true); ds.borderColor=ds._base;});
  syncLegend(); chart.update(); };

function setMetric(m,btn){ metric=m; chart.data.datasets=buildDatasets();
  if(soloed!==null){ chart.data.datasets.forEach((ds,k)=>chart.setDatasetVisibility(k,k===soloed)); }
  ["metricTotal","metricPlayers","metricPicks"].forEach(id=>document.getElementById(id).classList.remove('on'));
  btn.classList.add('on'); chart.update(); }
document.getElementById('metricTotal').onclick=e=>setMetric('total',e.target);
document.getElementById('metricPlayers').onclick=e=>setMetric('players',e.target);
document.getElementById('metricPicks').onclick=e=>setMetric('picks',e.target);

document.getElementById('themeToggle').onclick=()=>{
  const cur=document.documentElement.getAttribute('data-theme');
  document.documentElement.setAttribute('data-theme', cur==='light'?'dark':'light');
  chart.options.scales.x.grid.color=css('--grid'); chart.options.scales.y.grid.color=css('--grid');
  chart.options.scales.x.ticks.color=css('--ink2'); chart.options.scales.y.ticks.color=css('--ink2');
  chart.options.scales.y.title.color=css('--muted');
  Object.values(boundaryAnns).forEach(a=>a.label.color=css('--muted'));
  chart.update();
};
</script>
</body>
</html>
"""

out = os.path.join(HERE, "dynasty_value_over_time_dp.html")
with open(out, "w") as f:
    f.write(HTML.replace("__PAYLOAD__", json.dumps(payload))
                .replace("__FIRST__", first).replace("__LAST__", last))
print("wrote", out, "size", os.path.getsize(out), "bytes", "| DP-gap line-break days:", gap_days)
