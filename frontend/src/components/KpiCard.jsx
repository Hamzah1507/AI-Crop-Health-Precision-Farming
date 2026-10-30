import { Link } from 'react-router-dom';
import { FiArrowUpRight } from 'react-icons/fi';

// One dashboard metric. `value` is whatever the backend returned; nothing is invented here.
export default function KpiCard({ icon: Icon, label, value, hint, to }) {
  return (
    <Link to={to} className="card-link group flex flex-col gap-4 p-5" aria-label={`${label}: ${value}. Open ${label}`}>
      <div className="flex items-start justify-between">
        <span className="icon-tile" aria-hidden="true"><Icon /></span>
        <FiArrowUpRight className="text-slate-300 transition-colors group-hover:text-green-600" aria-hidden="true" />
      </div>
      <div>
        <p className="font-display text-[2.25rem] leading-none font-medium text-slate-900 tnum">{value}</p>
        <p className="mt-2 text-sm font-medium text-slate-700">{label}</p>
        {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
      </div>
    </Link>
  );
}

export function KpiCardSkeleton() {
  return (
    <div className="card flex flex-col gap-4 p-5" aria-hidden="true">
      <div className="skeleton h-10 w-10" />
      <div>
        <div className="skeleton h-9 w-16" />
        <div className="skeleton mt-3 h-4 w-28" />
      </div>
    </div>
  );
}
