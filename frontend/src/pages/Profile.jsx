import { useState, useEffect } from 'react';
import { useAuth } from '../context/auth';
import { Link } from 'react-router-dom';
import { usersAPI, farmsAPI, cropsAPI } from '../services/api';
import { apiError } from '../utils/apiError';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import { FiSave, FiCheckCircle, FiUser, FiRotateCcw, FiAlertTriangle, FiMapPin } from 'react-icons/fi';

const BLANK = { full_name: '', phone: '', address: '', experience_years: 0 };

export default function Profile() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(BLANK);
  const [savedProfile, setSavedProfile] = useState(BLANK);   // last values stored on the server (for Cancel)
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const [farms, setFarms] = useState({ loading: true, items: [], crops: [], error: '' });

  useEffect(() => {
    usersAPI.getProfile().then((res) => {
      if (res.data.profile) { setProfile(res.data.profile); setSavedProfile(res.data.profile); }
      setLoading(false);
    }).catch((err) => {
      setError(apiError(err, 'Could not load your profile.'));
      setLoading(false);
    });
    // Only the signed-in user's own farms and crops (the API scopes both to the account)
    Promise.all([farmsAPI.getAll(), cropsAPI.getAll()])
      .then(([f, c]) => setFarms({ loading: false, items: f.data, crops: c.data, error: '' }))
      .catch((err) => setFarms({ loading: false, items: [], crops: [], error: apiError(err, 'Could not load your farms.') }));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      // Show what the server actually stored, so a refresh looks identical
      const res = await usersAPI.updateProfile(profile);
      setProfile(res.data);
      setSavedProfile(res.data);
      setSuccess('Profile updated successfully!');
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      setError(apiError(err, 'Could not save your profile. Please try again.'));
    } finally {
      setSaving(false);
    }
  };

  const dirty = JSON.stringify(profile) !== JSON.stringify(savedProfile);
  const cancel = () => { setProfile(savedProfile); setError(''); setSuccess(''); };

  return (
    <div className="mx-auto max-w-3xl animate-fadeIn space-y-6">
      <PageHeader
        eyebrow="Module 5 · Farmer profile"
        title="Farmer profile"
        description="Your account details and farming background."
      />

      {success && <div className="alert alert-success" role="status"><FiCheckCircle className="mt-0.5 shrink-0" aria-hidden="true" /> {success}</div>}
      {error && <div className="alert alert-error" role="alert"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />{error}</div>}

      <SectionCard icon={FiUser} title="Account" description="Sign-in details (read only)">
        <div className="flex items-center gap-4">
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-green-700 font-display text-2xl text-white" aria-hidden="true">
            {user?.username?.[0]?.toUpperCase()}
          </span>
          <div className="min-w-0">
            <p className="truncate font-display text-xl font-medium text-slate-900">{user?.username}</p>
            <p className="truncate text-sm text-slate-500">{user?.email}</p>
            <span className="badge badge-success mt-1.5 capitalize">{user?.role}</span>
          </div>
        </div>
      </SectionCard>

      <SectionCard icon={FiUser} title="Personal details" description="Used to personalise your farm records">
        {loading ? (
          <div className="space-y-4" aria-busy="true" aria-label="Loading profile">
            <div className="skeleton h-10 w-full" /><div className="skeleton h-10 w-full" /><div className="skeleton h-10 w-full" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="label" htmlFor="full_name">Full name</label>
                <input id="full_name" type="text" value={profile.full_name || ''} onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  placeholder="Enter your full name" className="input" autoComplete="name" />
              </div>
              <div>
                <label className="label" htmlFor="phone">Phone number</label>
                <input id="phone" type="tel" value={profile.phone || ''} onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  placeholder="Enter phone number" className="input" autoComplete="tel" />
              </div>
            </div>
            <div>
              <label className="label" htmlFor="address">Address</label>
              <input id="address" type="text" value={profile.address || ''} onChange={(e) => setProfile({ ...profile, address: e.target.value })}
                placeholder="Enter your address" className="input" autoComplete="street-address" />
            </div>
            <div className="max-w-xs">
              <label className="label" htmlFor="experience_years">Farming experience</label>
              <div className="relative">
                <input id="experience_years" type="number" value={profile.experience_years || 0}
                  onChange={(e) => setProfile({ ...profile, experience_years: parseInt(e.target.value) || 0 })} min="0" className="input pr-14" />
                <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-slate-500" aria-hidden="true">years</span>
              </div>
            </div>
            <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 pt-4">
              <button type="button" onClick={cancel} disabled={!dirty || saving} className="btn btn-secondary">
                <FiRotateCcw aria-hidden="true" /> Cancel
              </button>
              <button type="submit" disabled={saving || !dirty} className="btn btn-primary">
                {saving ? <span className="h-4 w-4 spinner" aria-hidden="true" /> : <FiSave aria-hidden="true" />}
                {saving ? 'Saving...' : 'Save profile'}
              </button>
            </div>
          </form>
        )}
      </SectionCard>

      <SectionCard icon={FiMapPin} title="My farms" description="Farms and crops saved to your account"
        actions={<Link to="/data-acquisition" className="btn btn-secondary btn-sm">Edit farm data</Link>}>
        {farms.loading ? (
          <div className="skeleton h-16 w-full" aria-busy="true" aria-label="Loading farms" />
        ) : farms.error ? (
          <p className="text-sm text-red-700" role="alert">{farms.error}</p>
        ) : farms.items.length === 0 ? (
          <p className="text-sm text-slate-500">No farms yet. Open the dashboard to create your default farm, or add one in Add farm data.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {farms.items.map((f) => {
              const names = farms.crops.filter((c) => c.farm_id === f.id).map((c) => c.name);
              return (
                <li key={f.id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3 first:pt-0 last:pb-0">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-900">{f.name}</p>
                    <p className="truncate text-xs text-slate-500">{f.location || 'No location set'}{f.area ? ` · ${f.area} ${f.area_unit || 'acres'}` : ''}</p>
                  </div>
                  <p className="text-xs text-slate-600">{names.length ? names.join(', ') : 'No crops yet'}</p>
                </li>
              );
            })}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}
