// Mirrors the backend rules in app/utils/file_handler.py (JPEG, PNG, WebP; 10 MB).
export const MAX_IMAGE_MB = 10;
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const ALLOWED_EXTS = ['jpg', 'jpeg', 'png', 'webp'];

/** Returns an error message for an unacceptable image file, or '' when it is fine. */
export function validateImageFile(file) {
  if (!file) return 'Please choose an image file.';
  const ext = (file.name || '').split('.').pop().toLowerCase();
  const validMime = ALLOWED_TYPES.includes(file.type);
  const validExt = ALLOWED_EXTS.includes(ext);
  if (!validMime && !validExt) return 'Unsupported file type. Please upload a JPEG, PNG or WebP image.';
  if (file.size > MAX_IMAGE_MB * 1024 * 1024) return `Image is too large. Maximum size is ${MAX_IMAGE_MB} MB.`;
  if (file.size === 0) return 'The selected file is empty.';
  return '';
}
