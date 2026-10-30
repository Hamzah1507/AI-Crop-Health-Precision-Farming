import { useState } from 'react';
import { Link } from 'react-router-dom';
import { FiCloud, FiSearch, FiDroplet, FiWind, FiAlertTriangle, FiCheckCircle, FiMapPin } from 'react-icons/fi';
import SectionCard from './SectionCard';
import EmptyState from './EmptyState';

const num = (v, unit = '') => (v === null || v === undefined ? '—' : `${v}${unit}`);
const dayName = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { weekday: 'short' });

// Compact dashboard weather card. It shows ONLY real data from the backend:
// live Open-Meteo values. If the service is unreachable the backend returns
// flagged placeholder numbers (is_live=false); those are never displayed here.
export default function WeatherSummary({ location, weather, loading, error, onLookup }) {
  const [query, setQuery] = useState('');

  const submit = (e) => {
    e.preventDefault();
    if (query.trim()) onLookup(query.trim());
  };

  const live = weather?.is_live === true;

  const lookupForm = (
    <form onSubmit={submit} className="flex items-center gap-2" role="search" aria-label="Look up weather for a location">
      <label htmlFor="weather-location" className="sr-only">Location</label>
      <input id="weather-location" type="text" value={query} onChange={(e) => setQuery(e.target.value)}
        placeholder="Check a location" className="input !min-h-[2rem] !py-1 !text-xs w-36 sm:w-44" />
      <button type="submit" className="btn btn-secondary btn-sm" disabled={!query.trim() || loading} aria-label="Look up weather">
        <FiSearch aria-hidden="true" />
      </button>
    </form>
  );

  return (
    <SectionCard icon={FiCloud} title="Weather" className="h-full" description={live ? (weather.resolved_location || location) : (location || 'No location selected')} actions={lookupForm}>
      {loading && (
        <div className="space-y-3" aria-busy="true" aria-label="Loading weather">
          <div className="skeleton h-12 w-40" />
          <div className="skeleton h-8 w-full" />
          <div className="skeleton h-16 w-full" />
        </div>
      )}

      {!loading && error && <div className="alert alert-error" role="alert"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />{error}</div>}

      {!loading && !error && !location && (
        <EmptyState compact icon={FiMapPin} title="No location yet"
          description="Add a farm with a location in Data Acquisition to see its weather here, or check any place using the box above.">
          <Link to="/data-acquisition" className="btn btn-secondary btn-sm">Add a farm location</Link>
        </EmptyState>
      )}

      {!loading && !error && weather && !live && (
        <div className="alert alert-warning" role="status">
          <FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>Live weather is unavailable right now, so no weather values are shown. Please try again in a moment.</span>
        </div>
      )}

      {!loading && !error && live && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="font-display text-5xl font-medium leading-none text-slate-900 tnum">
                {num(weather.temperature)}<span className="ml-1 text-2xl text-slate-500">°C</span>
              </p>
              <p className="mt-2 text-sm text-slate-700">{weather.description}</p>
            </div>
            <span className="badge badge-success"><FiCheckCircle className="text-[11px]" aria-hidden="true" /> Live data</span>
          </div>

          <div className="flex flex-wrap gap-2">
            <span className="chip"><FiDroplet className="text-green-600" aria-hidden="true" /> Humidity <strong className="font-semibold tnum">{num(weather.humidity, '%')}</strong></span>
            <span className="chip"><FiWind className="text-green-600" aria-hidden="true" /> Wind <strong className="font-semibold tnum">{num(weather.wind_speed, ' km/h')}</strong></span>
            <span className="chip"><FiCloud className="text-green-600" aria-hidden="true" /> Rain now <strong className="font-semibold tnum">{num(weather.rainfall, ' mm')}</strong></span>
          </div>

          {weather.forecast?.length > 0 && (
            <ul className="grid grid-cols-5 gap-2" aria-label="5-day forecast">
              {weather.forecast.map((d) => (
                <li key={d.date} className="panel px-2 py-2.5 text-center">
                  <p className="text-xs font-medium text-slate-500">{dayName(d.date)}</p>
                  <p className="mt-1 text-sm font-semibold text-slate-900 tnum">{num(d.temp_max, '°')}</p>
                  <p className="text-xs text-slate-500 tnum">{num(d.temp_min, '°')}</p>
                  <p className="mt-1 text-[11px] text-green-700 tnum">{num(d.precipitation_sum, ' mm')}</p>
                </li>
              ))}
            </ul>
          )}

          {weather.forecast_alerts?.length > 0 && (
            <ul className="space-y-1.5">
              {weather.forecast_alerts.slice(0, 2).map((a) => (
                <li key={a} className="alert alert-warning !py-2 text-xs"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />{a}</li>
              ))}
            </ul>
          )}

          <p className="text-[11px] text-slate-500">
            <a href={weather.attribution_url || 'https://open-meteo.com/'} target="_blank" rel="noopener noreferrer" className="underline hover:text-green-700">
              {weather.attribution}
            </a>
          </p>
        </div>
      )}
    </SectionCard>
  );
}
