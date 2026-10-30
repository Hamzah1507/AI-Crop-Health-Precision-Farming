import { Link } from 'react-router-dom';
import { FiSun, FiSearch, FiDroplet, FiCloud, FiAlertTriangle } from 'react-icons/fi';

// ---------------------------------------------------------------------------
// Authentication screens (Login + Register) - shared layout and form pieces.
// All styling here is scoped to these two screens; nothing global is changed.
// Palette: forest #0F3D2E, deep-green action #17583A, warm off-white #F5F3ED.
// ---------------------------------------------------------------------------

const POINTS = [
  { icon: FiSearch, text: 'Leaf-image disease and pest check (simulated until a trained model is added)' },
  { icon: FiDroplet, text: 'Rule-based soil analysis, fertilizer and irrigation guidance' },
  { icon: FiCloud, text: 'Live weather and 5-day forecast from Open-Meteo' },
];

// Decorative botanical line-art: one stem with paired leaves. Purely visual.
function Botanical({ className = '' }) {
  const leaves = [
    [203, 452, -150, 0.95], [207, 452, -28, 0.95],
    [200, 372, -158, 0.85], [212, 366, -22, 0.85],
    [205, 288, -150, 0.72], [214, 280, -30, 0.72],
    [212, 206, -156, 0.58], [219, 198, -24, 0.58],
    [218, 128, -148, 0.44], [222, 120, -32, 0.44],
  ];
  return (
    <svg viewBox="0 0 420 520" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"
      className={className} aria-hidden="true" focusable="false">
      <defs>
        <g id="auth-leaf">
          <path d="M0 0 C 34 -22, 84 -22, 120 0 C 84 22, 34 22, 0 0 Z" />
          <path d="M6 0 H 110" />
        </g>
      </defs>
      <path d="M198 520 C 204 440, 196 360, 208 280 S 224 130, 226 40" />
      {leaves.map(([x, y, angle, scale]) => (
        <use key={`${x}-${y}`} href="#auth-leaf" transform={`translate(${x} ${y}) rotate(${angle}) scale(${scale})`} />
      ))}
    </svg>
  );
}

function Brand({ onDark = true }) {
  return (
    <div className="flex items-center gap-3.5">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#237A4B] text-xl text-white ring-1 ring-white/20" aria-hidden="true"><FiSun /></span>
      <div className="leading-tight">
        <p className={`font-display text-[1.375rem] font-medium tracking-tight ${onDark ? 'text-white' : 'text-slate-900'}`}>CropHealth AI</p>
        <p className={`mt-0.5 text-[11px] font-medium uppercase tracking-[0.14em] ${onDark ? 'text-[#A9D4BD]' : 'text-slate-500'}`}>Precision Farming</p>
      </div>
    </div>
  );
}

// Shared layout: forest-green brand panel + warm off-white form side (stacked with a compact banner on small screens).
export default function AuthShell({ title, subtitle, children }) {
  return (
    <div className="flex min-h-screen flex-col bg-[#F5F3ED] lg:grid lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      {/* Brand panel: full on desktop, compact banner on tablets and phones */}
      <aside aria-label="About CropHealth AI"
        className="relative isolate overflow-hidden bg-[#0F3D2E] px-5 py-5 text-white sm:px-8 lg:flex lg:min-h-screen lg:flex-col lg:justify-between lg:px-12 lg:py-12 xl:px-16">
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(70%_55%_at_90%_0%,rgba(63,150,104,0.22),transparent_70%)]" aria-hidden="true" />
        <Botanical className="pointer-events-none absolute -bottom-44 -right-24 -z-10 hidden w-[27rem] -rotate-6 text-white/[0.08] lg:block" />
        <Botanical className="pointer-events-none absolute -right-8 -top-10 -z-10 w-44 rotate-12 text-white/[0.09] sm:w-56 lg:hidden" />

        <Brand />

        <div className="hidden lg:block">
          <p className="font-display text-[clamp(2.25rem,3.5vw,3.5rem)] font-medium leading-[1.08] tracking-tight text-white [text-wrap:balance]">
            Know your crops, soil and weather <span className="text-[#A9DBBF]">in one place.</span>
          </p>
          <ul className="mt-10 max-w-md divide-y divide-white/10 border-y border-white/10">
            {POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-4 py-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/[0.07] text-lg text-[#A9DBBF] ring-1 ring-white/10" aria-hidden="true"><Icon /></span>
                <span className="pt-1.5 text-[15px] leading-relaxed text-[#DCEBE2]">{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="hidden text-xs leading-relaxed tracking-wide text-[#9DC4AE] lg:block">
          AI-Powered Intelligent Crop Health &amp; Precision Farming Platform
        </p>
      </aside>

      {/* Form side */}
      <main className="flex flex-1 items-center justify-center px-5 py-8 sm:px-10 sm:py-12">
        <div className="w-full max-w-[26.5rem]">
          <div className="mb-7 text-center lg:text-left">
            <h1 className="font-display text-[2.125rem] font-medium leading-tight tracking-tight text-slate-900 sm:text-[2.375rem]">{title}</h1>
            <p className="mt-2 text-[15px] leading-relaxed text-slate-600">{subtitle}</p>
          </div>
          <div className="animate-fadeIn rounded-2xl border border-[#E4E0D4] bg-white p-6 shadow-[0_1px_2px_rgba(15,61,46,0.05),0_18px_40px_-18px_rgba(15,61,46,0.18)] sm:p-8">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}

/* --------------------------- Shared form pieces ---------------------------- */

// Labelled input with a leading icon, optional hint, and an accessible inline error.
export function AuthField({ id, label, icon: Icon, error, invalid = false, describedBy, ...inputProps }) {
  const isInvalid = invalid || !!error;
  const desc = [error ? `${id}-error` : null, describedBy].filter(Boolean).join(' ') || undefined;
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-[13px] font-medium text-slate-800">{label}</label>
      <div className="relative">
        <Icon className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-base text-slate-500" aria-hidden="true" />
        <input id={id} {...inputProps} aria-invalid={isInvalid || undefined} aria-describedby={desc}
          className={`input !h-12 !rounded-xl pl-10 pr-3.5 !text-[15px] ${isInvalid ? '!border-red-500 focus:!shadow-[0_0_0_3px_rgba(239,68,68,0.15)]' : ''}`} />
      </div>
      {error && <p id={`${id}-error`} role="alert" className="mt-1.5 flex items-start gap-1.5 text-[13px] leading-snug text-red-700"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />{error}</p>}
    </div>
  );
}

// Form-level error (for example a rejected login or a server-side registration error).
export function AuthAlert({ id = 'auth-error', children }) {
  if (!children) return null;
  return (
    <div id={id} role="alert" className="mb-5 flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 px-3.5 py-3 text-sm leading-snug text-red-800">
      <FiAlertTriangle className="mt-0.5 shrink-0 text-red-600" aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}

// Primary action: deep forest green with clear hover, focus and loading/disabled states.
export function AuthSubmit({ loading, loadingLabel, icon: Icon, children }) {
  return (
    <button type="submit" disabled={loading} aria-busy={loading || undefined}
      className="inline-flex h-12 w-full items-center justify-center gap-2.5 rounded-xl bg-[#17583A] text-[15px] font-medium text-white shadow-[0_1px_2px_rgba(15,61,46,0.35)] transition-colors duration-150 hover:bg-[#0F3D2E] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2F8559] disabled:cursor-not-allowed disabled:bg-[#17583A]/75">
      {loading ? <span className="h-4 w-4 spinner" aria-hidden="true" /> : <Icon aria-hidden="true" />}
      {loading ? loadingLabel : children}
    </button>
  );
}

// "Don't have an account? Register" row: set apart by a divider, with a clearly findable link.
export function AuthSwitch({ prompt, to, linkLabel }) {
  return (
    <p className="mt-7 border-t border-[#EDEAE0] pt-6 text-center text-sm text-slate-600">
      {prompt}{' '}
      <Link to={to} className="rounded font-semibold text-[#17583A] underline decoration-[#17583A]/35 decoration-2 underline-offset-4 transition-colors hover:text-[#0F3D2E] hover:decoration-[#0F3D2E] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2F8559]">
        {linkLabel}
      </Link>
    </p>
  );
}
