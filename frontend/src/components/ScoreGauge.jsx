// Semicircle gauge for the soil health score. Value and label come straight from the
// backend response; the colour follows the backend STATUS so a "Poor" result can never
// be drawn in a positive colour.
import { STATUS_COLOR } from '../utils/statusColors';

export default function ScoreGauge({ score, status }) {
  const value = Math.max(0, Math.min(100, Number(score) || 0));
  const color = STATUS_COLOR[status] || '#8F9A92';
  const arc = 'M 20 100 A 80 80 0 0 1 180 100';

  return (
    <div className="relative mx-auto w-full max-w-[260px]" role="img" aria-label={`Soil health score ${value} out of 100, status ${status}`}>
      <svg viewBox="0 0 200 112" className="w-full" aria-hidden="true">
        <path d={arc} fill="none" stroke="#E6E3D9" strokeWidth="14" strokeLinecap="round" />
        <path d={arc} fill="none" stroke={color} strokeWidth="14" strokeLinecap="round" pathLength="100"
          strokeDasharray={`${value} 100`} style={{ transition: 'stroke-dasharray 0.4s ease-out' }} />
      </svg>
      <div className="absolute inset-x-0 bottom-0 text-center">
        <p className="font-display text-4xl font-medium leading-none text-slate-900 tnum">{value}</p>
        <p className="mt-1 text-xs font-medium" style={{ color }}>{status}</p>
      </div>
    </div>
  );
}
