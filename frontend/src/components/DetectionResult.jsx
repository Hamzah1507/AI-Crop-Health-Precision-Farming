import { useState, useEffect } from 'react';
import { predictionsAPI } from '../services/api';
import { uploadUrl } from '../utils/uploadUrl';
import { FiAlertTriangle, FiCheckCircle, FiClock } from 'react-icons/fi';

// Renders one prediction returned by POST /api/detection/predict.
// Results with is_demo === 'true' are demonstration advisories (e.g. unsupported crop
// or fallback detector): they are labelled with a Simulated badge and carry no confidence score.
export default function DetectionResult({ result, previewUrl, fallbackCrop, isModelLoaded = true }) {
  const [treatments, setTreatments] = useState([]);
  const [naturalSize, setNaturalSize] = useState(null);
  const isDemo = result?.is_demo === 'true';
  const isUncertain = result?.prediction_type === 'uncertain' || result?.status === 'uncertain' || (result?.disease_name || '').toLowerCase().includes('unable to identify');
  const healthy = !isUncertain && result?.disease_name === 'Healthy Plant';
  const hasConfidence = result?.confidence !== null && result?.confidence !== undefined;
  const box = result?.bbox_data?.boxes?.[0];
  const displayImage = previewUrl || (result?.image_path ? uploadUrl(result.image_path) : null);
  const currentCrop = result?.crop_name || fallbackCrop;

  const demoMessage = !isModelLoaded
    ? 'Demonstration result — No trained AI model is currently loaded; using demonstration fallback.'
    : `Demonstration result — ${currentCrop || 'This crop'} is not currently supported by the trained AI model.`;

  useEffect(() => {
    if (!result?.id || isUncertain) return undefined;
    let cancelled = false;
    predictionsAPI.getRecommendations(result.id)
      .then((res) => { if (!cancelled) setTreatments(res.data || []); })
      .catch(() => { if (!cancelled) setTreatments([]); });
    return () => { cancelled = true; };
  }, [result?.id, isUncertain]);

  if (!result) return null;

  return (
    <div className="space-y-4">
      <div className={`flex items-start gap-3 rounded-xl border p-4 ${isUncertain
          ? 'border-amber-200 bg-amber-50'
          : healthy
            ? 'border-green-200 bg-green-50'
            : 'border-red-200 bg-red-50'
        }`}>
        {isUncertain ? (
          <FiAlertTriangle className="mt-0.5 shrink-0 text-2xl text-amber-600" aria-hidden="true" />
        ) : healthy ? (
          <FiCheckCircle className="mt-0.5 shrink-0 text-2xl text-green-600" aria-hidden="true" />
        ) : (
          <FiAlertTriangle className="mt-0.5 shrink-0 text-2xl text-red-600" aria-hidden="true" />
        )}
        <div className="min-w-0 flex-1">
          <p className="font-display text-xl font-medium leading-tight text-slate-900 break-words">{result.disease_name || result.pest_name || 'No result'}</p>
          <p className="mt-0.5 text-xs capitalize text-slate-500">Type: {result.prediction_type}</p>
          {isDemo && (
            <p className="mt-1 text-xs text-slate-600 font-normal">
              {demoMessage}
            </p>
          )}
        </div>
        {isDemo && <span className="badge badge-neutral shrink-0">Simulated</span>}
        {isUncertain && <span className="badge badge-warning shrink-0">Uncertain</span>}
      </div>

      {isUncertain && (
        <div className="alert alert-warning" role="alert">
          <FiAlertTriangle className="mt-0.5 shrink-0 text-amber-700" aria-hidden="true" />
          <div className="space-y-1 text-xs leading-relaxed text-amber-900">
            <p className="font-medium">
              Unable to identify reliably. The crop species or disease could not be determined with sufficient confidence. Upload a clear photograph of the affected leaf and select the correct crop if known.
            </p>
            <p className="text-amber-800">
              No disease-specific chemical treatments are recommended for unverified plant species. Consult a certified local agronomist before applying remedies.
            </p>
          </div>
        </div>
      )}

      <dl className="grid grid-cols-2 gap-3">
        <div className="panel p-3">
          <dt className="text-xs text-slate-500">Confidence score</dt>
          <dd>
            {hasConfidence ? (
              <>
                <span className="mt-1 block font-display text-2xl font-medium text-slate-900 tnum">{result.confidence}%</span>
                <span className="mt-1 block h-1.5 w-full rounded-full bg-slate-200">
                  <span className="block h-1.5 rounded-full bg-green-600" style={{ width: `${Math.min(100, Math.max(0, result.confidence))}%` }} />
                </span>
              </>
            ) : (
              <span className="mt-1 block text-sm font-medium text-slate-500">Not available{isDemo ? ' (simulated)' : ''}</span>
            )}
          </dd>
        </div>
        <div className="panel p-3">
          <dt className="text-xs text-slate-500">Crop</dt>
          <dd className="mt-1 text-sm font-semibold text-slate-800">{result.crop_name || fallbackCrop || 'Not specified'}</dd>
        </div>
        <div className="panel p-3">
          <dt className="text-xs text-slate-500">Date</dt>
          <dd className="mt-1 flex items-center gap-1 text-sm font-semibold text-slate-800">
            <FiClock className="text-xs text-slate-400" aria-hidden="true" />
            {result.created_at ? new Date(result.created_at).toLocaleString() : '—'}
          </dd>
        </div>
        <div className="panel p-3">
          <dt className="text-xs text-slate-500">Status</dt>
          <dd className={`mt-1 text-sm font-semibold capitalize ${result.status === 'failed'
              ? 'text-red-600'
              : isUncertain
                ? 'text-amber-700'
                : 'text-green-700'
            }`}>
            {result.status}
          </dd>
        </div>
      </dl>

      {treatments.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-medium text-slate-800">Suggested treatment</p>
          {treatments.map((t) => (
            <div key={t.id} className="rounded-xl border border-slate-200 p-3">
              <p className="text-xs font-medium text-slate-700">{t.title}</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">{t.description}</p>
            </div>
          ))}
          {isDemo && <p className="mt-1.5 text-[11px] text-slate-500">General guidance for the label shown above. Because that label is simulated, do not act on it.</p>}
        </div>
      )}

      {/* Affected-region box: only for real model output; supports pixel and normalized coordinates */}
      {!isDemo && box && displayImage && (
        <div>
          <p className="mb-2 text-sm font-medium text-slate-800">Affected region</p>
          <div className="relative inline-block">
            <img src={displayImage} alt="Detection" className="block max-h-48 rounded-lg"
              onLoad={(e) => setNaturalSize({ w: e.target.naturalWidth, h: e.target.naturalHeight })} />
            {naturalSize && (
              <div className="absolute rounded border-2 border-red-500" style={{
                left: `${box[2] <= 1.0 ? box[0] * 100 : (box[0] / naturalSize.w) * 100}%`,
                top: `${box[3] <= 1.0 ? box[1] * 100 : (box[1] / naturalSize.h) * 100}%`,
                width: `${box[2] <= 1.0 ? (box[2] - box[0]) * 100 : ((box[2] - box[0]) / naturalSize.w) * 100}%`,
                height: `${box[3] <= 1.0 ? (box[3] - box[1]) * 100 : ((box[3] - box[1]) / naturalSize.h) * 100}%`,
              }}>
                <span className="absolute -top-5 left-0 whitespace-nowrap rounded bg-red-500 px-1.5 py-0.5 text-[10px] text-white">
                  {result.bbox_data?.labels?.[0] || result.disease_name || result.pest_name || 'Detected'}
                  {result.bbox_data?.scores?.[0] != null ? ` (${result.bbox_data.scores[0]}%)` : ''}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
