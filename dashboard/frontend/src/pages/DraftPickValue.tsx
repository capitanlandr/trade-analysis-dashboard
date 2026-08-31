import React, { useEffect, useMemo, useState } from 'react';
import {
  TrendingUp, TrendingDown, Minus, AlertTriangle, Layers,
  GitCompareArrows, Trophy, Users, LineChart,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types — mirror FILE 2 of the draft-value CONTRACT (analysis.json).
// ---------------------------------------------------------------------------
type Verdict = 'APPRECIATED' | 'FLAT' | 'DECLINED';

interface SeriesPoint {
  date: string;
  value: number | null;
  kind: 'pick' | 'player';
  cohort_index: number;
}
interface PickPlayer {
  name: string;
  sleeper_id?: string;
  fp_id?: string;
  pos: string;
  nfl_team: string;
  age_now: number | null;
}
interface Pick {
  pick_label: string;
  round: number;
  slot: number;
  overall: number;
  owner_roster_id?: number;
  owner_team: string;
  player: PickPlayer;
  pre_draft_pick_value: number;
  latest_player_value: number | null;
  abs_delta: number;
  abs_pct: number;
  rel_delta: number;
  rank_pre: number;
  rank_latest: number;
  rank_change: number;
  verdict_absolute: Verdict;
  verdict_relative: Verdict;
  divergence: boolean;
  series: SeriesPoint[];
}
type SortKey = 'overall' | 'player' | 'pre' | 'now' | 'abs' | 'rel' | 'rank';

interface WindowStat {
  from: string;
  to: string;
  median_pct: number;
  mean_pct: number;
  min_pct: number;
  max_pct: number;
}
interface WindowSplit {
  fa_window: WindowStat;
  draft_window: WindowStat;
  ratio_draft_over_fa: number;
  verdict: string;
}

interface RoundAgg {
  round: number;
  count: number;
  mean_abs_pct: number;
  median_abs_pct: number;
  mean_rel_delta: number;
  median_rel_delta: number;
  share_appreciating: number;
  dips: boolean;
}
interface PositionAgg {
  pos: string;
  count: number;
  mean_abs_pct: number;
  median_abs_pct: number;
  mean_rel_delta: number;
  median_rel_delta: number;
  share_appreciating: number;
}
interface ClassIndexPoint {
  date: string;
  cohort_index: number;
  kind?: string;
}
interface AnalysisData {
  meta: {
    draft_id: string;
    draft_started_utc?: string;
    value_column: string;
    pre_draft_snapshot: { date: string; sha: string };
    post_draft_snapshot: { date: string; sha: string };
    snapshot_dates: string[];
    baseline_date: string;
    baseline_days_before_draft: number;
    baseline_predates_free_agency?: boolean;
    gap_note: string;
    cohort_index_pre?: number;
    cohort_index_latest?: number;
    is_fixture?: boolean;
    generated_utc: string;
    picks_excluded_no_ktc_data?: string[];
    picks_shown?: number;
    // Health of the upstream daily refresh. Drives the stale-data banner.
    refresh_status?: {
      degraded: boolean;
      data_age_days?: number | null;
      last_attempt_utc?: string | null;
      last_success_date?: string | null;
      errors?: string[];
      data_through?: string | null;
    };
  };
  picks: Pick[];
  per_round: RoundAgg[];
  round1_dips: boolean;
  round1_note: string;
  per_position: PositionAgg[];
  class_index_series: ClassIndexPoint[];
  window_split?: WindowSplit;
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------
const fmt = (n: number | null | undefined, digits = 0) =>
  n === null || n === undefined || Number.isNaN(n)
    ? '—'
    : n.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits });

const pct = (n: number | null | undefined) =>
  n === null || n === undefined || Number.isNaN(n) ? '—' : `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;

const verdictStyle: Record<Verdict, string> = {
  APPRECIATED: 'bg-green-100 text-green-800',
  FLAT: 'bg-gray-100 text-gray-700',
  DECLINED: 'bg-red-100 text-red-800',
};
const VerdictIcon: React.FC<{ v: Verdict; className?: string }> = ({ v, className }) => {
  if (v === 'APPRECIATED') return <TrendingUp className={className} />;
  if (v === 'DECLINED') return <TrendingDown className={className} />;
  return <Minus className={className} />;
};
const VerdictPill: React.FC<{ v: Verdict }> = ({ v }) => (
  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${verdictStyle[v]}`}>
    <VerdictIcon v={v} className="h-3 w-3" />
    {v.charAt(0) + v.slice(1).toLowerCase()}
  </span>
);

// Percentage cell tinted by sign.
const DeltaCell: React.FC<{ value: number; sub?: string }> = ({ value, sub }) => {
  const color = value > 5 ? 'text-green-700' : value < -5 ? 'text-red-700' : 'text-gray-600';
  return (
    <div className="flex flex-col">
      <span className={`text-sm font-semibold ${color}`}>{pct(value)}</span>
      {sub && <span className="text-xs text-gray-400">{sub}</span>}
    </div>
  );
};

// Inline SVG line chart for the class-index series (no external chart lib —
// the existing pages render charts as inline SVG / CSS bars, so we match that).
const ClassIndexChart: React.FC<{ series: ClassIndexPoint[] }> = ({ series }) => {
  if (series.length === 0) return null;
  const W = 640, H = 200, PAD = 40;
  const vals = series.map((p) => p.cohort_index);
  const min = Math.min(...vals), max = Math.max(...vals);
  const span = max - min || 1;
  const x = (i: number) => PAD + (series.length === 1 ? (W - 2 * PAD) / 2 : (i / (series.length - 1)) * (W - 2 * PAD));
  const y = (v: number) => H - PAD - ((v - min) / span) * (H - 2 * PAD);
  const line = series.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i).toFixed(1)} ${y(p.cohort_index).toFixed(1)}`).join(' ');
  const first = series[0].cohort_index, last = series[series.length - 1].cohort_index;
  const netPct = ((last - first) / first) * 100;

  return (
    <div>
      <div className="flex items-baseline gap-3 mb-2">
        <span className={`text-2xl font-bold ${netPct < -1 ? 'text-red-700' : netPct > 1 ? 'text-green-700' : 'text-gray-700'}`}>
          {pct(netPct)}
        </span>
        <span className="text-sm text-gray-500">
          class median moved from {fmt(first)} to {fmt(last)} ({netPct < 0 ? 'deflation' : 'inflation'})
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Class index over time">
        {/* baseline grid */}
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#e5e7eb" strokeWidth={1} />
        <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="#e5e7eb" strokeWidth={1} />
        <path d={line} fill="none" stroke="#7c3aed" strokeWidth={2.5} />
        {series.map((p, i) => (
          <g key={p.date}>
            <circle cx={x(i)} cy={y(p.cohort_index)} r={4} fill="#7c3aed" />
            <text x={x(i)} y={y(p.cohort_index) - 10} textAnchor="middle" className="fill-gray-700" fontSize={11} fontWeight={600}>
              {fmt(p.cohort_index)}
            </text>
            <text x={x(i)} y={H - PAD + 16} textAnchor="middle" className="fill-gray-500" fontSize={10}>
              {p.date}{p.kind ? ` (${p.kind})` : ''}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
const DraftPickValue: React.FC = () => {
  const [data, setData] = useState<AnalysisData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [onlyDivergent, setOnlyDivergent] = useState(false);
  // Both datasets are KeepTradeCut. They differ in BASELINE KIND, not source:
  //   2026 = pick-tier value the day before the draft (12 shared tier baselines)
  //   2025 = each rookie's own pre-draft PROSPECT value (48 distinct baselines)
  // KTC retires pick assets after a draft, so no 2025 tier history exists. That
  // makes 2025 higher-resolution but a slightly different question, which the
  // banner states rather than glossing.
  const [season, setSeason] = useState<'2026' | '2025'>('2026');
  const [roundFilter, setRoundFilter] = useState<number | 'all'>('all');
  const [posFilter, setPosFilter] = useState<string>('all');
  const [verdictFilter, setVerdictFilter] = useState<'all' | 'APPRECIATED' | 'FLAT' | 'DECLINED'>('all');
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('overall');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const toggleSort = (k: SortKey) => {
    if (k === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(k);
      // numeric deltas are most useful biggest-first; identifiers ascending
      setSortDir(k === 'overall' || k === 'player' ? 'asc' : 'desc');
    }
  };

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(season === '2025' ? '/ktc-analysis-2025.json' : '/ktc-analysis.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: AnalysisData) => setData(d))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load draft-value analysis'))
      .finally(() => setLoading(false));
  }, [season]);

  const picks = data?.picks ?? [];
  const divergentCount = useMemo(() => picks.filter((p) => p.divergence).length, [picks]);
  const visiblePicks = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = picks.filter((p) => {
      if (onlyDivergent && !p.divergence) return false;
      if (roundFilter !== 'all' && p.round !== roundFilter) return false;
      if (posFilter !== 'all' && p.player.pos !== posFilter) return false;
      if (verdictFilter !== 'all' && p.verdict_absolute !== verdictFilter) return false;
      if (q) {
        const hay = `${p.player.name} ${p.pick_label} ${p.owner_team} ${p.player.pos} ${p.player.nfl_team}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    const val = (p: Pick): number | string => {
      switch (sortKey) {
        case 'player': return p.player.name;
        case 'pre': return p.pre_draft_pick_value ?? -Infinity;
        case 'now': return p.latest_player_value ?? -Infinity;
        case 'abs': return p.abs_pct ?? -Infinity;
        case 'rel': return p.rel_delta ?? -Infinity;
        case 'rank': return p.rank_change ?? -Infinity;
        default: return p.overall;
      }
    };
    return rows.slice().sort((a, b) => {
      const av = val(a), bv = val(b);
      const c = typeof av === 'string' || typeof bv === 'string'
        ? String(av).localeCompare(String(bv))
        : (av as number) - (bv as number);
      return sortDir === 'asc' ? c : -c;
    });
  }, [picks, onlyDivergent, roundFilter, posFilter, verdictFilter, query, sortKey, sortDir]);

  const positions = useMemo(
    () => Array.from(new Set(picks.map((p) => p.player.pos).filter(Boolean))).sort(),
    [picks],
  );

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3" />
          <div className="h-4 bg-gray-200 rounded w-1/2" />
          {[...Array(6)].map((_, i) => <div key={i} className="h-16 bg-gray-200 rounded" />)}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-red-900 font-semibold mb-2">Draft Pick Value Not Available</h3>
          <p className="text-red-700 text-sm">{error || 'No data available'}</p>
          <p className="text-red-600 text-sm mt-2">
            Expected <code>/analysis.json</code> in <code>dashboard/frontend/public/</code>.
          </p>
        </div>
      </div>
    );
  }

  const { meta, per_round, per_position, class_index_series } = data;
  const generated = meta.generated_utc
    ? new Date(meta.generated_utc).toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true,
      })
    : 'unknown';

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <Layers className="h-7 w-7 text-primary-600" />
          Draft Pick Value
          {meta.is_fixture && (
            <span className="text-xs font-semibold uppercase tracking-wide bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
              Fixture data
            </span>
          )}
        </h1>
        <p className="text-gray-600">
          How the {season} rookie draft&apos;s picks converted into player value: absolute change
          vs cohort-relative change (share of class total, which is scale-free).
        </p>
        <p className="text-xs text-gray-400 mt-1">
          value column <code>{meta.value_column}</code> • pre-draft {meta.pre_draft_snapshot.date} →
          post-draft {meta.post_draft_snapshot.date} • updated {generated}
        </p>

        {/* Season toggle — both datasets are KeepTradeCut, different baseline kinds */}
        <div className="mt-4 flex items-center gap-3 flex-wrap">
          <span className="text-sm font-medium text-gray-700">Dataset:</span>
          <div className="inline-flex rounded-lg border border-gray-300 overflow-hidden">
            {([['2026', 'Keep Trade Cut 2026'], ['2025', 'Keep Trade Cut 2025']] as const).map(
              ([k, label]) => (
                <button
                  key={k}
                  onClick={() => setSeason(k)}
                  aria-pressed={season === k}
                  className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                    season === k
                      ? 'bg-primary-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {label}
                </button>
              ),
            )}
          </div>
          <span className="text-xs text-gray-500">
            {season === '2026'
              ? 'Baseline = pick-tier value the day before the draft. 4 months of hindsight.'
              : 'Baseline = each rookie\u2019s own pre-draft prospect value. A full year of hindsight.'}
          </span>
        </div>
      </div>

      {/* Stale-data warning. Driven by meta.refresh_status so a failed upstream
          refresh can never leave the tab quietly looking current. */}
      {meta.refresh_status?.degraded && (
        <div className="mb-6 bg-red-50 border-2 border-red-300 rounded-lg p-4 flex items-start gap-2">
          <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-red-900">
            <p className="font-semibold">
              Stale data: showing values through {meta.refresh_status.data_through}
              {typeof meta.refresh_status.data_age_days === 'number' &&
                ` (${meta.refresh_status.data_age_days} days old)`}
              .
            </p>
            <p className="mt-1">
              The daily KeepTradeCut refresh did not complete, so these are the last good numbers
              rather than today&apos;s. Last attempt{' '}
              {meta.refresh_status.last_attempt_utc?.slice(0, 16).replace('T', ' ')} UTC.
            </p>
            {!!meta.refresh_status.errors?.length && (
              <ul className="mt-2 list-disc list-inside text-xs">
                {meta.refresh_status.errors.map((e: string, i: number) => <li key={i}>{e}</li>)}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Free agency vs draft split — KTC only, the answer to the draft-timing debate */}
      {data.window_split && (
        <div className="mb-8 bg-white border-2 border-primary-200 rounded-lg p-5">
          <h2 className="text-lg font-bold text-gray-900 mb-1">
            {season === '2026'
              ? 'Does free agency actually move pick value?'
              : 'Pre-draft prospect drift vs the draft itself'}
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            {season === '2026'
              ? 'KTC has a draft-day snapshot, so the window splits cleanly. DynastyProcess cannot do this.'
              : 'Caution: the 2025 baseline is PROSPECT value, so the first window captures pre-draft hype building toward the NFL draft, not free agency moving pick prices. It is not comparable to the 2026 panel.'}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-lg bg-gray-50 p-4">
              <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                {season === '2026' ? 'Free agency window' : 'Pre-draft window'}
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {data.window_split.fa_window.median_pct > 0 ? '+' : ''}
                {data.window_split.fa_window.median_pct}%
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {data.window_split.fa_window.from} → {data.window_split.fa_window.to}
                <br />range {data.window_split.fa_window.min_pct}% to{' '}
                {data.window_split.fa_window.max_pct}%
              </div>
            </div>
            <div className="rounded-lg bg-gray-50 p-4">
              <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                Draft window
              </div>
              <div className="text-2xl font-bold text-red-600">
                {data.window_split.draft_window.median_pct}%
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {data.window_split.draft_window.from} → {data.window_split.draft_window.to}
                <br />range {data.window_split.draft_window.min_pct}% to{' '}
                {data.window_split.draft_window.max_pct}%
              </div>
            </div>
            <div className="rounded-lg bg-primary-50 p-4">
              <div className="text-xs uppercase tracking-wide text-primary-700 mb-1">
                Draft moves value
              </div>
              <div className="text-2xl font-bold text-primary-700">
                {data.window_split.ratio_draft_over_fa}×
              </div>
              <div className="text-xs text-primary-700 mt-1">more than free agency does</div>
            </div>
          </div>
          <p className="mt-4 text-sm text-gray-800 bg-gray-50 rounded p-3">
            {data.window_split.verdict}
          </p>
        </div>
      )}

      <div className="hidden">
        <p className="text-xs text-gray-400 mt-1">
          updated {generated}
        </p>
      </div>

      {/* Caveat banner — source-aware */}
      <div className="mb-8 bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-2">
        <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-amber-900">
          {(meta.baseline_days_before_draft ?? 0) <= 2 ? (
            <>
              <p className="font-semibold">
                Baseline: {meta.baseline_date}, the day before the draft.
              </p>
              <p className="mt-1">
                {meta.gap_note}
              </p>
            </>
          ) : (
            <>
              <p className="font-semibold">
                Baseline caveat: the pre-draft snapshot is {meta.baseline_date}.
              </p>
              <p className="mt-1">
                That is{' '}
                <span className="font-semibold">
                  {meta.baseline_days_before_draft} days before
                </span>{' '}
                the draft started ({meta.draft_started_utc?.slice(0, 10)}) and it also predates NFL
                free agency. {meta.gap_note} Free agency and the draft cannot be separated in this
                window.
              </p>
            </>
          )}

          {!!meta.picks_excluded_no_ktc_data?.length && (
            <p className="mt-3 pt-3 border-t border-amber-200">
              <span className="font-semibold">
                No KeepTradeCut data for {meta.picks_excluded_no_ktc_data.length} picks
              </span>{' '}
              — KTC never tracked a dynasty value for these players, so they are excluded rather
              than shown as zero: {meta.picks_excluded_no_ktc_data.join(', ')}. All four are late
              fourth-rounders, which means{' '}
              <span className="font-semibold">round 4 below reflects 8 of 12 picks</span> and its
              positive numbers carry survivorship bias: the untracked players are the ones that
              never became fantasy-relevant.
            </p>
          )}
        </div>
      </div>

      {/* Summary metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="card">
          <p className="text-sm font-medium text-gray-600">Picks analyzed</p>
          <p className="text-2xl font-bold text-gray-900">{picks.length}</p>
          <p className="text-xs text-gray-500">4 rounds × 12 teams</p>
        </div>
        <div className="card">
          <p className="text-sm font-medium text-gray-600 flex items-center gap-1">
            <GitCompareArrows className="h-4 w-4 text-purple-600" /> Divergent verdicts
          </p>
          <p className="text-2xl font-bold text-gray-900">{divergentCount}</p>
          <p className="text-xs text-gray-500">absolute and cohort-relative disagree</p>
        </div>
        <div className="card">
          <p className="text-sm font-medium text-gray-600">Round 1 systematic dip?</p>
          <p className={`text-2xl font-bold ${data.round1_dips ? 'text-red-700' : 'text-green-700'}`}>
            {data.round1_dips ? 'Yes (absolute)' : 'No'}
          </p>
          <p className="text-xs text-gray-500">see per-round rollup below</p>
        </div>
      </div>

      {/* Class index line */}
      <div className="mb-10">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <LineChart className="h-5 w-5 text-primary-600" />
          Class Index Over Time
        </h2>
        <div className="bg-white rounded-lg shadow p-5">
          <p className="text-sm text-gray-500 mb-3">
            Median <code>{meta.value_column}</code> across all 48 picks/players at each snapshot. This is the
            deflator: the cohort-relative column below divides each pick's movement by this line's movement, so
            a pick that fell only because the whole class fell reads as flat.
          </p>
          <ClassIndexChart series={class_index_series} />
        </div>
      </div>

      {/* Per-round rollup — REQUIRED (does round 1 dip?) */}
      <div className="mb-10">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Trophy className="h-5 w-5 text-primary-600" />
          Per-Round Rollup
        </h2>
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Round</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Picks</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Median Abs %</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Mean Abs %</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Median Rel Δ</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Share Appreciating</th>
                <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">Dips?</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {per_round.map((r, idx) => (
                <tr key={r.round} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-4 py-2 text-sm font-bold text-primary-700">Round {r.round}</td>
                  <td className="px-4 py-2 text-sm text-gray-600 text-right">{r.count}</td>
                  <td className="px-4 py-2 text-right"><DeltaCell value={r.median_abs_pct} /></td>
                  <td className="px-4 py-2 text-right"><DeltaCell value={r.mean_abs_pct} /></td>
                  <td className="px-4 py-2 text-right"><DeltaCell value={r.median_rel_delta} /></td>
                  <td className="px-4 py-2 text-sm text-gray-700 text-right">{(r.share_appreciating * 100).toFixed(0)}%</td>
                  <td className="px-4 py-2 text-center">
                    {r.dips ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800">
                        <TrendingDown className="h-3 w-3" /> Dips
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-600">
                        No
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 bg-primary-50 border border-primary-100 rounded-lg p-3 text-sm text-primary-900">
          {data.round1_note}
        </div>
      </div>

      {/* Per-position rollup */}
      {per_position.length > 0 && (
        <div className="mb-10">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Users className="h-5 w-5 text-primary-600" />
            Per-Position Rollup
          </h2>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Position</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Count</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Median Abs %</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Median Rel Δ</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Share Appreciating</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {per_position.map((p, idx) => (
                  <tr key={p.pos} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-4 py-2 text-sm font-semibold text-gray-900">{p.pos}</td>
                    <td className="px-4 py-2 text-sm text-gray-600 text-right">{p.count}</td>
                    <td className="px-4 py-2 text-right"><DeltaCell value={p.median_abs_pct} /></td>
                    <td className="px-4 py-2 text-right"><DeltaCell value={p.median_rel_delta} /></td>
                    <td className="px-4 py-2 text-sm text-gray-700 text-right">{(p.share_appreciating * 100).toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pick → player conversion table — REQUIRED */}
      <div className="mb-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <GitCompareArrows className="h-5 w-5 text-primary-600" />
            Pick → Player Conversion
            <span className="text-sm font-normal text-gray-400">
              ({visiblePicks.length}{visiblePicks.length !== picks.length && ` of ${picks.length}`})
            </span>
          </h2>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={onlyDivergent}
              onChange={(e) => setOnlyDivergent(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            Only rows where absolute & relative disagree ({divergentCount})
          </label>
        </div>

        <p className="text-sm text-gray-500 mb-3">
          <span className="font-semibold text-gray-700">Absolute</span> is raw pre-draft pick value → latest
          player value. <span className="font-semibold text-gray-700">Cohort-relative</span> divides out
          class-wide movement. They sit side by side so divergence is obvious; a
          <span className="inline-flex items-center gap-1 mx-1 px-1.5 py-0.5 rounded bg-purple-100 text-purple-800 text-xs font-semibold align-middle">
            <GitCompareArrows className="h-3 w-3" /> diverges
          </span>
          badge flags the rows where the two verdicts disagree.
        </p>

        {/* Filter bar */}
        <div className="bg-white rounded-lg shadow p-3 mb-3 flex flex-wrap items-center gap-3">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search player, pick, team…"
            aria-label="Search picks"
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500 min-w-[200px]"
          />
          <label className="text-sm text-gray-600 flex items-center gap-1.5">
            Round
            <select
              value={roundFilter}
              onChange={(e) => setRoundFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))}
              className="px-2 py-1.5 text-sm border border-gray-300 rounded-md"
            >
              <option value="all">All</option>
              {[1, 2, 3, 4].map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
          <label className="text-sm text-gray-600 flex items-center gap-1.5">
            Position
            <select
              value={posFilter}
              onChange={(e) => setPosFilter(e.target.value)}
              className="px-2 py-1.5 text-sm border border-gray-300 rounded-md"
            >
              <option value="all">All</option>
              {positions.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </label>
          <label className="text-sm text-gray-600 flex items-center gap-1.5">
            Verdict
            <select
              value={verdictFilter}
              onChange={(e) => setVerdictFilter(e.target.value as typeof verdictFilter)}
              className="px-2 py-1.5 text-sm border border-gray-300 rounded-md"
            >
              <option value="all">All</option>
              <option value="APPRECIATED">Appreciated</option>
              <option value="FLAT">Flat</option>
              <option value="DECLINED">Declined</option>
            </select>
          </label>
          {(query || roundFilter !== 'all' || posFilter !== 'all' || verdictFilter !== 'all' || onlyDivergent) && (
            <button
              onClick={() => {
                setQuery(''); setRoundFilter('all'); setPosFilter('all');
                setVerdictFilter('all'); setOnlyDivergent(false);
              }}
              className="px-3 py-1.5 text-sm font-medium text-primary-700 hover:bg-primary-50 rounded-md"
            >
              Clear filters
            </button>
          )}
          <span className="text-xs text-gray-400 ml-auto">Click any column header to sort</span>
        </div>

        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {([
                  ['overall', 'Pick', 'left', ''],
                  ['player', 'Player', 'left', ''],
                  ['pre', 'Pre-draft pick val', 'right', ''],
                  ['now', 'Current player val', 'right', ''],
                  ['abs', 'Absolute Δ', 'right', 'text-purple-600 bg-purple-50/60'],
                  ['rel', 'Cohort-relative Δ', 'right', 'text-indigo-600 bg-indigo-50/60'],
                  ['rank', 'Rank Δ', 'center', ''],
                ] as const).map(([key, label, align, extra]) => (
                  <th
                    key={key}
                    onClick={() => toggleSort(key)}
                    aria-sort={sortKey === key ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                    className={`px-3 py-2 text-${align} text-xs font-medium uppercase cursor-pointer select-none hover:bg-gray-100 transition-colors ${extra || 'text-gray-500'}`}
                  >
                    {label}
                    <span className={`ml-1 ${sortKey === key ? 'opacity-100' : 'opacity-25'}`}>
                      {sortKey === key ? (sortDir === 'asc' ? '▲' : '▼') : '▲'}
                    </span>
                  </th>
                ))}
                <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Flag</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {visiblePicks.map((p, idx) => (
                <tr
                  key={p.overall}
                  className={`${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} ${p.divergence ? 'ring-1 ring-inset ring-purple-200' : ''}`}
                >
                  <td className="px-3 py-2 whitespace-nowrap">
                    <div className="text-sm font-bold text-primary-700">{p.pick_label}</div>
                    <div className="text-xs text-gray-400">#{p.overall} • {p.owner_team}</div>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{p.player.name}</div>
                    <div className="text-xs text-gray-500">
                      {p.player.pos} • {p.player.nfl_team}
                      {p.player.age_now != null && ` • ${p.player.age_now}y`}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right text-sm text-gray-700">{fmt(p.pre_draft_pick_value)}</td>
                  <td className="px-3 py-2 text-right text-sm text-gray-900 font-medium">{fmt(p.latest_player_value)}</td>

                  {/* Absolute */}
                  <td className="px-3 py-2 text-right bg-purple-50/40">
                    <div className="flex flex-col items-end gap-1">
                      <DeltaCell value={p.abs_pct} sub={`${p.abs_delta > 0 ? '+' : ''}${fmt(p.abs_delta)} pts`} />
                      <VerdictPill v={p.verdict_absolute} />
                    </div>
                  </td>
                  {/* Cohort-relative */}
                  <td className="px-3 py-2 text-right bg-indigo-50/40">
                    <div className="flex flex-col items-end gap-1">
                      <DeltaCell value={p.rel_delta} />
                      <VerdictPill v={p.verdict_relative} />
                    </div>
                  </td>

                  <td className="px-3 py-2 text-center text-sm">
                    {p.rank_change === 0 ? (
                      <span className="text-gray-400">—</span>
                    ) : (
                      <span className={p.rank_change > 0 ? 'text-green-700 font-semibold' : 'text-red-700 font-semibold'}>
                        {p.rank_change > 0 ? `▲ ${p.rank_change}` : `▼ ${Math.abs(p.rank_change)}`}
                      </span>
                    )}
                    <div className="text-xs text-gray-400">#{p.rank_pre}→#{p.rank_latest}</div>
                  </td>
                  <td className="px-3 py-2 text-center">
                    {p.divergence && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800">
                        <GitCompareArrows className="h-3 w-3" /> diverges
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {visiblePicks.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-400">
                    No picks match the current filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DraftPickValue;
