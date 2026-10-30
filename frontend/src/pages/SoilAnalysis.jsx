import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { soilAPI, farmsAPI, cropsAPI } from '../services/api';
import { apiError } from '../utils/apiError';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import UnitField from '../components/UnitField';
import ScoreGauge from '../components/ScoreGauge';
import EmptyState from '../components/EmptyState';
import { FiDroplet, FiInfo, FiCloud, FiAlertTriangle, FiLayers, FiSliders, FiActivity, FiPackage } from 'react-icons/fi';

const CROP_OPTIONS = ['Rice', 'Wheat', 'Corn', 'Tomato', 'Potato', 'Soybean', 'Cotton', 'Sugarcane', 'Groundnut', 'Millet'];

const FIELDS = [
  { label: 'Soil pH', key: 'ph', unit: 'pH', placeholder: '6.5', step: '0.1', min: 0, max: 14, hint: 'Ideal 6.0 to 7.5' },
  { label: 'Nitrogen (N)', key: 'nitrogen', unit: 'kg/ha', placeholder: '35', step: '1', min: 0, hint: 'Ideal 20 to 50' },
  { label: 'Phosphorus (P)', key: 'phosphorus', unit: 'kg/ha', placeholder: '25', step: '1', min: 0, hint: 'Ideal 15 to 40' },
  { label: 'Potassium (K)', key: 'potassium', unit: 'kg/ha', placeholder: '30', step: '1', min: 0, hint: 'Ideal 20 to 45' },
  { label: 'Moisture', key: 'moisture', unit: '%', placeholder: '50', step: '1', min: 0, max: 100, hint: 'Ideal 30 to 70' },
];

const UNITS = { ph: '', nitrogen: ' kg/ha', phosphorus: ' kg/ha', potassium: ' kg/ha', moisture: '%' };
const PARAM_LABELS = { ph: 'Soil pH', nitrogen: 'Nitrogen', phosphorus: 'Phosphorus', potassium: 'Potassium', moisture: 'Moisture' };

const toNumber = (v) => (v === '' ? null : Number(v));

// Example measurements to fill the form with. Choosing one only fills the inputs: nothing is saved
// until the user submits. The summaries describe what the rule-based checks should flag.
const SCENARIOS = [
  { id: 'suitable', label: 'Suitable soil', summary: 'Everything inside its ideal range', values: { ph: '6.8', nitrogen: '35', phosphorus: '25', potassium: '32', moisture: '50' } },
  { id: 'acidic', label: 'Acidic soil', summary: 'Low pH, other values normal', values: { ph: '5.0', nitrogen: '35', phosphorus: '25', potassium: '32', moisture: '50' } },
  { id: 'deficient', label: 'Nutrient-deficient', summary: 'Low nitrogen, phosphorus and potassium', values: { ph: '6.6', nitrogen: '8', phosphorus: '6', potassium: '10', moisture: '45' } },
  { id: 'dry', label: 'Dry soil', summary: 'Very low moisture', values: { ph: '6.7', nitrogen: '32', phosphorus: '24', potassium: '30', moisture: '12' } },
];
const formFromRecord = (r) => Object.fromEntries(['ph', 'nitrogen', 'phosphorus', 'potassium', 'moisture'].map((k) => [k, r[k] == null ? '' : String(r[k])]));

const priorityBadge = (p) => (p === 'high' || p === 'critical' ? 'badge-danger' : p === 'medium' ? 'badge-warning' : 'badge-success');
const statusBadge = (s) => (s === 'Optimal' ? 'badge-success' : ['Low', 'Very Acidic', 'Very Dry', 'Waterlogged', 'Very Alkaline'].includes(s) ? 'badge-danger' : 'badge-warning');

export default function SoilAnalysis() {
  const [form, setForm] = useState({ ph: '', nitrogen: '', phosphorus: '', potassium: '', moisture: '', crop_name: '', location: '' });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [farms, setFarms] = useState([]);
  const [myCrops, setMyCrops] = useState([]);
  const [scenario, setScenario] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();
  const recordParam = searchParams.get('record');
  const [saved, setSaved] = useState(null);        // { id, created_at } while a stored record is being viewed
  const [savedError, setSavedError] = useState('');

  // The user's farm supplies the location (and the farm the record is stored against)
  useEffect(() => {
    let cancelled = false;
    Promise.all([farmsAPI.getAll().catch(() => ({ data: [] })), cropsAPI.getAll().catch(() => ({ data: [] }))]).then(([f, c]) => {
      if (cancelled) return;
      setFarms(f.data);
      setMyCrops(c.data);
      const newest = [...f.data].sort((a, b) => b.id - a.id).find((x) => x.location);
      if (newest) setForm((cur) => (cur.location ? cur : { ...cur, location: newest.location }));
    });
    return () => { cancelled = true; };
  }, []);

  // Opened from a recommendation: show the saved soil record it was based on (read-only; nothing is re-saved)
  useEffect(() => {
    if (!recordParam) return undefined;
    let cancelled = false;
    soilAPI.getLatest(recordParam)
      .then((res) => {
        if (cancelled || !res.data.record) return;
        setForm((cur) => ({ ...cur, ...formFromRecord(res.data.record) }));
        setResult({ ...res.data.analysis, fromRecord: true });
        setSaved({ id: res.data.record.id, created_at: res.data.record.created_at });
        setSavedError('');
      })
      .catch((err) => { if (!cancelled) setSavedError(apiError(err, 'Could not open that soil record.')); });
    return () => { cancelled = true; };
  }, [recordParam]);

  const applyScenario = (s) => {
    setScenario(s.id);
    setForm((cur) => ({ ...cur, ...s.values }));
    setFieldErrors({});
    setError('');
    setResult(null);
    setSaved(null);
    if (recordParam) setSearchParams({}, { replace: true });
  };

  const validate = () => {
    const fields = {};
    let form_ = '';
    if (!FIELDS.some((f) => form[f.key] !== '')) form_ = 'Enter at least one soil measurement.';
    for (const f of FIELDS) {
      if (form[f.key] === '') continue;
      const n = Number(form[f.key]);
      if (Number.isNaN(n) || n < f.min || (f.max !== undefined && n > f.max)) {
        fields[f.key] = `${f.label} must be between ${f.min} and ${f.max ?? 'a positive value'}.`;
      }
    }
    return { form: form_, fields };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const { form: formError, fields } = validate();
    setFieldErrors(fields);
    const first = formError || Object.values(fields)[0];
    if (first) { setError(first); return; }
    setLoading(true);
    setError('');
    // Store the record against the user's own farm, and against their crop when the chosen crop matches one of theirs
    const farm = [...farms].sort((a, b) => b.id - a.id).find((f) => f.location === form.location.trim()) || null;
    const crop = myCrops.find((c) => c.name.toLowerCase() === form.crop_name.toLowerCase() && (!farm || c.farm_id === farm.id)) || null;
    try {
      const res = await soilAPI.analyze({
        farm_id: farm?.id ?? null,
        crop_id: crop?.id ?? null,
        ph: toNumber(form.ph),
        nitrogen: toNumber(form.nitrogen),
        phosphorus: toNumber(form.phosphorus),
        potassium: toNumber(form.potassium),
        moisture: toNumber(form.moisture),
        crop_name: form.crop_name || null,
        location: form.location.trim() || null,
      });
      setResult(res.data);
      setSaved(null);
      if (recordParam) setSearchParams({}, { replace: true });
    } catch (err) {
      setError(apiError(err, 'Analysis failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const setValue = (key) => (value) => {
    setForm((f) => ({ ...f, [key]: value }));
    if (FIELDS.some((f) => f.key === key)) setScenario('');   // an edited value no longer matches the example
  };

  return (
    <div className="animate-fadeIn space-y-6">
      <PageHeader
        eyebrow="Module 3 · Soil analysis & smart farming recommendations"
        title="Soil analysis"
        description="Assess soil health and get fertilizer, crop and irrigation suggestions from your measurements."
        actions={<Link to="/recommendations" className="btn btn-secondary"><FiPackage aria-hidden="true" /> Saved recommendations</Link>}
      />

      <div className="alert alert-info" role="note">
        <FiInfo className="mt-0.5 shrink-0 text-slate-400" aria-hidden="true" />
        <span className="text-xs leading-relaxed">
          This analysis is <strong>rule-based</strong>: your measurements are compared with standard agronomic ranges. It gives general guidance only. It is not a machine-learning prediction and is <strong>not a substitute for laboratory soil testing</strong>.
        </span>
      </div>

      {(error || savedError) && <div className="alert alert-error" role="alert"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />{error || savedError}</div>}

      {saved && (
        <div className="alert alert-success" role="status">
          <FiInfo className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>
            Showing saved soil record #{saved.id}{saved.created_at ? ` from ${new Date(saved.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}` : ''}.
            It is re-assessed with the same rules and nothing is saved again unless you choose Analyze soil.
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        {/* Input form */}
        <SectionCard icon={FiSliders} title="Soil measurements" description="Enter the values you have" className="lg:col-span-5">
          <div className="mb-4">
            <p className="mb-2 text-xs font-medium text-slate-500">Example soils <span className="font-normal">(fills the form only; nothing is saved)</span></p>
            <div className="grid grid-cols-2 gap-2" role="group" aria-label="Example soil scenarios">
              {SCENARIOS.map((s) => (
                <button key={s.id} type="button" onClick={() => applyScenario(s)} aria-pressed={scenario === s.id} title={s.summary}
                  className={`rounded-lg border px-3 py-2 text-left text-xs transition-colors ${scenario === s.id ? 'border-green-700 bg-green-50 text-green-900' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>
                  <span className="block font-medium">{s.label}</span>
                  <span className="block text-[11px] text-slate-500">{s.summary}</span>
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {FIELDS.map((f) => (
              <UnitField key={f.key} id={f.key} label={f.label} unit={f.unit} hint={f.hint} value={form[f.key]}
                onChange={setValue(f.key)} placeholder={f.placeholder} step={f.step} min={f.min} max={f.max} error={fieldErrors[f.key]} />
            ))}

            <div className="divider pt-4">
              <p className="mb-3 text-xs font-medium text-slate-500">Optional context</p>
              <div className="space-y-4">
                <div>
                  <label className="label" htmlFor="crop">Crop</label>
                  <select id="crop" value={form.crop_name} onChange={(e) => setValue('crop_name')(e.target.value)} className="input">
                    <option value="">Select crop</option>
                    {CROP_OPTIONS.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="location">Location</label>
                  <input id="location" type="text" value={form.location} onChange={(e) => setValue('location')(e.target.value)}
                    placeholder="e.g., Pune, India" className="input" />
                  <p className="hint">Adds live weather alerts from Open-Meteo.</p>
                </div>
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn btn-primary w-full">
              {loading ? <span className="h-4 w-4 spinner" aria-hidden="true" /> : <FiDroplet aria-hidden="true" />}
              {loading ? 'Analyzing...' : 'Analyze soil'}
            </button>
          </form>
        </SectionCard>

        {/* Results */}
        <div className="space-y-4 lg:col-span-7" aria-live="polite">
          {!result && !loading && (
            <SectionCard icon={FiActivity} title="Analysis result" description="Appears here after you analyze soil measurements">
              <EmptyState icon={FiDroplet} title="No analysis yet" description="Enter your soil measurements and choose Analyze soil to see the health score, parameter checks and recommendations." />
            </SectionCard>
          )}

          {loading && (
            <div className="card p-12 text-center" role="status">
              <div className="mx-auto mb-3 h-10 w-10 rounded-full border-4 border-green-600 border-t-transparent animate-spin" aria-hidden="true" />
              <p className="text-sm text-slate-500">Analyzing soil parameters...</p>
            </div>
          )}

          {result && !loading && (
            <>
              <section className="card p-5" aria-label="Soil health score">
                <div className="grid items-center gap-6 sm:grid-cols-[minmax(0,260px)_1fr]">
                  <ScoreGauge score={result.soil_health_score} status={result.soil_health_status} />
                  <div>
                    <p className="eyebrow">Soil health score</p>
                    <p className="mt-1 text-sm text-slate-700">Status: <span className="font-semibold text-slate-900">{result.soil_health_status}</span></p>
                    <p className="mt-2 text-sm leading-relaxed text-slate-600">{result.health_summary}</p>
                    <p className="mt-2 text-[11px] text-slate-500">Rule-based score from standard agronomic ranges, not a machine-learning prediction.</p>
                  </div>
                </div>
              </section>

              {result.detailed_analysis && Object.keys(result.detailed_analysis).length > 0 && (
                <SectionCard icon={FiActivity} title="Parameter analysis" description="Each measurement against its ideal range">
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {Object.entries(result.detailed_analysis).map(([key, data]) => (
                      <div key={key} className="panel p-3">
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <span className="text-xs font-medium text-slate-500">{PARAM_LABELS[key] || key}</span>
                          <span className={`badge ${statusBadge(data.status)}`}>{data.status}</span>
                        </div>
                        <p className="font-display text-xl font-medium text-slate-900 tnum">{data.value}<span className="text-sm text-slate-500">{UNITS[key]}</span></p>
                        <p className="mt-1 text-xs text-slate-500">{data.action}</p>
                      </div>
                    ))}
                  </div>
                </SectionCard>
              )}

              <SectionCard icon={FiPackage} title="Fertilizer recommendations">
                <div className="space-y-3">
                  {result.fertilizer_recommendations?.map((rec, i) => (
                    <div key={i} className="rounded-xl border border-slate-200 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium text-slate-800">{rec.fertilizer}</p>
                        <span className={`badge capitalize ${priorityBadge(rec.priority)}`}>{rec.priority}</span>
                      </div>
                      <p className="mt-1 text-xs text-slate-600">{rec.reason}</p>
                      <p className="mt-1 text-xs text-slate-500">How to apply: {rec.application}</p>
                    </div>
                  ))}
                </div>
              </SectionCard>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {result.crop_recommendations && (
                  <SectionCard icon={FiLayers} title="Suitable crops" description="Matched on pH, moisture and nitrogen">
                    <div className="flex flex-wrap gap-2">
                      {result.crop_recommendations.map((crop, i) => (
                        <span key={i} className="badge badge-success !px-3 !py-1 !text-sm">{crop}</span>
                      ))}
                    </div>
                  </SectionCard>
                )}
                <SectionCard icon={FiDroplet} title="Irrigation" className={result.crop_recommendations ? '' : 'md:col-span-2'}>
                  <p className={`text-sm font-medium ${result.irrigation_recommendation?.priority === 'critical' ? 'text-red-600' : result.irrigation_recommendation?.priority === 'high' ? 'text-amber-700' : 'text-green-700'}`}>
                    {result.irrigation_recommendation?.status}
                  </p>
                  <p className="mt-2 text-xs text-slate-600">{result.irrigation_recommendation?.recommendation}</p>
                  <p className="mt-1 text-xs text-slate-500">Schedule: {result.irrigation_recommendation?.schedule}</p>
                </SectionCard>
              </div>

              {result.weather_alerts && (
              <SectionCard icon={FiCloud} title="Weather-based alerts">
                {result.weather_used && (
                  <p className="mb-3 text-xs text-slate-500">
                    Using live weather for <strong>{result.weather_used.location}</strong>: {result.weather_used.temperature}°C, {result.weather_used.humidity}% humidity, {result.weather_used.rainfall} mm rain, {result.weather_used.wind_speed} km/h wind.
                  </p>
                )}
                <ul className="space-y-2">
                  {result.weather_alerts?.map((alert, i) => (
                    <li key={i} className="panel p-3 text-sm text-slate-700">{alert}</li>
                  ))}
                </ul>
                {result.weather_used?.attribution && <p className="mt-3 text-[11px] text-slate-500">{result.weather_used.attribution}</p>}
              </SectionCard>
              )}

              <p className="text-xs text-slate-500">
                {result.fromRecord ? (
                  <>See the advice from this record in <Link to="/recommendations" className="font-medium text-green-700 hover:text-green-800">Recommendations</Link>.</>
                ) : result.repeat_analysis ? (
                  <>These measurements were analysed before, so no duplicate advice was added. See <Link to="/recommendations" className="font-medium text-green-700 hover:text-green-800">Recommendations</Link>.</>
                ) : (
                  <>{result.recommendations_created} new recommendation{result.recommendations_created === 1 ? '' : 's'} saved to <Link to="/recommendations" className="font-medium text-green-700 hover:text-green-800">Recommendations</Link>.</>
                )}
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
