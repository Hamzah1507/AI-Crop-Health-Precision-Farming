import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { recommendationsAPI } from '../services/api';
import { apiError } from '../utils/apiError';
import PageHeader from '../components/PageHeader';
import EmptyState from '../components/EmptyState';
import { FiStar, FiInfo, FiAlertTriangle, FiDroplet, FiPackage, FiActivity, FiLayers, FiCloud, FiRefreshCw, FiArrowRight } from 'react-icons/fi';

const FILTERS = [
  { value: '', label: 'All' },
  { value: 'fertilizer', label: 'Fertilizer' },
  { value: 'irrigation', label: 'Irrigation' },
  { value: 'soil', label: 'Soil' },
  { value: 'weather', label: 'Weather' },
  { value: 'treatment', label: 'Treatment' },
];

const TYPE_STYLE = {
  fertilizer: { icon: FiPackage, badge: 'badge-success', label: 'Fertilizer' },
  irrigation: { icon: FiDroplet, badge: 'badge-info', label: 'Irrigation' },
  soil: { icon: FiLayers, badge: 'badge-neutral', label: 'Soil' },
  weather: { icon: FiCloud, badge: 'badge-info', label: 'Weather' },
  treatment: { icon: FiActivity, badge: 'badge-danger', label: 'Treatment' },
};

const PRIORITY_BADGE = { critical: 'badge-danger', high: 'badge-danger', medium: 'badge-warning', low: 'badge-success' };

// What the advice is based on, shown on every card so it is never mistaken for a trained-model result
const basisFor = (rec) => {
  if (rec.type === 'weather') return 'Live weather (Open-Meteo) + rules';
  if (rec.source_type === 'prediction') return rec.is_simulated ? 'Simulated detector' : 'Detection model';
  return 'Rule-based from soil values';
};

const sourceLink = (rec) => {
  if (rec.source_type === 'soil_record') return { to: `/soil-analysis?record=${rec.source_id}`, label: 'View soil record' };
  if (rec.source_type === 'prediction') return { to: `/prediction-history#prediction-${rec.source_id}`, label: 'View scan' };
  return null;
};

export default function SmartRecommendations() {
  const [recommendations, setRecommendations] = useState([]);
  const [counts, setCounts] = useState({});
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    recommendationsAPI.getAll(filter || undefined)
      .then((res) => {
        if (cancelled) return;
        setRecommendations(res.data);
        setError('');
        // Category counts come from the unfiltered list, so they stay visible while a filter is applied
        if (!filter) setCounts(res.data.reduce((acc, r) => ({ ...acc, [r.type]: (acc[r.type] || 0) + 1 }), { '': res.data.length }));
      })
      .catch((err) => { if (!cancelled) setError(apiError(err, 'Could not load recommendations.')); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filter, attempt]);

  const choose = (value) => {
    if (value === filter) return;
    setLoading(true);
    setFilter(value);
  };
  const retry = useCallback(() => { setLoading(true); setError(''); setAttempt((n) => n + 1); }, []);

  const simulatedCount = recommendations.filter((r) => r.is_simulated).length;

  return (
    <div className="animate-fadeIn space-y-6">
      <PageHeader
        eyebrow="Module 3 · Smart farming recommendations"
        title="Recommendations"
        description="Fertilizer, irrigation, soil, weather and treatment suggestions generated from your soil analyses, live weather and leaf scans."
        actions={<Link to="/soil-analysis" className="btn btn-primary"><FiDroplet aria-hidden="true" /> Analyze soil</Link>}
      />

      <div className="alert alert-info" role="note">
        <FiInfo className="mt-0.5 shrink-0 text-slate-400" aria-hidden="true" />
        <span className="text-xs leading-relaxed">
          Soil, fertilizer and irrigation items are <strong>rule-based</strong> guidance from your measurements; weather items use the live Open-Meteo forecast.
          Treatment items come from disease detection, which is <strong>simulated</strong> until a trained model is added, so they are labelled and should not be acted on.
          Quantities are deliberately not given: confirm products and amounts with a soil test or your local agronomist.
        </span>
      </div>

      <div role="group" aria-label="Filter by recommendation type" className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button key={f.value || 'all'} type="button" onClick={() => choose(f.value)} aria-pressed={filter === f.value}
            className={`rounded-full border px-4 py-1.5 text-sm font-medium transition-colors ${
              filter === f.value ? 'border-green-700 bg-green-700 text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>
            {f.label}{counts[f.value] !== undefined && <span className="ml-1.5 text-xs opacity-80 tnum">{counts[f.value]}</span>}
          </button>
        ))}
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />
          <span className="flex-1">{error}</span>
          <button type="button" onClick={retry} className="btn btn-secondary btn-sm"><FiRefreshCw aria-hidden="true" /> Try again</button>
        </div>
      )}

      {!loading && simulatedCount > 0 && (
        <p className="text-xs text-slate-500">{simulatedCount} of these {simulatedCount === 1 ? 'is a' : 'are'} simulated treatment suggestion{simulatedCount === 1 ? '' : 's'} from the demonstration detector.</p>
      )}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2" aria-busy="true" aria-label="Loading recommendations">
          {Array.from({ length: 4 }, (_, i) => <div key={i} className="skeleton h-44" />)}
        </div>
      ) : recommendations.length === 0 && !error ? (
        <div className="card">
          <EmptyState icon={FiStar} title={filter ? `No ${filter} recommendations yet` : 'No recommendations yet'}
            description="Run a soil analysis or a disease detection and the resulting suggestions will appear here.">
            <Link to="/soil-analysis" className="btn btn-secondary">Soil analysis</Link>
            <Link to="/disease-detection" className="btn btn-secondary">Disease detection</Link>
          </EmptyState>
        </div>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {recommendations.map((rec) => {
            const style = TYPE_STYLE[rec.type] || { icon: FiStar, badge: 'badge-neutral', label: rec.type };
            const Icon = style.icon;
            const link = sourceLink(rec);
            // Older rows have no structured reason; fall back to the stored description
            const reason = rec.reason || rec.description;
            return (
              <li key={rec.id} className="card flex flex-col gap-3 p-5">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="icon-tile-sm" aria-hidden="true"><Icon /></span>
                    <span className={`badge ${style.badge}`}>{style.label}</span>
                    {rec.is_simulated && <span className="badge badge-warning">Simulated</span>}
                  </div>
                  <span className={`badge capitalize ${PRIORITY_BADGE[rec.priority] || 'badge-neutral'}`}>{rec.priority} priority</span>
                </div>

                <h2 className="text-sm font-semibold text-slate-900">{rec.title}</h2>

                <dl className="space-y-2 text-xs leading-relaxed">
                  {reason && (
                    <div><dt className="font-medium text-slate-500">Why</dt><dd className="text-slate-700">{reason}</dd></div>
                  )}
                  {rec.action && (
                    <div><dt className="font-medium text-slate-500">Suggested action</dt><dd className="text-slate-700">{rec.action}</dd></div>
                  )}
                </dl>

                <div className="mt-auto flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
                  <span>
                    {rec.crop_name ? <>Crop: <strong className="font-medium text-slate-700">{rec.crop_name}</strong> · </> : ''}
                    {basisFor(rec)}
                    {rec.created_at ? ` · ${new Date(rec.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}` : ''}
                  </span>
                  {link && (
                    <Link to={link.to} className="inline-flex items-center gap-1 font-medium text-green-700 hover:text-green-800">
                      {link.label} <FiArrowRight aria-hidden="true" />
                    </Link>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
