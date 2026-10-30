import axios from 'axios';

// VITE_API_URL lets a second dev server talk to an isolated test backend; normal runs use the default
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor - attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // A 401 from the login request just means wrong credentials: let the Login
    // page show the error instead of reloading it. Only expired/invalid sessions
    // on other requests force a redirect.
    const isLoginRequest = error.config?.url?.includes('/api/auth/login');
    if (error.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const authAPI = {
  register: (data) => api.post('/api/auth/register', data),
  login: (data) => api.post('/api/auth/login', data),
  getMe: () => api.get('/api/auth/me'),
};

// Users
export const usersAPI = {
  getProfile: () => api.get('/api/users/profile'),
  updateProfile: (data) => api.put('/api/users/profile', data),
};

// Farms
export const farmsAPI = {
  create: (data) => api.post('/api/farms/', data),
  // Idempotent: creates the default farm only when the user has none (safe to call on every dashboard load)
  ensureDefault: () => api.post('/api/farms/default'),
  getAll: () => api.get('/api/farms/'),
  get: (id) => api.get(`/api/farms/${id}`),
  update: (id, data) => api.put(`/api/farms/${id}`, data),
  delete: (id) => api.delete(`/api/farms/${id}`),
};

// Crops
export const cropsAPI = {
  create: (data) => api.post('/api/crops/', data),
  getAll: (farmId) => api.get('/api/crops/', { params: { farm_id: farmId } }),
  get: (id) => api.get(`/api/crops/${id}`),
  delete: (id) => api.delete(`/api/crops/${id}`),
};

// Soil
export const soilAPI = {
  createRecord: (data) => api.post('/api/soil/records', data),
  getRecords: () => api.get('/api/soil/records'),
  // Latest record + its rule-based assessment (read-only; used by the dashboard)
  // Optionally a specific saved record (the one a recommendation came from); otherwise the newest
  getLatest: (recordId) => api.get('/api/soil/latest', recordId ? { params: { record_id: recordId } } : undefined),
  analyze: (data) => api.post('/api/soil/analyze', data),
};

// Weather
export const weatherAPI = {
  fetch: (data) => api.post('/api/weather/fetch', data),
  // Read-only lookup (nothing is stored); used by the dashboard summary
  current: (location) => api.get('/api/weather/current', { params: { location } }),
};

// Detection
export const detectionAPI = {
  predict: (formData) => api.post('/api/detection/predict', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  getStatus: () => api.get('/api/detection/status'),
};

// Sample image library (development / demo aid)
export const samplesAPI = {
  list: (params) => api.get('/api/samples/', { params }),
};

// Predictions
export const predictionsAPI = {
  getAll: (skip = 0, limit = 50) => api.get('/api/predictions/', { params: { skip, limit } }),
  get: (id) => api.get(`/api/predictions/${id}`),
  getRecommendations: (id) => api.get(`/api/predictions/${id}/recommendations`),
  delete: (id) => api.delete(`/api/predictions/${id}`),
};

// Recommendations
export const recommendationsAPI = {
  getAll: (type) => api.get('/api/recommendations/', { params: { type } }),
  getRecent: () => api.get('/api/recommendations/recent'),
};

// Yield
export const yieldAPI = {
  predict: (data) => api.post('/api/yield/predict', data),
  getHistory: () => api.get('/api/yield/history'),
};

// Chatbot
export const chatbotAPI = {
  sendMessage: (data) => api.post('/api/chatbot/message', data),
  getConversations: () => api.get('/api/chatbot/conversations'),
  getConversation: (id) => api.get(`/api/chatbot/conversations/${id}`),
  deleteConversation: (id) => api.delete(`/api/chatbot/conversations/${id}`),
};

// Admin
export const adminAPI = {
  getStats: () => api.get('/api/admin/stats'),
  getUsers: () => api.get('/api/admin/users'),
  getPredictions: (skip = 0, limit = 100) => api.get('/api/admin/predictions', { params: { skip, limit } }),
  toggleUserActive: (userId) => api.put(`/api/admin/users/${userId}/toggle-active`),
};

// Farm Analytics & Reporting
export const analyticsAPI = {
  getSummary: (farmId) => api.get('/api/analytics/summary', { params: farmId ? { farm_id: farmId } : undefined }),
  getTrends: (params) => api.get('/api/analytics/trends', { params }),
  getReportData: (farmId) => api.get('/api/analytics/report-data', { params: farmId ? { farm_id: farmId } : undefined }),
};

export { API_BASE_URL };
export default api;
