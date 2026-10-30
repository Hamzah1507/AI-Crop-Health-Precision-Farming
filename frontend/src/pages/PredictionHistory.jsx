import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { predictionsAPI, usersAPI } from '../services/api';
import { uploadUrl } from '../utils/uploadUrl';
import { apiError } from '../utils/apiError';
import { exportPredictionHistoryPDF } from '../utils/pdfGenerator';
import PageHeader from '../components/PageHeader';
import EmptyState from '../components/EmptyState';
import { FiClock, FiTrash2, FiAlertTriangle, FiCheckCircle, FiSearch, FiImage, FiInfo, FiDownload } from 'react-icons/fi';

export default function PredictionHistory() {
  const [predictions, setPredictions] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const { hash } = useLocation();
  const targetId = /^#prediction-(\d+)$/.exec(hash)?.[1];   // set when arriving from a recommendation's "View scan" link

  useEffect(() => {
    predictionsAPI.getAll(0, 100)
      .then((res) => {
        setPredictions(res.data.predictions || []);
        setTotal(res.data.total);
      })
      .catch((err) => setError(apiError(err, 'Could not load prediction history.')))
      .finally(() => setLoading(false));
  }, []);

  // Bring the linked scan into view once the table has rendered
  useEffect(() => {
    if (!loading && targetId) document.getElementById(`prediction-${targetId}`)?.scrollIntoView({ block: 'center' });
  }, [loading, targetId]);

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this prediction? This cannot be undone.')) return;
    setError('');
    setDeletingId(id);
    try {
      await predictionsAPI.delete(id);
      setPredictions((list) => list.filter((p) => p.id !== id));
      setTotal((t) => t - 1);
    } catch (err) {
      setError(apiError(err, 'Could not delete the prediction.'));
    } finally {
      setDeletingId(null);
    }
  };

  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');

  const handleExportHistoryPDF = async () => {
    if (exporting || predictions.length === 0) return;
    setExporting(true);
    setExportError('');
    try {
      const { data: userProfile } = await usersAPI.getProfile().catch(() => ({ data: {} }));
      exportPredictionHistoryPDF(predictions, userProfile);
    } catch (err) {
      setExportError(apiError(err, 'Failed to export prediction history. Please try again.'));
    } finally {
      setExporting(false);
    }
  };

  const hasDemo = predictions.some((p) => p.is_demo === 'true');

  return (
    <div className="animate-fadeIn space-y-6">
      <PageHeader
        eyebrow="Module 2 · Prediction history"
        title="Prediction history"
        description={loading ? 'Loading your saved results…' : `Previous disease and pest detection results (${total} total).`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleExportHistoryPDF}
              disabled={exporting || loading || predictions.length === 0}
              className="btn btn-secondary"
              title="Download plant disease and pest diagnosis log in PDF format"
              aria-label="Export history log as PDF"
            >
              <FiDownload className={exporting ? 'animate-bounce' : ''} aria-hidden="true" />
              <span>{exporting ? 'Exporting PDF…' : 'Export History (PDF)'}</span>
            </button>
            <Link to="/disease-detection" className="btn btn-primary">
              <FiSearch aria-hidden="true" /> New detection
            </Link>
          </div>
        }
      />

      {error && <div className="alert alert-error" role="alert"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />{error}</div>}
      {exportError && <div className="alert alert-error" role="alert"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />{exportError}</div>}

      {hasDemo && (
        <div className="alert alert-warning text-xs" role="note">
          <FiInfo className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>Rows marked <strong>Demo</strong> are simulated results from the placeholder detector: no trained model was used, so they have no confidence score and are not real diagnoses.</span>
        </div>
      )}

      {loading ? (
        <div className="card p-5 space-y-3" aria-busy="true" aria-label="Loading prediction history">
          {Array.from({ length: 4 }, (_, i) => <div key={i} className="skeleton h-12 w-full" />)}
        </div>
      ) : predictions.length === 0 ? (
        <div className="card">
          <EmptyState icon={FiClock} title="No predictions yet" description="Run a detection in Disease Detection and the results will appear here.">
            <Link to="/disease-detection" className="btn btn-secondary"><FiSearch aria-hidden="true" /> Go to Disease Detection</Link>
          </EmptyState>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="table-clean">
              <caption className="sr-only">Saved disease and pest detection results</caption>
              <thead>
                <tr>
                  <th scope="col">Image</th>
                  <th scope="col">Result</th>
                  <th scope="col">Crop</th>
                  <th scope="col">Type</th>
                  <th scope="col">Confidence</th>
                  <th scope="col">Status</th>
                  <th scope="col">Date</th>
                  <th scope="col"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {predictions.map((pred) => {
                  const isUncertain = pred.prediction_type === 'uncertain' || pred.status === 'uncertain' || (pred.disease_name || '').toLowerCase().includes('unable to identify');
                  const healthy = !isUncertain && pred.disease_name === 'Healthy Plant';
                  const thumb = uploadUrl(pred.image_path);
                  return (
                    <tr key={pred.id} id={`prediction-${pred.id}`} className={String(pred.id) === targetId ? 'bg-green-50' : undefined}
                      aria-current={String(pred.id) === targetId ? 'true' : undefined}>
                      <td>
                        <span className="flex h-11 w-11 items-center justify-center overflow-hidden rounded-lg bg-slate-100 text-slate-400">
                          {thumb ? <img src={thumb} alt={`Leaf image for prediction ${pred.id}`} className="h-full w-full object-cover" loading="lazy" onError={(e) => { e.currentTarget.style.display = 'none'; }} /> : <FiImage aria-hidden="true" />}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${healthy ? 'badge-success' : 'badge-warning'}`}>
                          {healthy ? <FiCheckCircle aria-hidden="true" /> : <FiAlertTriangle aria-hidden="true" />}
                          {pred.disease_name || pred.pest_name || '-'}
                        </span>
                      </td>
                      <td className="text-slate-700">{pred.crop_name || '-'}</td>
                      <td className="capitalize text-slate-600">{pred.prediction_type}</td>
                      <td>
                        {pred.confidence !== null && pred.confidence !== undefined ? (
                          <div className="flex items-center gap-2">
                            <span className="font-medium tnum">{pred.confidence}%</span>
                            <span className="h-1.5 w-16 rounded-full bg-slate-200">
                              <span className={`block h-1.5 rounded-full ${isUncertain ? 'bg-amber-500' : 'bg-green-600'}`} style={{ width: `${pred.confidence}%` }} />
                            </span>
                          </div>
                        ) : <span className="text-xs text-slate-500">{pred.is_demo === 'true' ? 'N/A (simulated)' : '-'}</span>}
                      </td>
                      <td className="whitespace-nowrap">
                        <span className={`badge capitalize ${isUncertain ? 'badge-warning' : pred.status === 'failed' ? 'badge-danger' : 'badge-success'}`}>{pred.status}</span>
                        {pred.is_demo === 'true' && <span className="badge badge-neutral ml-1">Demo</span>}
                      </td>
                      <td className="whitespace-nowrap text-xs text-slate-500 tnum">{pred.created_at ? new Date(pred.created_at).toLocaleString() : '-'}</td>
                      <td className="text-right">
                        <button type="button" onClick={() => handleDelete(pred.id)} disabled={deletingId === pred.id}
                          title="Delete prediction" aria-label={`Delete prediction ${pred.id}`} className="btn btn-ghost btn-danger-ghost btn-sm !px-2">
                          <FiTrash2 aria-hidden="true" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
