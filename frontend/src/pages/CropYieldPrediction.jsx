import { useState, useEffect } from 'react';
import { yieldAPI } from '../services/api';
import { apiError } from '../utils/apiError';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import UnitField from '../components/UnitField';
import EmptyState from '../components/EmptyState';
import { FiTrendingUp, FiAlertTriangle, FiSliders, FiCloud, FiList, FiClock } from 'react-icons/fi';

const CROP_OPTIONS = ['Rice', 'Wheat', 'Corn', 'Tomato', 'Potato', 'Soybean', 'Cotton', 'Sugarcane', 'Groundnut', 'Millet', 'Apple', 'Grape'];
const SEASONS = ['Kharif (Monsoon)', 'Rabi (Winter)', 'Zaid (Summer)'];

const SOIL_FIELDS = [
  { label: 'Soil pH', key: 'soil_ph', unit: 'pH', placeholder: '6.5', step: '0.1', min: 0, max: 14 },
  { label: 'Nitrogen (N)', key: 'soil_nitrogen', unit: 'kg/ha', placeholder: '35', step: '1', min: 0 },
  { label: 'Phosphorus (P)', key: 'soil_phosphorus', unit: 'kg/ha', placeholder: '25', step: '1', min: 0 },
  { label: 'Potassium (K)', key: 'soil_potassium', unit: 'kg/ha', placeholder: '30', step: '1', min: 0 },
  { label: 'Soil moisture', key: 'soil_moisture', unit: '%', placeholder: '50', step: '1', min: 0, max: 100 },
];
const WEATHER_FIELDS = [
  { label: 'Temperature', key: 'temperature', unit: '°C', placeholder: '28', step: '0.1', min: -50, max: 60 },
  { label: 'Humidity', key: 'humidity', unit: '%', placeholder: '65', step: '0.1', min: 0, max: 100 },
  { label: 'Rainfall', key: 'rainfall', unit: 'mm', placeholder: '5', step: '0.1', min: 0 },
];

const toNumber = (v) => (v === '' ? null : Number(v));

// Example inputs that fill the form only; an estimate is stored when the user submits it
const SCENARIOS = [
  { id: 'favourable', label: 'Favourable conditions', summary: 'Soil and weather in range',
    values: { crop_name: 'Wheat', area: '2', season: 'Rabi (Winter)', soil_ph: '6.8', soil_nitrogen: '35', soil_phosphorus: '25', soil_potassium: '32', soil_moisture: '50', temperature: '22', humidity: '60', rainfall: '3' } },
  { id: 'dry', label: 'Dry and hot', summary: 'Low moisture, high temperature, no rain',
    values: { crop_name: 'Wheat', area: '2', season: 'Zaid (Summer)', soil_ph: '6.8', soil_nitrogen: '35', soil_phosphorus: '25', soil_potassium: '32', soil_moisture: '15', temperature: '41', humidity: '25', rainfall: '0' } },
  { id: 'poor', label: 'Nutrient-poor soil', summary: 'Low N, P and K, acidic pH',
    values: { crop_name: 'Wheat', area: '2', season: 'Rabi (Winter)', soil_ph: '5.1', soil_nitrogen: '8', soil_phosphorus: '6', soil_potassium: '10', soil_moisture: '45', temperature: '22', humidity: '60', rainfall: '3' } },
];

export default function CropYieldPrediction() {
  const [form, setForm] = useState({
    crop_name: '', area: '', soil_ph: '', soil_nitrogen: '', soil_phosphorus: '',
    soil_potassium: '', soil_moisture: '', temperature: '', humidity: '', rainfall: '', season: ''
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [history, setHistory] = useState({ loading: true, items: [], error: '' });
  const [scenario, setScenario] = useState('');

  const loadHistory = () => yieldAPI.getHistory()
    .then((res) => setHistory({ loading: false, items: res.data, error: '' }))
    .catch((err) => setHistory({ loading: false, items: [], error: apiError(err, 'Could not load your saved estimates.') }));
  useEffect(() => { loadHistory(); }, []);

  const applyScenario = (s) => {
    setScenario(s.id);
    setForm((f) => ({ ...f, ...s.values }));
    setFieldErrors({});
    setError('');
    setResult(null);
  };

  const validate = () => {
    const fields = {};
    if (!form.crop_name) fields.crop_name = 'Please select a crop.';
    if (form.area !== '' && !(Number(form.area) > 0)) fields.area = 'Area must be greater than 0.';
    for (const f of [...SOIL_FIELDS, ...WEATHER_FIELDS]) {
      if (form[f.key] === '') continue;
      const n = Number(form[f.key]);
      if (Number.isNaN(n) || n < f.min || (f.max !== undefined && n > f.max)) {
        fields[f.key] = `${f.label} must be between ${f.min} and ${f.max ?? 'a positive value'}.`;
      }
    }
    return fields;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const fields = validate();
    setFieldErrors(fields);
    const first = Object.values(fields)[0];
    if (first) { setError(first); return; }
    setLoading(true);
    setError('');
    try {
      const res = await yieldAPI.predict({
        crop_name: form.crop_name,
        area: toNumber(form.area),
        soil_ph: toNumber(form.soil_ph),
        soil_nitrogen: toNumber(form.soil_nitrogen),
        soil_phosphorus: toNumber(form.soil_phosphorus),
        soil_potassium: toNumber(form.soil_potassium),
        soil_moisture: toNumber(form.soil_moisture),
        temperature: toNumber(form.temperature),
        humidity: toNumber(form.humidity),
        rainfall: toNumber(form.rainfall),
        season: form.season || null,
      });
      setResult(res.data);
      loadHistory();
    } catch (err) {
      setError(apiError(err, 'Estimate failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const setValue = (key) => (value) => {
    setForm((f) => ({ ...f, [key]: value }));
    setScenario('');
  };
  const numberField = (f) => (
    <UnitField key={f.key} id={f.key} label={f.label} unit={f.unit} value={form[f.key]} onChange={setValue(f.key)}
      placeholder={f.placeholder} step={f.step} min={f.min} max={f.max} error={fieldErrors[f.key]} />
  );

  const total = result?.area && result?.predicted_yield != null ? Math.round(result.area * result.predicted_yield * 100) / 100 : null;
  const given = (v, unit = '') => (v === null || v === undefined ? null : `${v}${unit}`);

  return (
    <div className="animate-fadeIn space-y-6">
      <PageHeader
        eyebrow="Module 4 · Crop yield"
        title="Crop yield estimate"
        description="Estimate the expected yield from the crop, soil and weather values you enter."
      />

      {error && <div className="alert alert-error" role="alert"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />{error}</div>}

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
        {/* Input form */}
        <form onSubmit={handleSubmit} className="space-y-6" noValidate>
          <div>
            <p className="mb-2 text-xs font-medium text-slate-500">Example conditions <span className="font-normal">(fills the form only)</span></p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 lg:grid-cols-1" role="group" aria-label="Example yield scenarios">
              {SCENARIOS.map((s) => (
                <button key={s.id} type="button" onClick={() => applyScenario(s)} aria-pressed={scenario === s.id}
                  className={`rounded-lg border px-3 py-2 text-left text-xs transition-colors ${scenario === s.id ? 'border-green-700 bg-green-50 text-green-900' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>
                  <span className="block font-medium">{s.label}</span>
                  <span className="block text-[11px] text-slate-500">{s.summary}</span>
                </button>
              ))}
            </div>
          </div>

          <SectionCard icon={FiSliders} title="Crop & area">
            <div className="space-y-4">
              <div>
                <label className="label" htmlFor="crop_name">Crop <span className="text-red-600" aria-hidden="true">*</span></label>
                <select id="crop_name" value={form.crop_name} onChange={(e) => setValue('crop_name')(e.target.value)} className="input"
                  aria-required="true" aria-invalid={fieldErrors.crop_name ? true : undefined} aria-describedby={fieldErrors.crop_name ? 'crop_name-error' : undefined}>
                  <option value="">Select crop</option>
                  {CROP_OPTIONS.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                {fieldErrors.crop_name && <p id="crop_name-error" className="mt-1 text-xs text-red-600">{fieldErrors.crop_name}</p>}
              </div>
              <UnitField id="area" label="Area" unit="hectares" value={form.area} onChange={setValue('area')} placeholder="10" step="0.1" min="0" error={fieldErrors.area} />
              <div>
                <label className="label" htmlFor="season">Season</label>
                <select id="season" value={form.season} onChange={(e) => setValue('season')(e.target.value)} className="input">
                  <option value="">Select season</option>
                  {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
          </SectionCard>

          <SectionCard icon={FiSliders} title="Soil" description="Optional">
            <div className="space-y-4">{SOIL_FIELDS.map(numberField)}</div>
          </SectionCard>

          <SectionCard icon={FiCloud} title="Weather" description="Optional">
            <div className="space-y-4">{WEATHER_FIELDS.map(numberField)}</div>
          </SectionCard>

          <button type="submit" disabled={loading} className="btn btn-primary w-full">
            {loading ? <span className="h-4 w-4 spinner" aria-hidden="true" /> : <FiTrendingUp aria-hidden="true" />}
            {loading ? 'Estimating...' : 'Estimate yield'}
          </button>
        </form>

        {/* Result */}
        <div className="space-y-4 lg:col-span-2" aria-live="polite">
          {!result && !loading && (
            <div className="card">
              <EmptyState icon={FiTrendingUp} title="No estimate yet" description="Choose a crop and enter your soil and weather values to get a rough yield estimate." />
            </div>
          )}

          {loading && (
            <div className="card p-12 text-center" role="status">
              <div className="mx-auto mb-3 h-10 w-10 rounded-full border-4 border-green-600 border-t-transparent animate-spin" aria-hidden="true" />
              <p className="text-sm text-slate-500">Estimating crop yield...</p>
            </div>
          )}

          {result && !loading && (
            <>
              <section className="card border-green-200 bg-green-50/60 p-6" aria-label="Estimated yield">
                <p className="eyebrow">Estimated yield (rule-based)</p>
                <div className="mt-2 flex flex-wrap items-baseline gap-2">
                  <p className="font-display text-5xl font-medium text-slate-900 tnum">≈ {result.predicted_yield}</p>
                  <p className="text-base text-slate-600">{result.yield_unit}</p>
                </div>
                {total !== null && <p className="mt-2 text-sm text-slate-700">About <strong className="tnum">{total}</strong> tons over {result.area} hectares</p>}
                <p className="mt-3 text-xs text-slate-600">
                  Crop: {result.crop_name} · Input completeness: {result.confidence}% (share of optional inputs you provided, not an accuracy score)
                </p>
                <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
                  Rule-based estimate starting from typical crop yields and adjusted for soil and weather values, not a trained-model prediction.
                </p>
              </section>

              {result.factors?.length > 0 && (
                <SectionCard icon={FiList} title="What shaped this estimate" description="Adjustments applied to the typical yield for this crop">
                  <ul className="space-y-2">
                    {result.factors.map((f) => (
                      <li key={f.factor} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2">
                        <span className="text-sm text-slate-700"><span className="font-medium text-slate-900">{f.factor}:</span> {f.detail}</span>
                        <span className={`badge ${f.impact === 'Positive' ? 'badge-success' : f.impact === 'Negative' ? 'badge-danger' : 'badge-warning'}`}>{f.impact}</span>
                      </li>
                    ))}
                  </ul>
                  {result.model_note && <p className="mt-3 text-[11px] text-slate-500">{result.model_note}</p>}
                </SectionCard>
              )}

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <SectionCard icon={FiList} title="Estimate details" description="Rule-based calculation details">
                  <dl className="space-y-2 text-sm">
                    {[
                      { label: 'Crop', value: result.crop_name },
                      { label: 'Estimated yield', value: `${result.predicted_yield} ${result.yield_unit}` },
                      { label: 'Input completeness', value: `${result.confidence}%` },
                      { label: 'Area', value: result.area ? `${result.area} hectares` : '-' },
                      { label: 'Season', value: result.season || '-' },
                      { label: 'Date', value: result.created_at ? new Date(result.created_at).toLocaleString() : '-' },
                    ].map((item) => (
                      <div key={item.label} className="flex justify-between gap-3 border-b border-slate-100 py-1.5 last:border-0">
                        <dt className="text-slate-500">{item.label}</dt>
                        <dd className="text-right font-medium text-slate-800">{item.value}</dd>
                      </div>
                    ))}
                  </dl>
                </SectionCard>

                <SectionCard icon={FiSliders} title="Inputs used" description="Values that shaped the estimate">
                  <dl className="space-y-2 text-sm">
                    {[
                      { label: 'Soil pH', value: given(result.soil_ph) },
                      { label: 'Nitrogen', value: given(result.soil_nitrogen, ' kg/ha') },
                      { label: 'Phosphorus', value: given(result.soil_phosphorus, ' kg/ha') },
                      { label: 'Potassium', value: given(result.soil_potassium, ' kg/ha') },
                      { label: 'Moisture', value: given(result.soil_moisture, '%') },
                      { label: 'Temperature', value: given(result.temperature, '°C') },
                      { label: 'Humidity', value: given(result.humidity, '%') },
                      { label: 'Rainfall', value: given(result.rainfall, ' mm') },
                    ].filter(i => i.value).map((item) => (
                      <div key={item.label} className="flex justify-between gap-3 border-b border-slate-100 py-1.5 last:border-0">
                        <dt className="text-slate-500">{item.label}</dt>
                        <dd className="font-medium text-slate-800">{item.value}</dd>
                      </div>
                    ))}
                  </dl>
                </SectionCard>
              </div>
            </>
          )}

          <SectionCard icon={FiClock} title="Saved estimates" description="Each estimate you run is stored; all are rule-based">
            {history.loading ? (
              <div className="skeleton h-16 w-full" aria-busy="true" aria-label="Loading saved estimates" />
            ) : history.error ? (
              <p className="text-sm text-red-700" role="alert">{history.error}</p>
            ) : history.items.length === 0 ? (
              <p className="text-sm text-slate-500">No saved estimates yet. Run one and it will be listed here.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="table-clean">
                  <caption className="sr-only">Saved rule-based yield estimates</caption>
                  <thead>
                    <tr><th scope="col">Crop</th><th scope="col">Estimate</th><th scope="col">Area</th><th scope="col">Season</th><th scope="col">Date</th></tr>
                  </thead>
                  <tbody>
                    {history.items.slice(0, 8).map((h) => (
                      <tr key={h.id}>
                        <td className="font-medium text-slate-800">{h.crop_name}</td>
                        <td className="tnum">≈ {h.predicted_yield} <span className="text-xs text-slate-500">{h.yield_unit}</span></td>
                        <td className="tnum">{h.area ? `${h.area} ha` : '-'}</td>
                        <td className="text-slate-600">{h.season || '-'}</td>
                        <td className="whitespace-nowrap text-xs text-slate-500">{h.created_at ? new Date(h.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {history.items.length > 8 && <p className="mt-2 text-xs text-slate-500">Showing the 8 most recent of {history.items.length}.</p>}
              </div>
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
