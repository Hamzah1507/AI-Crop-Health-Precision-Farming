import { useState, useEffect, useRef } from 'react';
import { Outlet, NavLink, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/auth';
import { detectionAPI } from '../services/api';
import {
  FiGrid, FiUpload, FiSearch, FiClock, FiUser, FiLogOut, FiMenu, FiX, FiSun,
  FiDroplet, FiStar, FiTrendingUp, FiActivity, FiChevronDown, FiMessageSquare
} from 'react-icons/fi';

// Rail entries match the routes in App.jsx. The chatbot, analytics and admin
// screens are not built on the frontend, so they are intentionally not listed.
// Groups are separated by a thin divider, as in the reference rail.
const NAV_GROUPS = [
  [{ to: '/dashboard', icon: FiGrid, label: 'Dashboard' }],
  [
    { to: '/data-acquisition', icon: FiUpload, label: 'Data Acquisition' },
    { to: '/disease-detection', icon: FiSearch, label: 'Disease Detection' },
    { to: '/soil-analysis', icon: FiDroplet, label: 'Soil Analysis' },
    { to: '/recommendations', icon: FiStar, label: 'Recommendations' },
    { to: '/yield-prediction', icon: FiTrendingUp, label: 'Yield Estimate' },
  ],
  [
    { to: '/chatbot', icon: FiMessageSquare, label: 'AI Agronomist' },
    { to: '/prediction-history', icon: FiClock, label: 'Prediction History' },
  ],
];
const PROFILE_LINK = { to: '/profile', icon: FiUser, label: 'My Profile' };

// True when the viewport is at least the Tailwind `lg` breakpoint
function useIsDesktop() {
  const query = '(min-width: 1024px)';
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = (e) => setMatches(e.matches);
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, []);
  return matches;
}

// One rail/drawer entry. Desktop: icon-only tile with a tooltip. Mobile drawer: icon + label.
function RailLink({ link, onNavigate }) {
  const Icon = link.icon;
  return (
    <NavLink to={link.to} onClick={onNavigate} title={link.label}
      className={({ isActive }) =>
        `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors duration-150
         lg:mx-auto lg:h-11 lg:w-11 lg:justify-center lg:px-0 lg:py-0 ${
          isActive
            ? 'bg-green-50 font-medium text-green-800 lg:bg-white lg:text-green-700 lg:shadow-[0_1px_4px_rgba(20,32,26,0.12)]'
            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 lg:hover:bg-white/70'
        }`
      }>
      <Icon className="shrink-0 text-lg" aria-hidden="true" />
      <span className="lg:sr-only">{link.label}</span>
      <span aria-hidden="true"
        className="pointer-events-none absolute left-full z-50 ml-3 hidden whitespace-nowrap rounded-md bg-slate-900 px-2.5 py-1 text-xs font-medium text-white opacity-0 shadow-lift transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100 lg:block">
        {link.label}
      </span>
    </NavLink>
  );
}

function AccountMenu({ user, onLogout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClick);
    return () => { document.removeEventListener('keydown', onKey); document.removeEventListener('mousedown', onClick); };
  }, [open]);

  return (
    <div ref={ref} className="relative shrink-0">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-haspopup="menu" aria-expanded={open} aria-label="Account menu"
        className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white py-2 pl-2 pr-3 shadow-card transition-colors hover:border-slate-300">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-green-700 font-display text-lg text-white" aria-hidden="true">
          {user?.username?.[0]?.toUpperCase() || 'U'}
        </span>
        <span className="hidden min-w-0 text-left leading-tight sm:block">
          <span className="block max-w-[11rem] truncate text-sm font-medium text-slate-900">{user?.username}</span>
          <span className="block max-w-[11rem] truncate text-xs text-slate-500">{user?.email || <span className="capitalize">{user?.role}</span>}</span>
        </span>
        <FiChevronDown className={`hidden text-slate-500 transition-transform sm:block ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-full z-50 mt-2 w-52 rounded-xl border border-slate-200 bg-white p-1.5 shadow-lift">
          <Link to="/profile" role="menuitem" onClick={() => setOpen(false)}
            className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
            <FiUser aria-hidden="true" /> My profile
          </Link>
          <button type="button" role="menuitem" onClick={onLogout}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50">
            <FiLogOut aria-hidden="true" /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [detector, setDetector] = useState(null);   // real status from /api/detection/status
  const isDesktop = useIsDesktop();
  const closeRef = useRef(null);

  const drawerHidden = !isDesktop && !sidebarOpen;
  const onDashboard = pathname === '/dashboard';

  useEffect(() => {
    detectionAPI.getStatus().then((res) => setDetector(res.data)).catch(() => setDetector(null));
  }, []);

  // Escape closes the mobile drawer; focus moves into it when it opens
  useEffect(() => {
    if (!sidebarOpen) return undefined;
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') setSidebarOpen(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [sidebarOpen]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };
  const closeDrawer = () => setSidebarOpen(false);

  return (
    <div className="flex min-h-screen bg-ivory">
      <a href="#main" className="skip-link">Skip to main content</a>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden" onClick={closeDrawer} aria-hidden="true" />
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Rail (desktop) / drawer (mobile)                                  */}
      {/* ---------------------------------------------------------------- */}
      <aside
        aria-label="Primary"
        aria-hidden={drawerHidden || undefined}
        inert={drawerHidden || undefined}
        className={`fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 transform flex-col border-r border-slate-200 bg-white transition-transform duration-200
          lg:sticky lg:top-0 lg:h-screen lg:w-[76px] lg:translate-x-0 lg:bg-slate-50 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>

        {/* Brand tile */}
        <div className="flex h-[72px] items-center gap-3 px-4 lg:justify-center lg:px-0 lg:pt-3">
          <Link to="/dashboard" onClick={closeDrawer} title="CropHealth AI - Dashboard" aria-label="CropHealth AI, go to dashboard"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-green-700 text-xl text-white shadow-card">
            <FiSun aria-hidden="true" />
          </Link>
          <div className="min-w-0 flex-1 lg:hidden">
            <p className="font-display text-lg font-medium leading-tight text-slate-900">CropHealth AI</p>
            <p className="text-[11px] leading-tight text-slate-500">Precision Farming</p>
          </div>
          <button ref={closeRef} type="button" onClick={closeDrawer}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden" aria-label="Close navigation">
            <FiX className="text-lg" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-3 lg:overflow-visible lg:px-0 lg:py-4" aria-label="Main navigation">
          {NAV_GROUPS.map((group, i) => (
            <div key={i}>
              {i > 0 && <div className="mx-3 my-3 border-t border-slate-200 lg:mx-4 lg:my-4" aria-hidden="true" />}
              <div className="space-y-1 lg:space-y-2">
                {group.map((link) => <RailLink key={link.to} link={link} onNavigate={closeDrawer} />)}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom: profile + real detector status */}
        <div className="space-y-1 border-t border-slate-200 px-3 py-3 lg:space-y-2 lg:border-0 lg:px-0 lg:pb-5">
          <RailLink link={PROFILE_LINK} onNavigate={closeDrawer} />
          {detector && (
            <div className="group relative mx-3 flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-600 lg:mx-auto lg:h-11 lg:w-11 lg:justify-center lg:bg-transparent lg:px-0 lg:py-0"
              tabIndex={0} role="status"
              aria-label={detector.model_loaded ? 'Disease detector: trained model loaded' : 'Disease detector: simulated, no trained model loaded'}>
              <span className="relative flex h-5 w-5 items-center justify-center text-slate-500" aria-hidden="true">
                <FiActivity />
                <span className={`absolute -right-1 -top-1 h-2 w-2 rounded-full ring-2 ring-slate-50 ${detector.model_loaded ? 'bg-green-500' : 'bg-amber-500'}`} />
              </span>
              <span className="lg:hidden">Detector: {detector.model_loaded ? 'trained model' : 'simulated'}</span>
              <span aria-hidden="true"
                className="pointer-events-none absolute left-full z-50 ml-3 hidden whitespace-nowrap rounded-md bg-slate-900 px-2.5 py-1 text-xs font-medium text-white opacity-0 shadow-lift transition-opacity group-hover:opacity-100 group-focus:opacity-100 lg:block">
                Disease detector: {detector.model_loaded ? 'trained model loaded' : 'simulated (no trained model)'}
              </span>
            </div>
          )}
        </div>
      </aside>

      {/* ---------------------------------------------------------------- */}
      {/* Workspace                                                        */}
      {/* ---------------------------------------------------------------- */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-start gap-3 px-4 pb-3 pt-4 sm:px-5 lg:px-6 lg:pt-5">
          <button type="button" onClick={() => setSidebarOpen(true)}
            className="-ml-1 mt-1 rounded-md p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
            aria-label="Open navigation" aria-expanded={sidebarOpen}>
            <FiMenu className="text-lg" />
          </button>

          <div className="min-w-0 flex-1">
            {onDashboard ? (
              <>
                <h1 className="font-display text-[1.625rem] font-medium leading-tight tracking-tight text-slate-900 sm:text-[1.875rem]">
                  Hi, {user?.username || 'there'}!
                </h1>
                <p className="mt-0.5 text-sm text-slate-500">Here&apos;s today&apos;s overview of your farms, soil and weather.</p>
              </>
            ) : (
              <p className="hidden truncate pt-3 text-sm text-slate-500 sm:block">
                AI-Powered Intelligent Crop Health &amp; Precision Farming Platform
              </p>
            )}
          </div>

          {onDashboard && (
            <div className="mt-1 hidden items-center gap-2 md:flex">
              <Link to="/chatbot" className="btn btn-secondary"><FiMessageSquare aria-hidden="true" /> AI Agronomist</Link>
              <Link to="/data-acquisition" className="btn btn-secondary"><FiUpload aria-hidden="true" /> Add data</Link>
              <Link to="/disease-detection" className="btn btn-primary"><FiSearch aria-hidden="true" /> Detect disease</Link>
            </div>
          )}
          <AccountMenu user={user} onLogout={handleLogout} />
        </header>

        <main id="main" tabIndex={-1} className="flex-1 px-4 pb-6 sm:px-5 lg:px-6 focus:outline-none">
          <div className="mx-auto max-w-[1680px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
