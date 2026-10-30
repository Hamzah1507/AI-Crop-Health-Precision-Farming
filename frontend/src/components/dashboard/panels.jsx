import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FiThermometer, FiWind, FiDroplet, FiSearch, FiSliders, FiPackage, FiImage, FiMapPin,
  FiTrendingUp, FiAlertTriangle, FiArrowRight, FiEdit3, FiX
} from 'react-icons/fi';
import { WiDaySunny, WiDayCloudy, WiCloudy, WiFog, WiRain, WiShowers, WiSnow, WiThunderstorm, WiCloud } from 'react-icons/wi';
import { STATUS_COLOR } from '../../utils/statusColors';
import { uploadUrl } from '../../utils/uploadUrl';
import aerialImage from '../../assets/farm-aerial.jpg';

// ---------------------------------------------------------------------------
// Reference-style dashboard panels. Every value shown comes from a backend
// response; where there is no data the panel shows an honest empty state.
// ---------------------------------------------------------------------------

const val = (v, unit = '') => (v === null || v === undefined || Number.isNaN(v) ? '—' : `${v}${unit}`);
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '');

export function DashCard({ className = '', children, label, padding = 'p-4 xl:p-[18px]' }) {
  return (
    <section aria-label={label} className={`card flex flex-col ${padding} ${className}`}>
      {children}
    </section>
  );
}

function CardTitle({ icon: Icon, children, right }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <h2 className="flex min-w-0 items-center gap-2.5 font-display text-[1.0625rem] font-medium leading-tight text-slate-900">
        {Icon && <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-green-50 text-[15px] text-green-700" aria-hidden="true"><Icon /></span>}
        <span className="truncate">{children}</span>
      </h2>
      {right}
    </div>
  );
}

function weatherIcon(weather) {
  if (!weather?.is_live) return { Icon: WiCloud, color: 'text-slate-300' };   // muted placeholder, not a forecast
  const d = (weather.description || '').toLowerCase();
  const c = weather.condition;
  if (c === 'Thunderstorm') return { Icon: WiThunderstorm, color: 'text-slate-500' };
  if (c === 'Snow') return { Icon: WiSnow, color: 'text-sky-400' };
  if (c === 'Rain') return { Icon: d.includes('shower') ? WiShowers : WiRain, color: 'text-sky-500' };
  if (c === 'Drizzle') return { Icon: WiShowers, color: 'text-sky-400' };
  if (c === 'Fog') return { Icon: WiFog, color: 'text-slate-400' };
  if (d.includes('overcast')) return { Icon: WiCloudy, color: 'text-slate-400' };
  if (c === 'Clouds') return { Icon: WiDayCloudy, color: 'text-amber-400' };
  return { Icon: WiDaySunny, color: 'text-amber-400' };
}

/* --------------------------------- Weather -------------------------------- */
export function WeatherPanel({ location, usingDefault = false, weather, loading, error, onLookup }) {
  const [editing, setEditing] = useState(false);
  const [query, setQuery] = useState('');
  const live = weather?.is_live === true;
  const { Icon, color } = weatherIcon(weather);
  const today = new Date();

  const submit = (e) => {
    e.preventDefault();
    if (query.trim()) { onLookup(query.trim()); setEditing(false); setQuery(''); }
  };

  const title = loading ? null : live ? weather.description : error ? 'Weather unavailable' : weather ? 'Weather unavailable' : 'Weather';
  const pills = [
    { icon: FiThermometer, label: 'Temperature', value: live ? val(weather.temperature) : '—', unit: live ? '°C' : '' },
    { icon: FiWind, label: 'Wind', value: live ? val(weather.wind_speed) : '—', unit: live ? 'km/h' : '' },
    { icon: FiDroplet, label: 'Humidity', value: live ? val(weather.humidity) : '—', unit: live ? '%' : '' },
  ];

  return (
    <DashCard label="Weather">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        <div className="flex flex-col">
          {loading ? <div className="skeleton h-6 w-32" aria-label="Loading weather" /> : (
            <h2 className="font-display text-[1.0625rem] font-medium leading-tight text-slate-900">{title}</h2>
          )}
          <Icon className={`-ml-1 mt-1 text-[64px] leading-none ${color}`} aria-hidden="true" />
          <p className="mt-auto flex items-baseline gap-1.5 font-display text-slate-900">
            <span className="text-[2.5rem] font-medium leading-none tnum">{today.getDate()}</span>
            <span className="text-[0.9375rem] text-slate-600">{today.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}</span>
          </p>
        </div>

        <ul className="flex flex-col justify-center gap-2" aria-label="Current conditions">
          {pills.map((p) => {
            const PIcon = p.icon;
            return (
              <li key={p.label} className="flex items-center justify-between rounded-full bg-slate-100 px-4 py-2.5">
                <span className="flex items-center gap-2.5 text-sm text-slate-700"><PIcon className="text-base text-slate-600" aria-hidden="true" />{p.label}</span>
                {loading ? <span className="skeleton h-5 w-12" /> : (
                  <span className="font-display text-xl leading-none text-slate-900 tnum">
                    {p.value}<span className="ml-1 font-sans text-xs text-slate-600">{p.unit}</span>
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      <div className="mt-3 flex min-h-[1.75rem] flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-slate-100 pt-2.5 text-[11px] text-slate-500">
        {editing ? (
          <form onSubmit={submit} className="flex w-full items-center gap-2" role="search" aria-label="Look up weather for a location">
            <label htmlFor="weather-location" className="sr-only">Location</label>
            <input id="weather-location" autoFocus type="text" value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., Pune, India" className="input !min-h-[1.875rem] !py-1 !text-xs flex-1" />
            <button type="submit" className="btn btn-primary btn-sm" disabled={!query.trim()}>Check</button>
            <button type="button" onClick={() => setEditing(false)} className="btn btn-ghost btn-sm !px-2" aria-label="Cancel"><FiX aria-hidden="true" /></button>
          </form>
        ) : (
          <>
            <span className="flex min-w-0 items-center gap-1.5">
              <FiMapPin className="shrink-0" aria-hidden="true" />
              {!location && !loading && <span>No location yet. <Link to="/data-acquisition" className="font-medium text-green-700 underline">Add a farm location</Link></span>}
              {location && loading && <span>Loading {location}…</span>}
              {location && !loading && error && <span className="text-red-600" role="alert">{error}</span>}
              {location && !loading && !error && live && (
                <span className="truncate"><strong className="font-medium text-slate-700">{weather.resolved_location || location}</strong> · Live data{usingDefault ? ' · Default location' : ''}</span>
              )}
              {location && !loading && !error && weather && !live && (
                <span className="flex items-center gap-1 text-amber-700" role="status"><FiAlertTriangle aria-hidden="true" /> Live weather unavailable. No values shown.</span>
              )}
            </span>
            <span className="flex items-center gap-3">
              {live && (
                <a href={weather.attribution_url || 'https://open-meteo.com/'} target="_blank" rel="noopener noreferrer" className="underline hover:text-green-700">
                  {weather.attribution}
                </a>
              )}
              <button type="button" onClick={() => setEditing(true)} className="font-medium text-green-700 hover:text-green-800">Check another place</button>
            </span>
          </>
        )}
      </div>
    </DashCard>
  );
}

/* ------------------------------ Compact stat ------------------------------ */
export function StatCard({ icon, title, value, unit, hint, to, loading }) {
  return (
    <DashCard label={title}>
      <CardTitle icon={icon}>{title}</CardTitle>
      <div className="mt-4 flex items-end justify-between gap-2">
        {loading ? <div className="skeleton h-10 w-20" /> : (
          <p className="flex items-baseline gap-2 font-display">
            <span className="text-[2.5rem] font-medium leading-none text-slate-900 tnum">{value}</span>
            <span className="font-sans text-sm text-slate-500">{unit}</span>
          </p>
        )}
        {!loading && hint && <p className="max-w-[55%] text-right text-[11px] leading-snug text-slate-500">{hint}</p>}
      </div>
      {to && <Link to={to} className="sr-only">Open {title}</Link>}
    </DashCard>
  );
}

/* ------------------------------ Soil strip -------------------------------- */
const BANDS = [
  { label: 'Critical', width: 25, color: STATUS_COLOR.Critical },
  { label: 'Poor', width: 20, color: STATUS_COLOR.Poor },
  { label: 'Moderate', width: 20, color: STATUS_COLOR.Moderate },
  { label: 'Good', width: 20, color: STATUS_COLOR.Good },
  { label: 'Excellent', width: 15, color: STATUS_COLOR.Excellent },
];

export function SoilStrip({ loading, soil }) {
  const analysis = soil?.analysis;
  const status = analysis?.soil_health_status;
  const detail = analysis?.detailed_analysis || {};
  const short = { nitrogen: 'N', phosphorus: 'P', potassium: 'K' };

  return (
    <DashCard label="Soil nutrient status">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
        <div className="min-w-0">
          <h2 className="font-display text-[1.0625rem] font-medium leading-tight text-slate-900">Soil Nutrient Status</h2>
          {loading ? <div className="skeleton mt-2 h-4 w-48" /> : !analysis ? (
            <p className="mt-1 text-sm text-slate-500">No soil records yet. <Link to="/data-acquisition" className="font-medium text-green-700 underline">Add measurements</Link></p>
          ) : (
            <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-600">
              {['nitrogen', 'phosphorus', 'potassium'].filter((k) => detail[k]).map((k) => (
                <span key={k} className="inline-flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${detail[k].status === 'Optimal' ? 'bg-green-600' : detail[k].status === 'High' ? 'bg-amber-500' : 'bg-red-500'}`} aria-hidden="true" />
                  {short[k]} {detail[k].status}
                </span>
              ))}
            </p>
          )}
        </div>

        {!loading && analysis && (
          <div className="flex items-center gap-4">
            <div className="w-36" role="img" aria-label={`Soil health score ${analysis.soil_health_score} out of 100, status ${status}`}>
              <div className="relative flex gap-0.5">
                {BANDS.map((b) => <span key={b.label} className="h-2 rounded-full" style={{ width: `${b.width}%`, background: b.color, opacity: b.label === status ? 1 : 0.35 }} />)}
                <span className="absolute top-1/2 h-4 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-slate-900 ring-2 ring-white"
                  style={{ left: `${Math.max(2, Math.min(98, analysis.soil_health_score))}%` }} />
              </div>
            </div>
            <p className="text-right leading-tight">
              <span className="block font-display text-xl font-medium" style={{ color: STATUS_COLOR[status] || '#5F6D64' }}>{status}</span>
              <span className="block text-[11px] text-slate-500 tnum">{analysis.soil_health_score}/100</span>
            </p>
          </div>
        )}
      </div>
    </DashCard>
  );
}

/* --------------------------------- Map ------------------------------------ */
export function FarmMap({ loading, farms, farmId, onSelectFarm, crops, soil, defaultFarmName = '' }) {
  const farm = farms.find((f) => f.id === farmId) || null;
  const farmCrops = farm ? crops.filter((c) => c.farm_id === farm.id) : [];
  const rec = soil?.record;
  const rows = rec ? [
    { label: 'Soil pH', value: val(rec.ph) },
    { label: 'Nitrogen', value: val(rec.nitrogen, ' kg/ha') },
    { label: 'Phosphorus', value: val(rec.phosphorus, ' kg/ha') },
    { label: 'Potassium', value: val(rec.potassium, ' kg/ha') },
    { label: 'Moisture', value: val(rec.moisture, '%') },
  ] : [];

  return (
    <section aria-label="Farm overview" className="relative h-full min-h-[29rem] overflow-hidden rounded-card border border-slate-200 shadow-card xl:min-h-[22rem]">
      <img src={aerialImage} alt="" className="absolute inset-0 h-full w-full object-cover" />
      <div className="absolute inset-0 bg-gradient-to-b from-black/10 via-transparent to-black/25" aria-hidden="true" />

      <Link to="/data-acquisition" title="Manage farm data" aria-label="Manage farm data"
        className="absolute right-3 top-3 flex h-10 w-10 items-center justify-center rounded-full bg-green-900/80 text-white backdrop-blur-sm transition-colors hover:bg-green-800">
        <FiEdit3 aria-hidden="true" />
      </Link>

      {/* Contextual overlay: real farm, crops and the latest soil record */}
      <div className="absolute left-1/2 top-[8%] w-[min(86%,21rem)] -translate-x-1/2 rounded-2xl border border-white/25 bg-green-950/65 p-4 text-white shadow-lift backdrop-blur-md">
        {loading ? (
          <div className="space-y-3" aria-hidden="true"><div className="skeleton mx-auto h-5 w-40 opacity-30" /><div className="skeleton h-10 w-full opacity-30" /><div className="skeleton h-20 w-full opacity-30" /></div>
        ) : !farm ? (
          <div className="py-2 text-center">
            <p className="font-display text-lg font-medium">No farm yet</p>
            <p className="mt-1 text-xs text-green-100">Add your first farm to see its location, crops and latest soil record here.</p>
            <Link to="/data-acquisition" className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-white/50 px-3 py-1.5 text-xs font-medium hover:bg-white/10">
              Add a farm <FiArrowRight aria-hidden="true" />
            </Link>
          </div>
        ) : (
          <>
            {farms.length > 1 ? (
              <>
                <label htmlFor="map-farm" className="sr-only">Farm</label>
                <select id="map-farm" value={farm.id} onChange={(e) => onSelectFarm(Number(e.target.value))}
                  className="w-full rounded-lg border border-white/30 bg-green-950/60 px-2 py-1 text-center font-display text-lg font-medium text-white">
                  {farms.map((f) => <option key={f.id} value={f.id} className="text-slate-900">{f.name}</option>)}
                </select>
              </>
            ) : (
              <h2 className="truncate text-center font-display text-lg font-medium">{farm.name}</h2>
            )}
            <div className="my-2.5 border-t border-white/20" />
            <dl className="grid grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] gap-3 text-xs">
              <div><dt className="text-green-100/90">Location</dt><dd className="mt-0.5 break-words text-sm font-medium leading-snug">{farm.location || '—'}</dd></div>
              <div><dt className="text-green-100/90">Area</dt><dd className="mt-0.5 text-sm font-medium tnum">{farm.area ? `${farm.area} ${farm.area_unit || 'acres'}` : 'Not set'}</dd></div>
            </dl>
            <div className="mt-2.5 text-xs">
              <p className="text-green-100/90">Crops</p>
              <p className="mt-1 flex flex-wrap gap-1.5">
                {farmCrops.length ? farmCrops.map((c) => <span key={c.id} className="rounded-full bg-white/15 px-2 py-0.5 text-xs font-medium">{c.name}</span>) : <span className="text-green-100">None added yet</span>}
              </p>
            </div>
            {defaultFarmName && farm.name === defaultFarmName && (
              <p className="mt-2.5 text-[11px] leading-snug text-green-100/90">Default farm. Set its area and crops in <Link to="/data-acquisition" className="font-medium underline">Data Acquisition</Link>.</p>
            )}
            <div className="my-2.5 border-t border-white/20" />
            <p className="flex items-center justify-between text-sm font-medium">
              Latest soil record
              {rec && <span className="text-[11px] font-normal text-green-100/90">{fmtDate(rec.created_at)}</span>}
            </p>
            {rec ? (
              <dl className="mt-2 rounded-xl bg-black/20 px-3 py-2 text-xs">
                {rows.map((r) => (
                  <div key={r.label} className="flex justify-between py-0.5"><dt className="text-green-100/90">{r.label}</dt><dd className="font-medium tnum">{r.value}</dd></div>
                ))}
              </dl>
            ) : (
              <p className="mt-2 text-xs text-green-100">No soil measurements saved yet.</p>
            )}
          </>
        )}
      </div>

      <p className="absolute bottom-3 left-3 rounded-full bg-black/45 px-3 py-1 text-[11px] text-white backdrop-blur-sm">
        Decorative aerial photo · not a live map of your farm
      </p>
      <p className="absolute bottom-3 right-3 hidden text-[10px] text-white/80 sm:block">Photo: Artem Beliaikin (CC0)</p>
    </section>
  );
}

/* ------------------- Irrigation / pH / fertilizer (rule-based) ------------- */
export function IrrigationCard({ loading, soil, className = '', padding = 'p-3.5 xl:p-4' }) {
  const irr = soil?.analysis?.irrigation_recommendation;
  return (
    <DashCard label="Irrigation guidance" className={className} padding={padding}>
      <CardTitle icon={FiDroplet}>Irrigation</CardTitle>
      {loading ? <div className="skeleton mt-3 h-14 w-full" /> : !irr ? (
        <p className="mt-2 text-sm text-slate-500">Save soil moisture to get irrigation guidance. <Link to="/soil-analysis" className="font-medium text-green-700 underline">Analyze soil</Link></p>
      ) : (
        <>
          <p className="mt-2 text-sm font-medium leading-snug text-slate-900">{irr.status}</p>
          <p className="mt-0.5 text-xs leading-snug text-slate-600">{irr.schedule}</p>
          <div className="mt-auto flex flex-wrap items-center justify-between gap-x-2 gap-y-1 pt-2">
            <span className={`badge whitespace-nowrap capitalize ${irr.priority === 'critical' || irr.priority === 'high' ? 'badge-danger' : irr.priority === 'medium' ? 'badge-warning' : 'badge-success'}`}>{irr.priority} priority</span>
            <span className="text-[11px] text-slate-500">Advice only</span>
          </div>
        </>
      )}
    </DashCard>
  );
}

export function PhCard({ loading, soil, className = '', padding = 'p-3.5 xl:p-4' }) {
  const ph = soil?.analysis?.detailed_analysis?.ph;
  return (
    <DashCard label="Soil pH" className={className} padding={padding}>
      <CardTitle icon={FiSliders}>Soil pH</CardTitle>
      {loading ? <div className="skeleton mt-3 h-14 w-full" /> : !ph ? (
        <p className="mt-2 text-sm text-slate-500">No pH measurement saved yet.</p>
      ) : (
        <>
          <div className="mt-2 flex items-end justify-between gap-2">
            <p className="text-sm leading-tight text-slate-600">Status:<br /><span className="font-medium text-slate-900">{ph.status}</span></p>
            <p className="font-display text-[2.25rem] font-medium leading-none text-slate-900 tnum">{ph.value}</p>
          </div>
          <p className="mt-auto pt-2 text-xs leading-snug text-slate-600">{ph.action}</p>
        </>
      )}
    </DashCard>
  );
}

export function FertilizerCard({ loading, soil, recommendationCount, className = '', padding = 'p-3.5 xl:p-4' }) {
  const recs = soil?.analysis?.fertilizer_recommendations || [];
  return (
    <DashCard label="Fertilizer guidance" className={className} padding={padding}>
      <CardTitle icon={FiPackage}
        right={<Link to="/recommendations" className="inline-flex items-center gap-1 text-xs font-medium text-green-700 hover:text-green-800">
          {recommendationCount ? `${recommendationCount} saved` : 'View all'} <FiArrowRight aria-hidden="true" /></Link>}>
        Fertilizer guidance
      </CardTitle>
      <p className="mt-1 text-xs text-slate-500">Rule-based, from your latest soil record</p>
      {loading ? <div className="skeleton mt-2.5 h-12 w-full" /> : recs.length === 0 ? (
        <p className="mt-2.5 text-sm text-slate-500">Save soil measurements to see fertilizer guidance.</p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {recs.slice(0, 3).map((r) => (
            <li key={r.fertilizer} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-1.5">
              <span className="min-w-0 truncate text-sm font-medium text-slate-900">{r.fertilizer}</span>
              <span className={`badge shrink-0 capitalize ${r.priority === 'high' ? 'badge-danger' : r.priority === 'medium' ? 'badge-warning' : 'badge-success'}`}>{r.priority}</span>
            </li>
          ))}
        </ul>
      )}
    </DashCard>
  );
}

/* ----------------------- Yield analytics (real history) -------------------- */
export function YieldPanel({ loading, yields, className = '' }) {
  const nums = yields.map((y) => y.predicted_yield).filter((n) => typeof n === 'number');
  const latest = yields[0];
  const bars = [...yields].slice(0, 8).reverse();
  const max = Math.max(...nums, 0);
  const min = Math.min(...nums, 0);
  const avg = nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : 0;
  const r1 = (n) => Math.round(n * 10) / 10;
  const isSingle = nums.length === 1;

  return (
    <DashCard label="Yield estimates" className={className}>
      <CardTitle
        icon={FiTrendingUp}
        right={
          <Link
            to="/yield-prediction"
            className="text-xs font-medium text-green-700 hover:text-green-800"
          >
            Estimate
          </Link>
        }
      >
        Yield Estimates
      </CardTitle>
      <p className="mt-1 text-xs text-slate-500">
        Rule-based estimates, not a trained-model prediction
      </p>

      {loading ? (
        <div className="skeleton mt-4 h-28 w-full" />
      ) : !latest ? (
        <div className="flex flex-1 flex-col items-center justify-center py-6 text-center">
          <p className="text-sm font-medium text-slate-700">No yield estimates yet</p>
          <p className="mt-1 max-w-[16rem] text-xs text-slate-500">
            Estimate expected harvest yields based on crop, soil, and weather inputs.
          </p>
          <Link to="/yield-prediction" className="btn btn-secondary btn-sm mt-3">
            Estimate a yield
          </Link>
        </div>
      ) : isSingle ? (
        /* Single estimate: compact, balanced layout without oversized chart or duplicate min/max/avg */
        <div className="mt-3 flex flex-1 flex-col justify-between space-y-3">
          <div className="rounded-xl border border-green-200/80 bg-green-50/50 p-3.5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-green-800">
                  Estimated Yield
                </span>
                <div className="mt-0.5 flex items-baseline gap-1.5">
                  <span className="font-display text-3xl font-semibold text-slate-900 tnum">
                    ≈ {latest.predicted_yield}
                  </span>
                  <span className="text-xs font-medium text-slate-600">
                    {latest.yield_unit || 'tons/hectare'}
                  </span>
                </div>
              </div>
              <span className="badge badge-success shrink-0 font-medium">
                {latest.crop_name}
              </span>
            </div>

            <div className="mt-2.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 border-t border-green-200/60 pt-2 text-[11px] text-slate-600">
              <span className="font-medium text-slate-800">{latest.crop_name}</span>
              <span className="text-slate-300">·</span>
              <span>{latest.yield_unit || 'tons/hectare'}</span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-500">{fmtDate(latest.created_at)}</span>
            </div>
          </div>

          {/* Compact summary section replacing the empty chart */}
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Estimate Parameters
            </p>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg border border-slate-100 bg-white p-2 shadow-xs">
                <span className="block text-[10px] text-slate-400">Crop</span>
                <span className="mt-0.5 block truncate font-semibold text-slate-800">
                  {latest.crop_name || '—'}
                </span>
              </div>
              <div className="rounded-lg border border-slate-100 bg-white p-2 shadow-xs">
                <span className="block text-[10px] text-slate-400">Area</span>
                <span className="mt-0.5 block truncate font-semibold text-slate-800">
                  {latest.area ? `${latest.area} ha` : 'Baseline'}
                </span>
              </div>
              <div className="rounded-lg border border-slate-100 bg-white p-2 shadow-xs">
                <span className="block text-[10px] text-slate-400">Season</span>
                <span className="mt-0.5 block truncate font-semibold text-slate-800">
                  {latest.season || 'Standard'}
                </span>
              </div>
              <div className="rounded-lg border border-slate-100 bg-white p-2 shadow-xs">
                <span className="block text-[10px] text-slate-400">Date</span>
                <span className="mt-0.5 block truncate font-semibold text-slate-800">
                  {fmtDate(latest.created_at) || 'Recent'}
                </span>
              </div>
            </div>
            {latest.area && latest.predicted_yield ? (
              <p className="mt-2 text-center text-[11px] text-slate-600">
                Projected total: <strong className="text-slate-900">{Math.round(latest.area * latest.predicted_yield * 10) / 10} tons</strong> over {latest.area} ha
              </p>
            ) : null}
          </div>

          <div className="mt-auto flex items-center justify-between border-t border-slate-100 pt-2.5 text-[11px] text-slate-500">
            <span>Single logged record</span>
            <Link
              to="/yield-prediction"
              className="inline-flex items-center gap-1 font-medium text-green-700 hover:text-green-800"
            >
              New estimate <FiArrowRight className="text-[10px]" aria-hidden="true" />
            </Link>
          </div>
        </div>
      ) : (
        /* Multiple estimates: compact chart with real max/min/avg variance */
        <>
          <div className="mt-3 text-center">
            <p className="font-display text-[2.75rem] font-medium leading-none text-slate-900 tnum">
              ≈ {latest.predicted_yield}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {latest.yield_unit} · {latest.crop_name} · {fmtDate(latest.created_at)}
            </p>
          </div>
          <div
            className="relative mt-3 h-16 w-full"
            role="img"
            aria-label={`Last ${bars.length} yield estimates, oldest to newest`}
          >
            <div className="absolute inset-0 flex items-end justify-center gap-2 border-b border-slate-200">
              {bars.map((y) => (
                <span
                  key={y.id}
                  title={`${y.crop_name}: ${y.predicted_yield} ${y.yield_unit}`}
                  className="w-full max-w-[2.25rem] rounded-t-md bg-green-600/85"
                  style={{ height: `${Math.max(12, (y.predicted_yield / (max || 1)) * 100)}%` }}
                />
              ))}
            </div>
          </div>
          <dl className="mt-auto grid grid-cols-3 gap-2 pt-3 text-center">
            {[['Max', max], ['Min', min], ['Avg', avg]].map(([label, n]) => (
              <div key={label}>
                <dd className="font-display text-xl font-medium text-slate-900 tnum">{r1(n)}</dd>
                <dt className="text-[11px] text-slate-500">{label}</dt>
              </div>
            ))}
          </dl>
          <p className="mt-2 text-center text-[11px] text-slate-500">
            Across your {nums.length} estimates
          </p>
        </>
      )}
    </DashCard>
  );
}

/* --------------------------- Recent leaf scans ----------------------------- */
export function ScansPanel({ loading, scans, detector, className = '' }) {
  const hasDemo = scans.some((p) => p.is_demo === 'true');
  return (
    <DashCard label="Recent leaf scans" className={className}>
      <CardTitle icon={FiImage} right={<Link to="/prediction-history" className="inline-flex items-center gap-1 text-xs font-medium text-green-700 hover:text-green-800">History <FiArrowRight aria-hidden="true" /></Link>}>
        Recent Leaf Scans
      </CardTitle>
      {hasDemo && (
        <p className="mt-1 text-xs text-amber-800">
          {detector?.model_loaded
            ? 'Historical list includes simulated demo scans.'
            : 'Detector is simulated: results are not real diagnoses.'}
        </p>
      )}
      {loading ? (
        <div className="mt-3 space-y-2" aria-hidden="true">{Array.from({ length: 3 }, (_, i) => <div key={i} className="skeleton h-11 w-full" />)}</div>
      ) : scans.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center py-6 text-center">
          <p className="text-sm font-medium text-slate-700">No leaf scans yet</p>
          <p className="mt-1 max-w-[16rem] text-xs text-slate-500">Upload a leaf image to run your first disease and pest check.</p>
          <Link to="/disease-detection" className="btn btn-secondary btn-sm mt-3"><FiSearch aria-hidden="true" /> Upload an image</Link>
        </div>
      ) : (
        <ul className="mt-3 space-y-2">
          {scans.slice(0, 5).map((p) => {
            const thumb = uploadUrl(p.image_path);
            return (
              <li key={p.id} className="flex items-center gap-3 rounded-xl bg-slate-50 p-2">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-slate-200 text-slate-500">
                  {thumb ? <img src={thumb} alt="" loading="lazy" className="h-full w-full object-cover" onError={(e) => { e.currentTarget.style.display = 'none'; }} /> : <FiImage aria-hidden="true" />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-slate-900">{p.disease_name || p.pest_name || '—'}</span>
                  <span className="block truncate text-[11px] text-slate-500">{p.crop_name || 'Crop not specified'} · {fmtDate(p.created_at)}{p.confidence !== null && p.confidence !== undefined ? ` · ${p.confidence}%` : ''}</span>
                </span>
                {p.is_demo === 'true' && <span className="badge badge-neutral shrink-0">Demo</span>}
              </li>
            );
          })}
        </ul>
      )}

      {/* Real status from /api/detection/status */}
      {detector && (
        <p className="mt-auto flex items-start gap-2 border-t border-slate-100 pt-3 text-[11px] leading-snug text-slate-500" role="status">
          <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${detector.model_loaded ? 'bg-green-500' : 'bg-amber-500'}`} aria-hidden="true" />
          {detector.model_loaded
            ? 'Disease detector: trained model loaded.'
            : 'Disease detector: simulated. No trained model is loaded, so scan results are demonstrations, not diagnoses.'}
        </p>
      )}
    </DashCard>
  );
}
