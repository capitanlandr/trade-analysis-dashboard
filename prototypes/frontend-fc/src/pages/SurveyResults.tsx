import React, { useEffect, useState } from 'react';
import { ClipboardList, Trophy, TrendingDown, TrendingUp } from 'lucide-react';

// ---------------------------------------------------------------------------
// Types (mirror scripts/generate_survey_results.py output)
// ---------------------------------------------------------------------------
interface Placement { place: string; count: number; }
interface SurveyTeam {
  team: string;
  team_short: string;
  avg_predicted_rank: number | null;
  first_place_votes: number;
  first_place_pct: number;
  placements: Placement[];
  responses: number;
  consensus_seed: number;
}
interface SurveyDivision {
  division: string;
  teams: SurveyTeam[];
  consensus_favorite: string;
}
interface PickResult { label: string; count: number; pct: number; }
interface PickQuestion {
  question: string;
  multi_select: boolean;
  note: string | null;
  responses: number;
  top_answer: string | null;
  top_pct: number | null;
  results: PickResult[];
}
interface SurveyData {
  title: string;
  subtitle: string;
  total_responses: number;
  divisions: SurveyDivision[];
  pick_questions: PickQuestion[];
  insights: string[];
}

// ---------------------------------------------------------------------------
// Small presentational helpers
// ---------------------------------------------------------------------------
const BarRow: React.FC<{ label: string; count: number; pct: number; max: number }> = ({
  label, count, pct, max,
}) => (
  <div className="flex items-center gap-3 py-1">
    <div className="w-48 flex-shrink-0 text-sm text-gray-700 truncate" title={label}>{label}</div>
    <div className="flex-1 bg-gray-100 rounded h-6 relative overflow-hidden">
      <div
        className="bg-primary-500 h-6 rounded transition-all"
        style={{ width: `${max > 0 ? (count / max) * 100 : 0}%` }}
      />
      <span className="absolute inset-y-0 left-2 flex items-center text-xs font-medium text-gray-800">
        {count} ({pct}%)
      </span>
    </div>
  </div>
);

const iconForQuestion = (q: string) => {
  const s = q.toLowerCase();
  if (s.includes('championship')) return Trophy;
  if (s.includes('miss')) return TrendingDown;
  if (s.includes('make')) return TrendingUp;
  return ClipboardList;
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
const SurveyResults: React.FC = () => {
  const [data, setData] = useState<SurveyData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/survey-results.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: SurveyData) => setData(d))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load survey data'))
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
          <h3 className="text-red-900 font-semibold mb-2">Survey Results Not Available</h3>
          <p className="text-red-700 text-sm">{error || 'No data available'}</p>
          <p className="text-red-600 text-sm mt-2">
            Regenerate with <code>python3 scripts/generate_survey_results.py</code>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <ClipboardList className="h-7 w-7 text-primary-600" />
          {data.title}
        </h1>
        <p className="text-gray-600">
          {data.subtitle} • {data.total_responses} responses
        </p>
      </div>

      {/* Headline insights */}
      {data.insights.length > 0 && (
        <div className="mb-8 bg-primary-50 border border-primary-200 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-primary-900 mb-3 uppercase tracking-wide">
            Key Takeaways
          </h2>
          <ul className="space-y-2">
            {data.insights.map((ins, i) => (
              <li key={i} className="text-sm text-primary-900 flex items-start gap-2">
                <span className="text-primary-500 mt-0.5">•</span>
                <span>{ins}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Pick questions */}
      <div className="mb-10">
        <h2 className="text-xl font-bold text-gray-900 mb-4">League Predictions</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {data.pick_questions.map((q, i) => {
            const Icon = iconForQuestion(q.question);
            const max = q.results.reduce((m, r) => Math.max(m, r.count), 0);
            return (
              <div key={i} className="bg-white rounded-lg shadow p-5">
                <div className="flex items-start gap-2 mb-3">
                  <Icon className="h-5 w-5 text-primary-600 flex-shrink-0 mt-0.5" />
                  <h3 className="text-sm font-semibold text-gray-900">{q.question}</h3>
                </div>
                <div className="space-y-1">
                  {q.results.map((r, ri) => (
                    <BarRow key={ri} label={r.label} count={r.count} pct={r.pct} max={max} />
                  ))}
                </div>
                {q.note && <p className="text-xs text-gray-400 mt-3">{q.note}</p>}
              </div>
            );
          })}
        </div>
      </div>

      {/* Division standings predictions */}
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Predicted Division Standings</h2>
        <p className="text-sm text-gray-500 mb-4">
          Consensus seed is ordered by average predicted finish across all respondents (lower is better).
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {data.divisions.map((d) => (
            <div key={d.division} className="bg-white rounded-lg shadow overflow-hidden">
              <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                <h3 className="text-sm font-bold text-gray-900">{d.division}</h3>
                <p className="text-xs text-gray-500">Favorite: {d.consensus_favorite}</p>
              </div>
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-white">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Team</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Avg</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">1st votes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {d.teams.map((t, idx) => (
                    <tr key={t.team} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-3 py-2 text-sm font-bold text-gray-900">{t.consensus_seed}</td>
                      <td className="px-3 py-2">
                        <div className="text-sm font-medium text-gray-900">{t.team_short}</div>
                        <div className="text-xs text-gray-400 truncate max-w-[10rem]" title={t.team}>{t.team}</div>
                      </td>
                      <td className="px-3 py-2 text-right text-sm text-gray-700">{t.avg_predicted_rank}</td>
                      <td className="px-3 py-2 text-right text-sm text-gray-700">
                        {t.first_place_votes}
                        <span className="text-xs text-gray-400"> ({t.first_place_pct}%)</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SurveyResults;
