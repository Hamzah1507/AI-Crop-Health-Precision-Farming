import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { detectionAPI, samplesAPI, cropsAPI, API_BASE_URL } from '../services/api';
import { apiError } from '../utils/apiError';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import UploadDropzone from '../components/UploadDropzone';
import EmptyState from '../components/EmptyState';
import DetectionResult from '../components/DetectionResult';
import SampleLibrary from '../components/SampleLibrary';
import { FiSearch, FiInfo, FiImage, FiActivity, FiAlertTriangle, FiClock, FiGrid, FiCheckCircle } from 'react-icons/fi';

const CROP_OPTIONS = ['Rice', 'Wheat', 'Corn', 'Tomato', 'Potato', 'Soybean', 'Cotton', 'Sugarcane', 'Groundnut', 'Millet', 'Apple', 'Grape', 'Pepper'];
// Sample-library folder names -> the crop names this page offers
const LIBRARY_CROP_TO_OPTION = { maize: 'Corn' };
const toCropOption = (libraryCrop) => {
  const name = LIBRARY_CROP_TO_OPTION[libraryCrop] || (libraryCrop ? libraryCrop[0].toUpperCase() + libraryCrop.slice(1) : '');
  return CROP_OPTIONS.includes(name) ? name : '';
};

export default function DiseaseDetection() {
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [sample, setSample] = useState(null);          // library item the current image came from (null = user upload)
  const [cropName, setCropName] = useState('');
  const [cropId, setCropId] = useState('');
  const [myCrops, setMyCrops] = useState([]);
  const [library, setLibrary] = useState({ enabled: false, items: [] });
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [modelStatus, setModelStatus] = useState(null);

  useEffect(() => {
    detectionAPI.getStatus().then((res) => setModelStatus(res.data)).catch(() => setModelStatus(null));
    cropsAPI.getAll().then((res) => setMyCrops(res.data)).catch(() => setMyCrops([]));
    // The library is a development aid: when it is switched off or empty the selector simply does not appear
    samplesAPI.list()
      .then((res) => setLibrary({ enabled: !!res.data.enabled, items: res.data.items || [] }))
      .catch(() => setLibrary({ enabled: false, items: [] }));
  }, []);

  // Release the temporary preview URL when it is replaced or the page closes
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const chooseImage = (file, fromSample = null) => {
    setImage(file);
    setPreview(URL.createObjectURL(file));
    setSample(fromSample);
    setResult(null);
    setError('');
  };
  const removeImage = () => { setImage(null); setPreview(null); setSample(null); setResult(null); };

  // A sample goes through exactly the same upload path (and server-side validation) as a user's own photo
  const useSample = async (item) => {
    const res = await axios.get(`${API_BASE_URL}${item.url}`, { responseType: 'blob' }).catch(() => null);
    if (!res) throw new Error('Could not load that sample image. Is the backend running?');
    const file = new File([res.data], item.filename, { type: res.data.type || 'image/jpeg' });
    chooseImage(file, item);
    const option = toCropOption(item.crop);
    if (option) setCropName(option);
  };
  const closeLibrary = useCallback(() => setLibraryOpen(false), []);

  const pickMyCrop = (id) => {
    setCropId(id);
    const crop = myCrops.find((c) => String(c.id) === id);
    if (crop) setCropName(CROP_OPTIONS.find((c) => c.toLowerCase() === crop.name.toLowerCase()) || cropName);
  };

  const handleDetect = async () => {
    if (!image) { setError('Please upload a leaf image first'); return; }
    setLoading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', image);
      if (cropName) formData.append('crop_name', cropName);
      if (cropId) formData.append('crop_id', cropId);
      const res = await detectionAPI.predict(formData);
      setResult(res.data);
    } catch (err) {
      setResult(null);
      setError(apiError(err, 'Detection failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const demoMode = modelStatus ? !modelStatus.model_loaded : true;
  const showLibrary = library.enabled && library.items.length > 0;

  return (
    <div className="animate-fadeIn space-y-6">
      <PageHeader
        eyebrow="Module 2 · Plant disease & pest detection"
        title="Disease & pest detection"
        description="Upload a crop leaf image to check for diseases and pests. Every result is saved to your prediction history."
        actions={<Link to="/prediction-history" className="btn btn-secondary"><FiClock aria-hidden="true" /> History</Link>}
      />

      {demoMode ? (
        <div className="alert alert-warning" role="note">
          <FiInfo className="mt-0.5 shrink-0" aria-hidden="true" />
          <span><strong>Simulated detector:</strong> no trained detection model is loaded, so results on this page are generated for demonstration and are not real diagnoses.</span>
        </div>
      ) : (
        <div className="alert alert-success" role="note">
          <FiCheckCircle className="mt-0.5 shrink-0" aria-hidden="true" />
          <span><strong>Trained AI Model ({modelStatus?.model_type || 'Active'}):</strong> Genuine model is loaded and ready for disease and pest diagnosis.</span>
        </div>
      )}

      {error && <div className="alert alert-error" role="alert"><FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />{error}</div>}

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-5">
        {/* Upload */}
        <SectionCard icon={FiImage} title="Leaf image" description="JPEG, PNG or WebP" className="lg:col-span-2">
          <UploadDropzone id="leaf-image" file={image} previewUrl={preview} onFile={(f) => chooseImage(f)}
            onInvalid={setError} onRemove={removeImage} disabled={loading} />

          {showLibrary && (
            <button type="button" onClick={() => setLibraryOpen(true)} disabled={loading} className="btn btn-secondary mt-3 w-full">
              <FiGrid aria-hidden="true" /> {sample ? 'Choose another sample' : 'Choose from sample library'}
            </button>
          )}

          {sample && (
            <div className="alert alert-info mt-3" role="note">
              <FiInfo className="mt-0.5 shrink-0" aria-hidden="true" />
              <span>
                Sample image. Its <strong>dataset label</strong> is “{sample.label}” ({sample.label_source}), which is the source's description of the photo,
                not what this app predicts. Source: {sample.source}, {sample.license}.
              </span>
            </div>
          )}

          <div className="mt-5">
            <label className="label" htmlFor="crop">Crop <span className="font-normal text-slate-500">(optional)</span></label>
            <select id="crop" value={cropName} onChange={(e) => setCropName(e.target.value)} className="input" disabled={loading}>
              <option value="">Select crop</option>
              {CROP_OPTIONS.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {myCrops.length > 0 && (
            <div className="mt-4">
              <label className="label" htmlFor="my-crop">Link to one of my crops <span className="font-normal text-slate-500">(optional)</span></label>
              <select id="my-crop" value={cropId} onChange={(e) => pickMyCrop(e.target.value)} className="input" disabled={loading}>
                <option value="">Not linked</option>
                {myCrops.map(c => <option key={c.id} value={c.id}>{c.name}{c.variety ? ` (${c.variety})` : ''}</option>)}
              </select>
              <p className="mt-1 text-xs text-slate-500">Linked results appear against that crop in your history and recommendations.</p>
            </div>
          )}

          <button type="button" onClick={handleDetect} disabled={loading || !image} className="btn btn-primary mt-5 w-full">
            {loading ? <span className="h-4 w-4 spinner" aria-hidden="true" /> : <FiSearch aria-hidden="true" />}
            {loading ? 'Analyzing...' : 'Run detection'}
          </button>
        </SectionCard>

        {/* Result */}
        <SectionCard icon={FiActivity} title="Detection result" description={result ? 'Saved to your prediction history' : 'Appears here after you run a detection'} className="lg:col-span-3">
          <div aria-live="polite">
            {!result && !loading && (
              <EmptyState icon={FiSearch} title="No result yet" description="Upload a leaf image and choose Run detection to see the result here." />
            )}

            {loading && (
              <div className="py-12 text-center" role="status">
                <div className="mx-auto mb-3 h-10 w-10 rounded-full border-4 border-green-600 border-t-transparent animate-spin" aria-hidden="true" />
                <p className="text-sm text-slate-500">Analyzing image...</p>
              </div>
            )}

            {result && !loading && (
              <>
                <DetectionResult
                  result={result}
                  previewUrl={preview}
                  fallbackCrop={cropName}
                  isModelLoaded={modelStatus?.model_loaded ?? false}
                />
                <p className="mt-4 text-xs text-slate-500">
                  See all results in your <Link to="/prediction-history" className="font-medium text-green-700 hover:text-green-800">prediction history</Link>,
                  and any treatment advice in <Link to="/recommendations" className="font-medium text-green-700 hover:text-green-800">recommendations</Link>.
                </p>
              </>
            )}
          </div>
        </SectionCard>
      </div>

      {libraryOpen && <SampleLibrary items={library.items} selectedId={sample?.id} onSelect={useSample} onClose={closeLibrary} />}
    </div>
  );
}
