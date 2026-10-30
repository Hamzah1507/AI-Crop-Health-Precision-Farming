import { API_BASE_URL } from '../services/api';

// The backend serves stored images from /uploads/<file>. `image_path` is stored as a
// server path (e.g. "uploads\\abc.jpg"), so only its file name is used to build the URL.
export function uploadUrl(imagePath) {
  if (!imagePath) return null;
  const name = String(imagePath).split(/[\\/]/).pop();
  return name ? `${API_BASE_URL}/uploads/${encodeURIComponent(name)}` : null;
}
