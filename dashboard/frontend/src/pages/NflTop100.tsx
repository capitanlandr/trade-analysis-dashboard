import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  ListOrdered, Trophy, Users, AlertTriangle,
  Search, ChevronDown, ArrowUp, ArrowDown, ArrowUpDown, RotateCcw,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types (mirror scripts/generate_nfl_top100.py output)
// ---------------------------------------------------------------------------
interface Top100Player {
  rank: number;
  name: string;
  position: string;
  nflTeam: string;
}
interface RosteredPlayer extends Top100Player {
  fantasyTeam: string;
  manager: string;
  rosterId: number;
}
interface UnmatchedPlayer extends Top100Player {
  reason: string;
}
interface TeamCount {
  rosterId: number;
  fantasyTeam: string;
  manager: string;
  top100Count: number;
}
interface Top100Data {
  title: string;
  subtitle: string;
  generatedAt: string;
  source: string;
  sourceUrl: string;
  totalRanks: number;
  revealedCount: number;
  pendingCount: number;
  revealedRanks: number[];
  pendingRanks: number[];
  leagueId: string;
  players: Top100Player[];
  rostered: RosteredPlayer[];
  unmatched: UnmatchedPlayer[];
  teamCounts: TeamCount[];
  rosteredCount: number;
  unmatchedCount: number;
}

// ---------------------------------------------------------------------------
// Reusable multi-select dropdown (checkbox popover, no extra deps)
// ---------------------------------------------------------------------------
const MultiSelect: React.FC<{
  label: string;
  options: string[];
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
}> = ({ label, options, selected, onChange }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const toggle = (opt: string) => {
    const next = new Set(selected);
    if (next.has(opt)) next.delete(opt); else next.add(opt);
    onChange(next);
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-sm transition-colors ${
          selected.size > 0
            ? 'border-primary-400 bg-primary-50 text-primary-700'
            : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
        }`}
      >
        <span>{label}</span>
        {selected.size > 0 && (
          <span className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded-full bg-primary-600 text-white text-xs font-semibold">
            {selected.size}
          </span>
        )}
        <ChevronDown className="h-4 w-4 text-gray-400" />
      </button>
      {open && (
        <div className="absolute z-30 mt-1 w-56 max-h-72 overflow-auto bg-white border border-gray-200 rounded-md shadow-lg p-1">
          <div className="flex items-center justify-between px-2 py-1">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</span>
            {selected.size > 0 && (
              <button
                type="button"
                onClick={() => onChange(new Set())}
                className="text-xs text-primary-600 hover:underline"
              >
                Clear
              </button>
            )}
          </div>
          {options.map((opt) => (
            <label
              key={opt}
              className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-50 cursor-pointer text-sm text-gray-700"
            >
              <input
                type="checkbox"
                checked={selected.has(opt)}
                onChange={() => toggle(opt)}
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="truncate" title={opt || '(blank)'}>{opt || '(blank)'}</span>
            </label>
          ))}
          {options.length === 0 && (
            <div className="px-2 py-2 text-xs text-gray-400">No options</div>
          )}
        </div>
      )}
    </div>
  );
};

// Sortable column-header button.
type SortDir = 'asc' | 'desc';
const SortHeader: React.FC<{
  label: string;
  col: string;
  sortCol: string;
  sortDir: SortDir;
  onSort: (col: string) => void;
  align?: 'left' | 'right';
}> = ({ label, col, sortCol, sortDir, onSort, align = 'left' }) => {
  const active = sortCol === col;
  const Icon = active ? (sortDir === 'asc' ? ArrowUp : ArrowDown) : ArrowUpDown;
  return (
    <th className={`px-4 py-2 text-${align} text-xs font-medium text-gray-500 uppercase`}>
      <button
        type="button"
        onClick={() => onSort(col)}
        className={`inline-flex items-center gap-1 hover:text-gray-800 transition-colors ${
          active ? 'text-primary-700' : ''
        } ${align === 'right' ? 'flex-row-reverse' : ''}`}
      >
        <span>{label}</span>
        <Icon className="h-3.5 w-3.5" />
      </button>
    </th>
  );
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
const NflTop100: React.FC = () => {
  const [data, setData] = useState<Top100Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // --- Filter / sort state for the "Top-100 Players on Fantasy Rosters" table ---
  const [nameQuery, setNameQuery] = useState('');
  const [posFilter, setPosFilter] = useState<Set<string>>(new Set());
  const [nflFilter, setNflFilter] = useState<Set<string>>(new Set());
  const [teamFilter, setTeamFilter] = useState<Set<string>>(new Set());
  const [mgrFilter, setMgrFilter] = useState<Set<string>>(new Set());
  const [rankMin, setRankMin] = useState('');
  const [rankMax, setRankMax] = useState('');
  const [sortCol, setSortCol] = useState<string>('rank');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const rostered = data?.rostered ?? [];

  // Distinct option lists (sorted) for the multi-selects.
  const posOptions = useMemo(
    () => Array.from(new Set(rostered.map((p) => p.position).filter(Boolean))).sort(),
    [rostered],
  );
  const nflOptions = useMemo(
    () => Array.from(new Set(rostered.map((p) => p.nflTeam).filter(Boolean))).sort(),
    [rostered],
  );
  const teamOptions = useMemo(
    () => Array.from(new Set(rostered.map((p) => p.fantasyTeam).filter(Boolean))).sort(),
    [rostered],
  );
  const mgrOptions = useMemo(
    () => Array.from(new Set(rostered.map((p) => p.manager).filter(Boolean))).sort(),
    [rostered],
  );

  const filteredRostered = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    const lo = rankMin.trim() === '' ? null : parseInt(rankMin, 10);
    const hi = rankMax.trim() === '' ? null : parseInt(rankMax, 10);
    let rows = rostered.filter((p) => {
      if (q && !p.name.toLowerCase().includes(q)) return false;
      if (posFilter.size > 0 && !posFilter.has(p.position)) return false;
      if (nflFilter.size > 0 && !nflFilter.has(p.nflTeam)) return false;
      if (teamFilter.size > 0 && !teamFilter.has(p.fantasyTeam)) return false;
      if (mgrFilter.size > 0 && !mgrFilter.has(p.manager)) return false;
      if (lo !== null && !Number.isNaN(lo) && p.rank < lo) return false;
      if (hi !== null && !Number.isNaN(hi) && p.rank > hi) return false;
      return true;
    });
    const dir = sortDir === 'asc' ? 1 : -1;
    rows = [...rows].sort((a, b) => {
      let cmp = 0;
      if (sortCol === 'rank') cmp = a.rank - b.rank;
      else {
        const av = String(a[sortCol as keyof RosteredPlayer] ?? '');
        const bv = String(b[sortCol as keyof RosteredPlayer] ?? '');
        cmp = av.localeCompare(bv, undefined, { sensitivity: 'base' });
      }
      if (cmp === 0 && sortCol !== 'rank') cmp = a.rank - b.rank; // stable tiebreak by rank
      return cmp * dir;
    });
    return rows;
  }, [rostered, nameQuery, posFilter, nflFilter, teamFilter, mgrFilter, rankMin, rankMax, sortCol, sortDir]);

  const activeFilterCount =
    (nameQuery.trim() ? 1 : 0) + posFilter.size + nflFilter.size + teamFilter.size +
    mgrFilter.size + (rankMin.trim() ? 1 : 0) + (rankMax.trim() ? 1 : 0);

  const handleSort = (col: string) => {
    if (sortCol === col) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortCol(col);
      setSortDir(col === 'rank' ? 'asc' : 'asc');
    }
  };

  const resetFilters = () => {
    setNameQuery('');
    setPosFilter(new Set());
    setNflFilter(new Set());
    setTeamFilter(new Set());
    setMgrFilter(new Set());
    setRankMin('');
    setRankMax('');
    setSortCol('rank');
    setSortDir('asc');
  };

  useEffect(() => {
    fetch('/nfl-top-100.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: Top100Data) => setData(d))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load NFL Top 100 data'))
      .finally(() => setLoading(false));
  }, []);

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
          <h3 className="text-red-900 font-semibold mb-2">NFL Top 100 Not Available</h3>
          <p className="text-red-700 text-sm">{error || 'No data available'}</p>
          <p className="text-red-600 text-sm mt-2">
            Regenerate with <code>python3 scripts/generate_nfl_top100.py</code>.
          </p>
        </div>
      </div>
    );
  }

  const maxCount = data.teamCounts.reduce((m, t) => Math.max(m, t.top100Count), 0);
  const generated = data.generatedAt ? new Date(data.generatedAt).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true,
  }) : 'unknown';

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <ListOrdered className="h-7 w-7 text-primary-600" />
          {data.title}
        </h1>
        <p className="text-gray-600">{data.subtitle}</p>
        <p className="text-xs text-gray-400 mt-1">
          {data.revealedCount} of {data.totalRanks} ranks revealed
          {data.pendingCount > 0 && (
            <> • {data.pendingCount} not yet revealed (episodes still airing)</>
          )}
          {' '}• source:{' '}
          <a href={data.sourceUrl} target="_blank" rel="noopener noreferrer"
            className="text-primary-600 hover:underline">{data.source}</a>
          {' '}• updated {generated}
        </p>
      </div>

      {/* Pending banner */}
      {data.pendingCount > 0 && (
        <div className="mb-8 bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-amber-900">
            The 2026 list is revealed one episode at a time. Ranks{' '}
            <span className="font-semibold">
              {data.pendingRanks.length > 0
                ? `${Math.min(...data.pendingRanks)}–${Math.max(...data.pendingRanks)}`
                : ''}
            </span>{' '}
            are not yet public and are shown as pending — they refresh automatically as episodes air.
          </p>
        </div>
      )}

      {/* Per-fantasy-team Top-100 count summary */}
      <div className="mb-10">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Users className="h-5 w-5 text-primary-600" />
          Top-100 Players per Fantasy Team
        </h2>
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Fantasy Team</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Manager</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-1/2">Top-100 Players</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.teamCounts.map((t, idx) => (
                <tr key={t.rosterId} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-4 py-2 text-sm font-medium text-gray-900">{t.fantasyTeam}</td>
                  <td className="px-4 py-2 text-sm text-gray-600">{t.manager}</td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-3">
                      <div className="flex-1 bg-gray-100 rounded h-5 relative overflow-hidden max-w-xs">
                        <div className="bg-primary-500 h-5 rounded transition-all"
                          style={{ width: `${maxCount > 0 ? (t.top100Count / maxCount) * 100 : 0}%` }} />
                      </div>
                      <span className="text-sm font-bold text-gray-800 w-6 text-right">{t.top100Count}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ranked table of Top-100 players on fantasy teams — with filters + sorting */}
      <div className="mb-10">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Trophy className="h-5 w-5 text-primary-600" />
          Top-100 Players on Fantasy Rosters
          <span className="text-sm font-normal text-gray-400">
            ({filteredRostered.length}
            {filteredRostered.length !== data.rosteredCount && ` of ${data.rosteredCount}`})
          </span>
        </h2>

        {/* Filter bar */}
        <div className="bg-white rounded-lg shadow p-4 mb-3">
          <div className="flex flex-wrap items-center gap-3">
            {/* Player name search */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={nameQuery}
                onChange={(e) => setNameQuery(e.target.value)}
                placeholder="Search player name…"
                className="pl-8 pr-3 py-1.5 w-56 rounded-md border border-gray-300 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            <MultiSelect label="Position" options={posOptions} selected={posFilter} onChange={setPosFilter} />
            <MultiSelect label="NFL Team" options={nflOptions} selected={nflFilter} onChange={setNflFilter} />
            <MultiSelect label="Fantasy Team" options={teamOptions} selected={teamFilter} onChange={setTeamFilter} />
            <MultiSelect label="Manager" options={mgrOptions} selected={mgrFilter} onChange={setMgrFilter} />

            {/* Rank range */}
            <div className="flex items-center gap-1.5 text-sm text-gray-600">
              <span className="text-gray-500">Rank</span>
              <input
                type="number" inputMode="numeric" min={1} max={data.totalRanks}
                value={rankMin}
                onChange={(e) => setRankMin(e.target.value)}
                placeholder="min"
                className="w-16 px-2 py-1.5 rounded-md border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <span className="text-gray-400">–</span>
              <input
                type="number" inputMode="numeric" min={1} max={data.totalRanks}
                value={rankMax}
                onChange={(e) => setRankMax(e.target.value)}
                placeholder="max"
                className="w-16 px-2 py-1.5 rounded-md border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {activeFilterCount > 0 && (
              <button
                type="button"
                onClick={resetFilters}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
              >
                <RotateCcw className="h-4 w-4" />
                Reset ({activeFilterCount})
              </button>
            )}
          </div>

          {/* Rank quick-range chips (creative rank filtering) */}
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">Quick rank:</span>
            {[
              { label: 'Top 10', lo: 1, hi: 10 },
              { label: 'Top 25', lo: 1, hi: 25 },
              { label: 'Top 50', lo: 1, hi: 50 },
              { label: '51–100', lo: 51, hi: 100 },
            ].map((r) => {
              const activeChip = rankMin === String(r.lo) && rankMax === String(r.hi);
              return (
                <button
                  key={r.label}
                  type="button"
                  onClick={() => {
                    if (activeChip) { setRankMin(''); setRankMax(''); }
                    else { setRankMin(String(r.lo)); setRankMax(String(r.hi)); }
                  }}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                    activeChip
                      ? 'border-primary-500 bg-primary-600 text-white'
                      : 'border-gray-300 bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {r.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <SortHeader label="Rank" col="rank" sortCol={sortCol} sortDir={sortDir} onSort={handleSort} />
                <SortHeader label="Player" col="name" sortCol={sortCol} sortDir={sortDir} onSort={handleSort} />
                <SortHeader label="Pos" col="position" sortCol={sortCol} sortDir={sortDir} onSort={handleSort} />
                <SortHeader label="NFL Team" col="nflTeam" sortCol={sortCol} sortDir={sortDir} onSort={handleSort} />
                <SortHeader label="Fantasy Team" col="fantasyTeam" sortCol={sortCol} sortDir={sortDir} onSort={handleSort} />
                <SortHeader label="Manager" col="manager" sortCol={sortCol} sortDir={sortDir} onSort={handleSort} />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredRostered.map((p, idx) => (
                <tr key={`${p.rank}-${p.name}`} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-4 py-2 text-sm font-bold text-primary-700">#{p.rank}</td>
                  <td className="px-4 py-2 text-sm font-medium text-gray-900">{p.name}</td>
                  <td className="px-4 py-2 text-sm text-gray-600">{p.position}</td>
                  <td className="px-4 py-2 text-sm text-gray-600">{p.nflTeam}</td>
                  <td className="px-4 py-2 text-sm text-gray-900">{p.fantasyTeam}</td>
                  <td className="px-4 py-2 text-sm text-gray-600">{p.manager}</td>
                </tr>
              ))}
              {filteredRostered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                    No players match the current filters.
                    <button type="button" onClick={resetFilters} className="ml-2 text-primary-600 hover:underline">
                      Reset filters
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Flagged: revealed Top-100 players NOT on any fantasy roster */}
      {data.unmatched.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-600" />
            Top-100 Players Not on Any Fantasy Roster
            <span className="text-sm font-normal text-gray-400">({data.unmatchedCount})</span>
          </h2>
          <p className="text-sm text-gray-500 mb-3">
            These revealed Top-100 players are flagged because they are not rostered in this league
            (typically defensive players or free agents in a skill-position dynasty league).
          </p>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Rank</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Player</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Pos</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">NFL Team</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.unmatched.map((p) => (
                  <tr key={`${p.rank}-${p.name}`}>
                    <td className="px-4 py-2 text-sm font-bold text-gray-500">#{p.rank}</td>
                    <td className="px-4 py-2 text-sm text-gray-700">{p.name}</td>
                    <td className="px-4 py-2 text-sm text-gray-500">{p.position}</td>
                    <td className="px-4 py-2 text-sm text-gray-500">{p.nflTeam}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default NflTop100;
