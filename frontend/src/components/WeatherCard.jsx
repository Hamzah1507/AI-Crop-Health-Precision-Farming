import { FiCloud, FiAlertTriangle, FiCheckCircle } from 'react-icons/fi';

const fmt = (v, unit = '') => (v === null || v === undefined ? '—' : `${v}${unit}`);

// Shows weather returned by POST /api/weather/fetch. Live Open-Meteo data and
// fallback placeholder values are visually distinct and labelled.
export default function WeatherCard({ weather }) {
  if (!weather) return null;
  const live = weather.is_live;

  const tiles = [
    { label: 'Temperature', value: fmt(weather.temperature, '°C') },
    { label: 'Humidity', value: fmt(weather.humidity, '%') },
    { label: 'Rainfall (now)', value: fmt(weather.rainfall, ' mm') },
    { label: 'Wind speed', value: fmt(weather.wind_speed, ' km/h') },
    { label: 'Conditions', value: weather.description || '—' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-slate-800 flex items-center gap-1.5">
          <FiCloud className="text-slate-400" />
          {live ? (weather.resolved_location || weather.location) : weather.location}
        </p>
        {live ? (
          <span className="badge badge-success"><FiCheckCircle className="text-[11px]" aria-hidden="true" /> Live data</span>
        ) : (
          <span className="badge badge-warning"><FiAlertTriangle className="text-[11px]" aria-hidden="true" /> Not live</span>
        )}
      </div>

      {!live && (
        <div className="alert alert-warning" role="status">
          <FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>The live weather service could not be reached. The values below are <strong>placeholders, not real weather</strong>, and were not saved. Please try again later.</span>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {tiles.map((t) => (
          <div key={t.label} className={`border rounded-md p-3 ${live ? 'bg-slate-50 border-gray-200' : 'bg-amber-50/40 border-amber-200'}`}>
            <p className="text-xs text-slate-500">{t.label}</p>
            <p className="text-sm font-semibold text-slate-800 mt-0.5 break-words">{t.value}</p>
          </div>
        ))}
      </div>

      {live && weather.forecast?.length > 0 && (
        <div>
          <p className="text-xs font-medium text-slate-500 mb-2">5-day forecast</p>
          <div className="overflow-x-auto border border-gray-200 rounded-md">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 text-slate-500">
                <tr>
                  <th className="text-left font-medium px-3 py-2">Date</th>
                  <th className="text-left font-medium px-3 py-2">Conditions</th>
                  <th className="text-right font-medium px-3 py-2">Min / Max</th>
                  <th className="text-right font-medium px-3 py-2">Rain</th>
                  <th className="text-right font-medium px-3 py-2">Chance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-slate-700">
                {weather.forecast.map((d) => (
                  <tr key={d.date}>
                    <td className="px-3 py-2 whitespace-nowrap">{new Date(`${d.date}T00:00:00`).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</td>
                    <td className="px-3 py-2">{d.description}</td>
                    <td className="px-3 py-2 text-right tnum whitespace-nowrap">{fmt(d.temp_min, '°')} / {fmt(d.temp_max, '°C')}</td>
                    <td className="px-3 py-2 text-right tnum whitespace-nowrap">{fmt(d.precipitation_sum, ' mm')}</td>
                    <td className="px-3 py-2 text-right tnum">{fmt(d.precipitation_probability, '%')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {live && weather.forecast_alerts?.length > 0 && (
        <ul className="space-y-1.5">
          {weather.forecast_alerts.map((a, i) => (
            <li key={i} className="alert alert-warning"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />{a}</li>
          ))}
        </ul>
      )}

      {live && weather.attribution && (
        <p className="text-[11px] text-slate-500">
          <a href={weather.attribution_url || 'https://open-meteo.com/'} target="_blank" rel="noopener noreferrer" className="hover:text-green-700 underline">
            {weather.attribution}
          </a>
        </p>
      )}
    </div>
  );
}
