import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { predictionsAPI, farmsAPI, cropsAPI, soilAPI, recommendationsAPI, yieldAPI, weatherAPI, detectionAPI, analyticsAPI } from '../services/api';
import { apiError } from '../utils/apiError';
import { exportFarmReportPDF } from '../utils/pdfGenerator';
import {
  WeatherPanel, StatCard, SoilStrip, FarmMap, IrrigationCard, PhCard, FertilizerCard, YieldPanel, ScansPanel,
} from '../components/dashboard/panels';
import { FiCamera, FiGrid, FiUpload, FiSearch, FiAlertTriangle, FiDownload } from 'react-icons/fi';

// Layout follows the reference dashboard (greeting + account live in the layout header):
//   row 1: [weather, two compact cards, soil strip] | [large aerial farm panel with overlay]
//   row 2: [irrigation + pH, fertilizer]            | [yield panel] | [recent scans]
// Every value comes from the API; panels without data render an empty state.
export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [failedCount, setFailedCount] = useState(0);
  const [scans, setScans] = useState({ total: 0, list: [] });
  const [farms, setFarms] = useState([]);
  const [crops, setCrops] = useState([]);
  const [soil, setSoil] = useState(null);
  const [recommendationCount, setRecommendationCount] = useState(0);
  const [yields, setYields] = useState([]);
  const [detector, setDetector] = useState(null);

  const [farmId, setFarmId] = useState(null);
  const [defaults, setDefaults] = useState({ farmName: '', location: '' });   // from POST /api/farms/default
  const [weatherOverride, setWeatherOverride] = useState('');   // a place the user looked up manually
  const [weatherState, setWeatherState] = useState({ key: '', data: null, error: '' });   // result for the place named in `key`

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // First make sure the user has a farm (creates the default Ahmedabad farm only if they have none).
      // The call is idempotent and race-safe on the server, so StrictMode's double effect cannot duplicate it.
      let ensureFailed = 0;
      try {
        const { data } = await farmsAPI.ensureDefault();
        if (!cancelled) setDefaults({ farmName: data.default_farm_name, location: data.default_location });
      } catch {
        ensureFailed = 1;
      }
      if (cancelled) return;

      const results = await Promise.allSettled([
        predictionsAPI.getAll(0, 5),
        farmsAPI.getAll(),
        cropsAPI.getAll(),
        soilAPI.getLatest(),
        recommendationsAPI.getAll(),
        yieldAPI.getHistory(),
        detectionAPI.getStatus(),
      ]);
      if (cancelled) return;
      const ok = (r) => (r.status === 'fulfilled' ? r.value.data : null);
      const [pred, farm, crop, soilRes, rec, yld, det] = results;
      setDetector(ok(det));
      setScans({ total: ok(pred)?.total ?? 0, list: ok(pred)?.predictions ?? [] });
      const farmList = ok(farm) ?? [];
      setFarms(farmList);
      // Show the user's most recently added farm that has a location (their own choice wins over the default)
      const newestFirst = [...farmList].sort((a, b) => b.id - a.id);
      setFarmId((newestFirst.find((f) => f.location) ?? newestFirst[0])?.id ?? null);
      setCrops(ok(crop) ?? []);
      setSoil(ok(soilRes));
      setRecommendationCount((ok(rec) ?? []).length);
      setYields(ok(yld) ?? []);
      setFailedCount(ensureFailed + results.filter((r) => r.status === 'rejected').length);
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const selectedFarm = farms.find((f) => f.id === farmId) || null;
  // Weather: a place the user looked up, else the selected farm's own location, else the default (Ahmedabad)
  const weatherLocation = weatherOverride || selectedFarm?.location || defaults.location;
  const usingDefaultLocation = !weatherOverride && !selectedFarm?.location && !!defaults.location;

  useEffect(() => {
    if (!weatherLocation) return undefined;
    let cancelled = false;
    weatherAPI.current(weatherLocation)
      .then((res) => { if (!cancelled) setWeatherState({ key: weatherLocation, data: res.data, error: '' }); })
      .catch((err) => {
        if (!cancelled) setWeatherState({ key: weatherLocation, data: null, error: apiError(err, 'Could not load weather. Please try again.') });
      });
    return () => { cancelled = true; };
  }, [weatherLocation]);

  // Loading is derived: a place is loading until a result for exactly that place has arrived
  const weatherReady = weatherState.key === weatherLocation;
  const weather = {
    data: weatherReady ? weatherState.data : null,
    error: weatherReady ? weatherState.error : '',
    loading: !!weatherLocation && !weatherReady,
  };

  const selectFarm = (id) => { setFarmId(id); setWeatherOverride(''); };

  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');

  const handleExportReport = async () => {
    if (exporting) return;
    setExporting(true);
    setExportError('');
    try {
      const res = await analyticsAPI.getReportData(farmId || undefined);
      exportFarmReportPDF(res.data);
    } catch (err) {
      setExportError(apiError(err, 'Failed to generate farm report. Please try again.'));
    } finally {
      setExporting(false);
    }
  };

  const latestScan = scans.list[0];
  const latestScanName = latestScan ? (latestScan.disease_name || latestScan.pest_name) : null;

  return (
    <div className="animate-fadeIn space-y-2.5">
      {failedCount > 0 && (
        <div className="alert alert-warning" role="alert">
          <FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>Some dashboard data could not be loaded ({failedCount} of 8 requests failed), so those panels may look empty. Check that the backend is running and refresh the page.</span>
        </div>
      )}

      {exportError && (
        <div className="alert alert-error" role="alert">
          <FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>{exportError}</span>
        </div>
      )}

      {/* Header actions: responsive button bar */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2 md:hidden flex-1">
          <Link to="/data-acquisition" className="btn btn-secondary flex-1"><FiUpload aria-hidden="true" /> Add data</Link>
          <Link to="/disease-detection" className="btn btn-primary flex-1"><FiSearch aria-hidden="true" /> Detect disease</Link>
        </div>
        <div className="ml-auto">
          <button
            type="button"
            onClick={handleExportReport}
            disabled={exporting || loading}
            className="btn btn-secondary"
            title="Download full farm performance and diagnostic report in PDF format"
            aria-label="Export Farm Report as PDF"
          >
            <FiDownload className={exporting ? 'animate-bounce' : ''} aria-hidden="true" />
            <span>{exporting ? 'Generating PDF…' : 'Export Farm Report (PDF)'}</span>
          </button>
        </div>
      </div>

      {/* Row 1: Weather, Quick Stats & Aerial Farm Map */}
      <div className="grid gap-2.5 md:grid-cols-2 xl:grid-cols-[1.45fr_2fr]">
        {/* Row 1, left: weather, compact cards, soil strip */}
        <div className="flex flex-col gap-2.5 md:col-span-2 xl:col-span-1">
          <WeatherPanel location={weatherLocation} usingDefault={usingDefaultLocation} weather={weather.data} loading={loading || weather.loading}
            error={weather.error} onLookup={setWeatherOverride} />
          <div className="grid grid-cols-1 gap-2.5 min-[420px]:grid-cols-2">
            <StatCard icon={FiCamera} title="Leaf Scans" loading={loading} value={scans.total} unit={scans.total === 1 ? 'scan' : 'scans'}
              hint={latestScanName ? `Latest: ${latestScanName}${latestScan.is_demo === 'true' ? ' (simulated)' : ''}` : 'Upload a leaf image to start'} />
            <StatCard icon={FiGrid} title="Farms & Crops" loading={loading} value={farms.length} unit={farms.length === 1 ? 'farm' : 'farms'}
              hint={`${crops.length} crop${crops.length === 1 ? '' : 's'} tracked`} />
          </div>
          <SoilStrip loading={loading} soil={soil} />
        </div>

        {/* Row 1, right: aerial farm panel with real farm, crops and soil overlay */}
        <div className="min-h-[29rem] md:col-span-2 xl:col-span-1 xl:min-h-0">
          <FarmMap loading={loading} farms={farms} farmId={farmId} onSelectFarm={selectFarm} crops={crops} soil={soil} defaultFarmName={defaults.farmName} />
        </div>
      </div>

      {/* Row 2: Precision Ag Intelligence, Yield Estimates & Leaf Scans */}
      <div className="grid gap-2.5 md:grid-cols-2 xl:grid-cols-3">
        {/* Row 2, Column 1: Irrigation + pH + Fertilizer stacked vertically */}
        <div className="grid grid-cols-1 gap-2.5 md:col-span-2 md:grid-cols-3 xl:col-span-1 xl:flex xl:flex-col h-full">
          <IrrigationCard loading={loading} soil={soil} className="flex-1" />
          <PhCard loading={loading} soil={soil} className="flex-1" />
          <FertilizerCard loading={loading} soil={soil} recommendationCount={recommendationCount} className="flex-1" />
        </div>

        {/* Row 2, Column 2: Yield estimates */}
        <YieldPanel loading={loading} yields={yields} className="h-full" />

        {/* Row 2, Column 3: Recent leaf scans */}
        <ScansPanel loading={loading} scans={scans.list} detector={detector} className="h-full" />
      </div>
    </div>
  );
}
