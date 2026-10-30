import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/auth';
import DashboardLayout from './layouts/DashboardLayout';

// Routed modules: Data Acquisition, Disease Detection (simulated until a trained
// model is loaded), Soil Analysis, Recommendations (both rule-based), Yield
// Estimate (rule-based), Prediction History and Profile. The chatbot, analytics
// and admin screens have no frontend pages yet.

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import DataAcquisition from './pages/DataAcquisition';
import DiseaseDetection from './pages/DiseaseDetection';
import PredictionHistory from './pages/PredictionHistory';
import Profile from './pages/Profile';
import SoilAnalysis from './pages/SoilAnalysis';
import SmartRecommendations from './pages/SmartRecommendations';
import CropYieldPrediction from './pages/CropYieldPrediction';
import Chatbot from './pages/Chatbot';

// Protected Route Wrapper
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ivory" role="status">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 rounded-full border-4 border-green-600 border-t-transparent animate-spin" aria-hidden="true" />
          <p className="text-sm text-slate-500">Loading...</p>
        </div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  
  return children;
};

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<Navigate to="/login" replace />} />
          
          {/* Protected Routes (Dashboard Layout) */}
          <Route path="/" element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="data-acquisition" element={<DataAcquisition />} />
            <Route path="disease-detection" element={<DiseaseDetection />} />
            <Route path="soil-analysis" element={<SoilAnalysis />} />
            <Route path="recommendations" element={<SmartRecommendations />} />
            <Route path="yield-prediction" element={<CropYieldPrediction />} />
            <Route path="prediction-history" element={<PredictionHistory />} />
            <Route path="chatbot" element={<Chatbot />} />
            <Route path="profile" element={<Profile />} />
          </Route>
          
          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
