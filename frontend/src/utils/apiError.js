// Turn an axios error into a message a farmer can act on (never a raw stack or "[object Object]").
export function apiError(err, fallback = 'Something went wrong. Please try again.') {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return `Please check the form: ${detail[0].msg}`;   // FastAPI validation errors
  const status = err?.response?.status;
  if (status === 413) return 'That file is too large to upload.';
  if (status === 429) return 'Too many requests. Please wait a moment and try again.';
  if (status >= 500) return `The server had a problem (HTTP ${status}). Please try again in a moment.`;
  if (status === 403) return 'You do not have permission to do that.';
  if (!err?.response && err?.request) return 'Cannot reach the server. Check your connection and that the backend is running.';
  return fallback;
}
