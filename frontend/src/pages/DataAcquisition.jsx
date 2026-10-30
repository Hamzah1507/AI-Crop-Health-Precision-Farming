import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { FiImage, FiSend, FiCloud, FiCheckCircle, FiAlertTriangle, FiMapPin, FiDroplet } from 'react-icons/fi';
import { farmsAPI, cropsAPI, weatherAPI, soilAPI, detectionAPI } from '../services/api';
import { apiError } from '../utils/apiError';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import UploadDropzone from '../components/UploadDropzone';
import UnitField from '../components/UnitField';
import WeatherCard from '../components/WeatherCard';
import DetectionResult from '../components/DetectionResult';

const CROP_OPTIONS = ['Rice', 'Wheat', 'Corn', 'Tomato', 'Potato', 'Soybean', 'Cotton', 'Sugarcane', 'Groundnut', 'Millet', 'Apple', 'Grape'];

const SOIL_FIELDS = [
  { label: 'Soil pH', key: 'ph', unit: 'pH', placeholder: '6.5', step: '0.1', min: 0, max: 14, hint: 'Ideal 6.0 to 7.5' },
  { label: 'Nitrogen (N)', key: 'nitrogen', unit: 'kg/ha', placeholder: '35', step: '1', min: 0, hint: 'Ideal 20 to 50' },
  { label: 'Phosphorus (P)', key: 'phosphorus', unit: 'kg/ha', placeholder: '25', step: '1', min: 0, hint: 'Ideal 15 to 40' },
  { label: 'Potassium (K)', key: 'potassium', unit: 'kg/ha', placeholder: '30', step: '1', min: 0, hint: 'Ideal 20 to 45' },
  { label: 'Moisture', key: 'moisture', unit: '%', placeholder: '50', step: '1', min: 0, max: 100, hint: 'Ideal 30 to 70' },
];

const EMPTY_SOIL = { ph: '', nitrogen: '', phosphorus: '', potassium: '', moisture: '' };

// '' -> null (not provided); anything else -> number. A real 0 is kept.
const toNumber = (v) => (v === '' || v === null || v === undefined ? null : Number(v));

export default function DataAcquisition() {
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [cropName, setCropName] = useState('');
  const [farm, setFarm] = useState({ name: '', location: '', area: '' });
  const [soil, setSoil] = useState(EMPTY_SOIL);
  const [weather, setWeather] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherError, setWeatherError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [saved, setSaved] = useState([]);
  const [detection, setDetection] = useState(null);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const savedSoilKey = useRef(null);   // stops a retry from saving the same soil record twice
  const [farms, setFarms] = useState([]);
  const [farmChoice, setFarmChoice] = useState('new');   // id of an existing farm, or 'new'
  const [soilNote, setSoilNote] = useState('');

  const farmToForm = (f) => ({ name: f.name, location: f.location || '', area: f.area == null ? '' : String(f.area) });

  // Make sure the user has a farm (the server creates the default Ahmedabad farm only if there is none),
  // then start on their newest farm so the location, weather and crop context are already filled in.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try { await farmsAPI.ensureDefault(); } catch { /* the form still works without a default farm */ }
      try {
        const list = (await farmsAPI.getAll()).data;
        if (cancelled) return;
        setFarms(list);
        const newest = [...list].sort((a, b) => b.id - a.id)[0];
        if (newest) { setFarmChoice(String(newest.id)); setFarm(farmToForm(newest)); }
      } catch (err) {
        if (!cancelled) setError(apiError(err, 'Could not load your farms.'));
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const chooseFarm = (value) => {
    setFarmChoice(value);
    setFieldErrors({});
    const picked = farms.find((f) => String(f.id) === value);
    setFarm(picked ? farmToForm(picked) : { name: '', location: '', area: '' });
    setWeather(null);
    setWeatherError('');
  };

  const useLatestSoil = async () => {
    setSoilNote('');
    try {
      const { data } = await soilAPI.getLatest();
      if (!data.record) { setSoilNote('You have no saved soil measurements yet.'); return; }
      const r = data.record;
      setSoil(Object.fromEntries(SOIL_FIELDS.map((f) => [f.key, r[f.key] == null ? '' : String(r[f.key])])));
      setSoilNote(`Filled from your latest saved record (#${r.id}). Submitting saves a new record.`);
    } catch (err) {
      setSoilNote(apiError(err, 'Could not load your latest soil record.'));
    }
  };

  useEffect(() => () => { if (imagePreview) URL.revokeObjectURL(imagePreview); }, [imagePreview]);

  const chooseImage = (file) => {
    setImage(file);
    setImagePreview(URL.createObjectURL(file));
    setError('');
  };
  const removeImage = () => { setImage(null); setImagePreview(null); };

  const fetchWeather = async () => {
    if (!farm.location.trim()) { setWeatherError('Enter the farm location first.'); return; }
    setWeatherLoading(true);
    setWeatherError('');
    try {
      const res = await weatherAPI.fetch({ location: farm.location.trim() });
      setWeather(res.data);
    } catch (err) {
      setWeather(null);
      setWeatherError(apiError(err, 'Failed to fetch weather. Please try again.'));
    } finally {
      setWeatherLoading(false);
    }
  };

  // Returns { form, fields }; both empty when the form can be submitted.
  const validate = () => {
    const fields = {};
    const hasSoil = Object.values(soil).some((v) => v !== '');
    let form = '';
    if (!farm.name.trim() && !cropName && !hasSoil && !image) {
      form = 'Enter farm details, soil measurements or a leaf image before submitting.';
    }
    if (cropName && !farm.name.trim()) fields.farmName = 'Enter a farm name so the selected crop can be saved to a farm.';
    if (farm.area !== '' && !(Number(farm.area) > 0)) fields.area = 'Farm area must be greater than 0.';
    for (const f of SOIL_FIELDS) {
      if (soil[f.key] === '') continue;
      const n = Number(soil[f.key]);
      if (Number.isNaN(n)) fields[f.key] = `${f.label} must be a number.`;
      else if (n < f.min || (f.max !== undefined && n > f.max)) fields[f.key] = `${f.label} must be between ${f.min} and ${f.max ?? 'a positive value'}.`;
    }
    return { form, fields };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const { form, fields } = validate();
    setFieldErrors(fields);
    const first = form || Object.values(fields)[0];
    if (first) { setError(first); setSaved([]); return; }

    setSubmitting(true);
    setError('');
    setSaved([]);
    setDetection(null);
    const done = [];
    try {
      let farmRecord = null;
      let cropRecord = null;

      // Farm: update the existing farm with this name, otherwise create it
      const farmName = farm.name.trim();
      if (farmName) {
        const details = {};
        if (farm.location.trim()) details.location = farm.location.trim();
        if (farm.area !== '') details.area = Number(farm.area);
        const current = (await farmsAPI.getAll()).data;
        // A farm picked in the selector is updated by id; otherwise a matching name is reused instead of duplicated
        const existing = current.find((f) => String(f.id) === farmChoice) || current.find((f) => f.name.toLowerCase() === farmName.toLowerCase());
        if (existing) {
          farmRecord = (await farmsAPI.update(existing.id, { name: farmName, ...details })).data;
          done.push(`Existing farm "${farmRecord.name}" updated (no duplicate created)`);
        } else {
          farmRecord = (await farmsAPI.create({ name: farmName, ...details })).data;
          done.push(`Farm "${farmRecord.name}" created`);
        }
        setFarms((await farmsAPI.getAll()).data);
        setFarmChoice(String(farmRecord.id));
      }

      // Crop on that farm (the server returns the existing crop if it is already there)
      if (cropName && farmRecord) {
        cropRecord = (await cropsAPI.create({ farm_id: farmRecord.id, name: cropName })).data;
        done.push(`Crop "${cropRecord.name}" saved to ${farmRecord.name}`);
      }

      // Soil measurements, linked to the farm and crop when present
      if (Object.values(soil).some((v) => v !== '')) {
        const soilKey = JSON.stringify([soil, farmRecord?.id ?? null, cropRecord?.id ?? null]);
        if (savedSoilKey.current === soilKey) {
          done.push('Soil measurements were already saved by the previous attempt');
        } else {
          await soilAPI.createRecord({
            farm_id: farmRecord?.id ?? null,
            crop_id: cropRecord?.id ?? null,
            ph: toNumber(soil.ph),
            nitrogen: toNumber(soil.nitrogen),
            phosphorus: toNumber(soil.phosphorus),
            potassium: toNumber(soil.potassium),
            moisture: toNumber(soil.moisture),
          });
          savedSoilKey.current = soilKey;
          done.push('Soil measurements saved');
        }
      }

      // Leaf image: run it through disease detection and keep the prediction
      if (image) {
        const formData = new FormData();
        formData.append('file', image);
        if (cropName) formData.append('crop_name', cropName);
        if (cropRecord) formData.append('crop_id', cropRecord.id);
        const res = await detectionAPI.predict(formData);
        setDetection({ result: res.data, preview: imagePreview });
        done.push('Leaf image uploaded and analysed');
      }

      // Everything succeeded: soil values are saved, so clear them. The image, farm and crop stay.
      setSoil(EMPTY_SOIL);
      savedSoilKey.current = null;
    } catch (err) {
      // On failure nothing the user typed or selected is cleared, so they can fix the problem and retry.
      setError(`${apiError(err, 'Submission failed. Please try again.')}${done.length ? ' (steps completed before the error are listed below)' : ''}`);
    } finally {
      setSaved(done);
      setSubmitting(false);
    }
  };

  const setSoilValue = (key) => (value) => setSoil((s) => ({ ...s, [key]: value }));

  return (
    <div className="animate-fadeIn space-y-6">
      <PageHeader
        eyebrow="Module 1 · Data acquisition"
        title="Add farm data"
        description="Record farm details, soil measurements and a leaf image, and check the weather for your location."
      />

      {error && <div className="alert alert-error" role="alert"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" /> {error}</div>}

      {saved.length > 0 && (
        <div className="alert alert-success flex-col !items-start" role="status">
          <p className="flex items-center gap-2 font-medium"><FiCheckCircle aria-hidden="true" /> {error ? 'Partially saved' : 'Saved'}</p>
          <ul className="ml-6 list-disc space-y-0.5 text-sm">
            {saved.map((s) => <li key={s}>{s}</li>)}
          </ul>
          {!error && (
            <p className="mt-1 text-xs">
              Next: <Link to="/soil-analysis" className="font-medium underline">analyze your soil</Link>,{' '}
              <Link to="/disease-detection" className="font-medium underline">run disease detection</Link> or{' '}
              <Link to="/prediction-history" className="font-medium underline">view prediction history</Link>.
            </p>
          )}
        </div>
      )}

      {detection && (
        <SectionCard icon={FiImage} title="Leaf image result" description="Saved to your prediction history">
          <DetectionResult result={detection.result} previewUrl={detection.preview} fallbackCrop={cropName} />
        </SectionCard>
      )}

      <form onSubmit={handleSubmit} className="space-y-6" noValidate>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5 items-start">
          {/* Crop & Farm */}
          <SectionCard icon={FiMapPin} title="Farm & crop" description="Where and what you grow" className="lg:col-span-3">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="label" htmlFor="farm-select">Farm</label>
                <select id="farm-select" value={farmChoice} onChange={(e) => chooseFarm(e.target.value)} className="input" disabled={submitting}>
                  {farms.map((f) => <option key={f.id} value={f.id}>{f.name}{f.location ? ` · ${f.location}` : ''}</option>)}
                  <option value="new">New farm…</option>
                </select>
                <p className="hint">Choose a farm to update it, or pick “New farm…” to add another.</p>
              </div>
              <div>
                <label className="label" htmlFor="farmName">Farm name</label>
                <input id="farmName" type="text" value={farm.name} onChange={(e) => setFarm({ ...farm, name: e.target.value })}
                  placeholder="e.g., Green Valley Farm" className="input"
                  aria-invalid={fieldErrors.farmName ? true : undefined} aria-describedby={fieldErrors.farmName ? 'farmName-error' : undefined} />
                {fieldErrors.farmName && <p id="farmName-error" className="mt-1 text-xs text-red-600">{fieldErrors.farmName}</p>}
              </div>
              <div>
                <label className="label" htmlFor="crop">Crop</label>
                <select id="crop" value={cropName} onChange={(e) => setCropName(e.target.value)} className="input">
                  <option value="">Select a crop</option>
                  {CROP_OPTIONS.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="location">Location</label>
                <input id="location" type="text" value={farm.location} onChange={(e) => setFarm({ ...farm, location: e.target.value })}
                  placeholder="e.g., Pune, India" className="input" />
                <p className="hint">Used for weather. A city name works best.</p>
              </div>
              <UnitField id="area" label="Farm area" unit="acres" value={farm.area} onChange={(v) => setFarm({ ...farm, area: v })}
                placeholder="e.g., 10" step="0.1" min="0" error={fieldErrors.area} />
            </div>
            <p className="mt-4 text-xs text-slate-500">Submitting a farm name that already exists updates that farm instead of creating a copy.</p>
          </SectionCard>

          {/* Image Upload */}
          <SectionCard icon={FiImage} title="Leaf image" description="Optional. Runs the disease and pest check." className="lg:col-span-2">
            <UploadDropzone id="leaf-image" file={image} previewUrl={imagePreview} onFile={chooseImage}
              onInvalid={setError} onRemove={removeImage} disabled={submitting} />
          </SectionCard>
        </div>

        {/* Soil Parameters */}
        <SectionCard icon={FiDroplet} title="Soil measurements" description="Optional. Leave blank any value you don't have."
          actions={<button type="button" onClick={useLatestSoil} disabled={submitting} className="btn btn-secondary btn-sm">Use latest saved values</button>}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {SOIL_FIELDS.map((f) => (
              <UnitField key={f.key} id={`soil-${f.key}`} label={f.label} unit={f.unit} hint={f.hint}
                value={soil[f.key]} onChange={setSoilValue(f.key)} placeholder={f.placeholder}
                step={f.step} min={f.min} max={f.max} error={fieldErrors[f.key]} />
            ))}
          </div>
          {soilNote && <p className="mt-3 text-xs text-slate-500" role="status">{soilNote}</p>}
        </SectionCard>

        {/* Weather */}
        <SectionCard icon={FiCloud} title="Weather" description="Current conditions and a 5-day forecast for your location"
          actions={
            <button type="button" onClick={fetchWeather} disabled={weatherLoading} className="btn btn-secondary btn-sm">
              {weatherLoading ? <span className="h-3.5 w-3.5 spinner" aria-hidden="true" /> : <FiCloud aria-hidden="true" />}
              {weatherLoading ? 'Fetching...' : 'Fetch weather'}
            </button>
          }>
          {weatherError && <div className="alert alert-error mb-4" role="alert"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" /> {weatherError}</div>}
          {weather ? (
            <WeatherCard weather={weather} />
          ) : (
            !weatherError && <p className="text-sm text-slate-500">Enter a location above and choose "Fetch weather" to see current conditions and a 5-day forecast.</p>
          )}
        </SectionCard>

        <div className="flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-end">
          <p className="text-xs text-slate-500 sm:mr-auto">Farm, crop, soil values and the leaf image are saved together.</p>
          <button type="submit" disabled={submitting} className="btn btn-primary px-6">
            {submitting ? <span className="h-4 w-4 spinner" aria-hidden="true" /> : <FiSend aria-hidden="true" />}
            {submitting ? 'Saving...' : 'Submit data'}
          </button>
        </div>
      </form>
    </div>
  );
}
