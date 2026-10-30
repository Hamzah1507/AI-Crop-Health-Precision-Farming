import { useState } from 'react';
import { FiUploadCloud, FiRefreshCw, FiX } from 'react-icons/fi';
import { validateImageFile, MAX_IMAGE_MB } from '../utils/imageValidation';

// Keyboard-accessible leaf-image picker with drag-and-drop and preview.
// Client checks are a convenience only; the backend validates the real file bytes.
export default function UploadDropzone({ id, file, previewUrl, onFile, onInvalid, onRemove, disabled = false }) {
  const [dragging, setDragging] = useState(false);

  const accept = (picked) => {
    if (!picked) return;
    const problem = validateImageFile(picked);
    if (problem) { onInvalid?.(problem); return; }
    onFile(picked);
  };

  const handleChange = (e) => {
    const picked = e.target.files[0];
    e.target.value = '';           // allow choosing the same file again
    accept(picked);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (!disabled) accept(e.dataTransfer.files[0]);
  };

  return (
    <div>
      <input id={id} type="file" accept="image/jpeg,image/png,image/webp" onChange={handleChange}
        disabled={disabled} className="peer sr-only" />
      {previewUrl ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <img src={previewUrl} alt="Selected leaf preview" className="mx-auto max-h-56 w-full rounded-lg object-contain" />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <p className="min-w-0 truncate text-xs text-slate-500">
              {file?.name} · {file ? `${(file.size / 1024).toFixed(0)} KB` : ''}
            </p>
            <div className="flex gap-2">
              <label htmlFor={id} className={`btn btn-secondary btn-sm ${disabled ? 'pointer-events-none opacity-60' : 'cursor-pointer'}`}>
                <FiRefreshCw aria-hidden="true" /> Replace
              </label>
              <button type="button" onClick={onRemove} disabled={disabled} className="btn btn-ghost btn-danger-ghost btn-sm">
                <FiX aria-hidden="true" /> Remove
              </button>
            </div>
          </div>
        </div>
      ) : (
        <label htmlFor={id}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`flex w-full cursor-pointer flex-col items-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors
            peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-green-500
            ${dragging ? 'border-green-500 bg-green-50' : 'border-slate-300 hover:border-green-500 hover:bg-green-50/50'}
            ${disabled ? 'pointer-events-none opacity-60' : ''}`}>
          <span className="icon-tile mb-3" aria-hidden="true"><FiUploadCloud /></span>
          <span className="text-sm font-medium text-slate-800">Click to upload, or drag a leaf image here</span>
          <span className="mt-1 text-xs text-slate-500">JPEG, PNG or WebP, up to {MAX_IMAGE_MB} MB</span>
        </label>
      )}
    </div>
  );
}
