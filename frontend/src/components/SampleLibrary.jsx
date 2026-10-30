import { useEffect, useMemo, useRef, useState } from 'react';
import { FiX, FiInfo, FiAlertTriangle, FiCheck } from 'react-icons/fi';
import { API_BASE_URL } from '../services/api';

const CONDITIONS = [
  { value: '', label: 'All' },
  { value: 'healthy', label: 'Healthy leaves' },
  { value: 'disease', label: 'Diseased leaves' },
  { value: 'pest', label: 'Pests & pest damage' },
  { value: 'photo', label: 'Crop photos' },
];
const CONDITION_LABEL = { healthy: 'Healthy', disease: 'Disease', pest: 'Pest', photo: 'Crop photo' };
const titleCase = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);

// Modal picker for the local sample image library. Labels shown here are the SOURCE's labels, not predictions.
export default function SampleLibrary({ items, selectedId, onSelect, onClose }) {
  const [crop, setCrop] = useState('');
  const [condition, setCondition] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');
  const closeRef = useRef(null);

  // Focus moves into the dialog, Escape closes it, and focus returns to whatever opened it
  useEffect(() => {
    const opener = document.activeElement;
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('keydown', onKey); opener?.focus?.(); };
  }, [onClose]);

  const crops = useMemo(() => [...new Set(items.map((i) => i.crop))].sort(), [items]);
  const shown = items.filter((i) => (!crop || i.crop === crop) && (!condition || i.condition === condition));

  const choose = async (item) => {
    setBusyId(item.id);
    setError('');
    try {
      await onSelect(item);
      onClose();
    } catch (e) {
      setError(e.message || 'Could not load that sample image.');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/50 p-3 sm:p-6" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div role="dialog" aria-modal="true" aria-labelledby="sample-title" className="flex max-h-[90vh] w-full max-w-5xl flex-col rounded-card border border-slate-200 bg-white shadow-lift">
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div>
            <h2 id="sample-title" className="font-display text-xl font-medium text-slate-900">Sample image library</h2>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-500">
              Real, openly licensed crop photographs for testing. The label under each image is the <strong>source's own label</strong>
              (dataset or photographer), not a prediction by CropHealth AI.
            </p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Close sample library" className="btn btn-ghost btn-sm !px-2"><FiX aria-hidden="true" /></button>
        </header>

        <div className="flex flex-wrap items-end gap-3 border-b border-slate-100 px-5 py-3">
          <div>
            <label htmlFor="sample-crop" className="label">Crop</label>
            <select id="sample-crop" value={crop} onChange={(e) => setCrop(e.target.value)} className="input !min-h-[2.25rem] !w-40 !py-1.5">
              <option value="">All crops</option>
              {crops.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}
            </select>
          </div>
          <div role="group" aria-label="Filter by condition" className="flex flex-wrap gap-2">
            {CONDITIONS.map((c) => (
              <button key={c.value || 'all'} type="button" onClick={() => setCondition(c.value)} aria-pressed={condition === c.value}
                className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${condition === c.value ? 'border-green-700 bg-green-700 text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>
                {c.label}
              </button>
            ))}
          </div>
          <p className="ml-auto text-xs text-slate-500" aria-live="polite">{shown.length} of {items.length} images</p>
        </div>

        {error && <div className="alert alert-error mx-5 mt-3" role="alert"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />{error}</div>}

        <div className="overflow-y-auto p-5">
          {shown.length === 0 ? (
            <p className="py-10 text-center text-sm text-slate-500">No sample images match these filters.</p>
          ) : (
            <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {shown.map((item) => (
                <li key={item.id}>
                  <button type="button" onClick={() => choose(item)} disabled={busyId !== null} aria-pressed={selectedId === item.id}
                    aria-label={`Use sample: ${titleCase(item.crop)}, ${item.label}`}
                    className={`group w-full overflow-hidden rounded-xl border bg-white text-left transition-shadow hover:shadow-lift disabled:opacity-60 ${selectedId === item.id ? 'border-green-600 ring-2 ring-green-600/40' : 'border-slate-200'}`}>
                    <span className="relative block aspect-square bg-slate-100">
                      <img src={`${API_BASE_URL}${item.url}`} alt={`${titleCase(item.crop)}: ${item.label}`} loading="lazy" crossOrigin="anonymous" className="h-full w-full object-cover" />
                      {selectedId === item.id && <span className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-green-700 text-white" aria-hidden="true"><FiCheck /></span>}
                      {busyId === item.id && <span className="absolute inset-0 flex items-center justify-center bg-white/70"><span className="h-6 w-6 spinner text-green-700" aria-hidden="true" /></span>}
                    </span>
                    <span className="block px-2.5 py-2">
                      <span className="block truncate text-xs font-medium text-slate-900">{titleCase(item.crop)} · {item.label}</span>
                      <span className="mt-0.5 flex items-center justify-between gap-1 text-[11px] text-slate-500">
                        <span>{CONDITION_LABEL[item.condition] || item.condition}</span>
                        <span className="truncate">{item.license}</span>
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <footer className="flex items-start gap-2 border-t border-slate-200 px-5 py-3 text-[11px] leading-relaxed text-slate-500">
          <FiInfo className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>Sources: PlantVillage (CC BY-SA 3.0) and Wikimedia Commons (per-image licences). Full attribution is in <code>backend/uploads/sample_images/README.md</code>.
            The disease detector is still simulated, so its answer for these images is not a real diagnosis.</span>
        </footer>
      </div>
    </div>
  );
}
