import { Link } from 'react-router-dom';
import {
  FiArrowUpRight, FiSearch, FiDroplet, FiStar,
  FiClock, FiShield
} from 'react-icons/fi';
import { uploadUrl } from '../../utils/uploadUrl';

export default function ChatbotContextPanel({
  predictions = [],
  recommendations = [],
  soilRecord = null
}) {
  const latestPrediction = predictions && predictions.length > 0 ? predictions[0] : null;
  const otherPredictions = predictions && predictions.length > 1 ? predictions.slice(1, 3) : [];
  const remainingCount = predictions && predictions.length > 3 ? predictions.length - 3 : 0;

  const latestRecommendation = recommendations && recommendations.length > 0 ? recommendations[0] : null;

  // Format date nicely
  const formatDate = (isoString) => {
    if (!isoString) return 'Recent';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return 'Recent';
    }
  };

  return (
    <div className="flex h-full flex-col bg-white border-l border-slate-200 p-3.5 sm:p-4 overflow-y-auto space-y-5">
      {/* ------------------------------------------------------------- */}
      {/* SECTION 1: TODAY / RECENT ACTIVITY (matches IMAGE 1 Top Right)*/}
      {/* ------------------------------------------------------------- */}
      <div>
        <div className="flex items-center justify-between px-1 mb-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Today</p>
          <span className="text-[11px] text-slate-400">Live Context</span>
        </div>

        {/* Leaf Disease Detection Card */}
        <div className="rounded-2xl border border-slate-200/90 bg-slate-50/70 p-3.5 shadow-sm transition hover:shadow-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-green-100 text-green-800 text-xs font-medium">
                <FiSearch />
              </span>
              <div>
                <p className="text-xs font-semibold text-slate-900 leading-tight">Leaf Disease Detection</p>
                <p className="text-[10px] text-slate-500">
                  {latestPrediction ? formatDate(latestPrediction.created_at) : 'No scans today'}
                </p>
              </div>
            </div>
            <Link
              to="/disease-detection"
              title="Open Disease Detection module"
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700 transition"
            >
              <FiArrowUpRight className="text-sm" />
            </Link>
          </div>

          {/* Visual Gallery Layout (Recreates Leaf Photo arrangement from IMAGE 1) */}
          {latestPrediction ? (
            <div className="mt-3">
              <div className="grid grid-cols-3 gap-2">
                {/* Main Large Leaf Thumbnail */}
                <div className="col-span-2 relative h-28 overflow-hidden rounded-xl bg-slate-200 border border-slate-200">
                  {latestPrediction.image_path ? (
                    <img
                      src={uploadUrl(latestPrediction.image_path)}
                      alt={latestPrediction.disease_name || 'Crop Leaf'}
                      className="h-full w-full object-cover"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-green-50 text-green-700 text-xs">
                      No photo
                    </div>
                  )}
                  {/* Status Pill on image */}
                  <div className="absolute bottom-1.5 left-1.5 rounded-md bg-slate-900/80 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
                    {latestPrediction.crop_name || 'Crop Leaf'}
                  </div>
                </div>

                {/* Secondary Thumbnails Stack */}
                <div className="flex flex-col gap-2">
                  {otherPredictions.map((op, idx) => (
                    <div key={idx} className="relative h-[3.25rem] overflow-hidden rounded-lg bg-slate-200 border border-slate-200">
                      {op.image_path ? (
                        <img
                          src={uploadUrl(op.image_path)}
                          alt={op.disease_name || 'Leaf scan'}
                          className="h-full w-full object-cover"
                          onError={(e) => {
                            e.target.style.display = 'none';
                          }}
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center bg-slate-100 text-[10px] text-slate-500">
                          Scan #{idx + 2}
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Remaining items indicator like IMAGE 1 (+02 Image More) */}
                  {remainingCount > 0 && (
                    <div className="flex flex-1 items-center justify-center rounded-lg bg-slate-200/90 text-[10px] font-semibold text-slate-700">
                      +{remainingCount} More
                    </div>
                  )}
                </div>
              </div>

              {/* Diagnosis Details */}
              <div className="mt-3 rounded-xl bg-white p-2.5 border border-slate-200">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800 truncate">
                    {latestPrediction.disease_name || 'Diagnosed Condition'}
                  </span>
                  {latestPrediction.confidence ? (
                    <span className="rounded-md bg-green-50 px-1.5 py-0.5 text-[10px] font-medium text-green-700">
                      {latestPrediction.confidence}%
                    </span>
                  ) : null}
                </div>

                {/* AI Model Tag */}
                <div className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-500">
                  <FiShield className={latestPrediction.is_demo === 'false' ? 'text-green-600' : 'text-amber-500'} />
                  <span>
                    {latestPrediction.is_demo === 'false' ? 'Verified ResNet-18 Inference' : 'Demonstration Fallback'}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-2 text-center py-4 text-xs text-slate-500">
              <p>No recent leaf scans found.</p>
              <Link to="/disease-detection" className="mt-1 inline-block text-xs font-medium text-green-700 hover:underline">
                Upload a leaf image
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* SECTION 2: YESTERDAY / FARM RECOMMENDATIONS (matches IMAGE 1) */}
      {/* ------------------------------------------------------------- */}
      <div>
        <div className="flex items-center justify-between px-1 mb-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Recent Insights</p>
          <span className="text-[11px] text-slate-400">Agronomy</span>
        </div>

        {/* AI Recommendation Card */}
        <div className="rounded-2xl border border-slate-200/90 bg-slate-50/70 p-3.5 shadow-sm transition hover:shadow-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-green-100 text-green-800 text-xs font-medium">
                <FiStar />
              </span>
              <div>
                <p className="text-xs font-semibold text-slate-900 leading-tight">AI Recommendation</p>
                <p className="text-[10px] text-slate-500">
                  {latestRecommendation ? formatDate(latestRecommendation.created_at) : 'Advisory Engine'}
                </p>
              </div>
            </div>
            <Link
              to="/recommendations"
              title="Open Smart Recommendations module"
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700 transition"
            >
              <FiArrowUpRight className="text-sm" />
            </Link>
          </div>

          <div className="mt-2.5 rounded-xl bg-white p-2.5 border border-slate-200">
            {latestRecommendation ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-800 truncate">
                    {latestRecommendation.title}
                  </span>
                  <span className="capitalize text-[10px] rounded-md bg-green-50 px-1.5 py-0.5 font-medium text-green-700">
                    {latestRecommendation.type}
                  </span>
                </div>
                <p className="mt-1 line-clamp-2 text-xs text-slate-600 leading-relaxed">
                  {latestRecommendation.description}
                </p>
              </>
            ) : (
              <p className="text-xs text-slate-500">
                Balanced soil parameters. Follow routine irrigation schedule and scout for early leaf spot symptoms.
              </p>
            )}
          </div>
        </div>

        {/* Soil Health Status Mini Card */}
        {soilRecord && (
          <div className="mt-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-xs font-medium text-slate-700">
                <FiDroplet className="text-green-700" /> Soil Health Status
              </span>
              <span className="rounded-md bg-green-50 px-2 py-0.5 text-[10px] font-semibold text-green-800">
                pH {soilRecord.ph ?? '7.0'}
              </span>
            </div>
            <div className="mt-2 grid grid-cols-3 gap-1.5 text-center text-[10px]">
              <div className="rounded-lg bg-slate-50 p-1.5 border border-slate-100">
                <span className="text-slate-400 block">N</span>
                <span className="font-semibold text-slate-800">{soilRecord.nitrogen ?? 23} kg/ha</span>
              </div>
              <div className="rounded-lg bg-slate-50 p-1.5 border border-slate-100">
                <span className="text-slate-400 block">P</span>
                <span className="font-semibold text-slate-800">{soilRecord.phosphorus ?? 21} kg/ha</span>
              </div>
              <div className="rounded-lg bg-slate-50 p-1.5 border border-slate-100">
                <span className="text-slate-400 block">K</span>
                <span className="font-semibold text-slate-800">{soilRecord.potassium ?? 29} kg/ha</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* SECTION 3: QUICK ACTIONS                                       */}
      {/* ------------------------------------------------------------- */}
      <div>
        <p className="px-1 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Quick Actions</p>
        <div className="space-y-1.5">
          <Link
            to="/disease-detection"
            className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm transition hover:border-green-300 hover:bg-green-50/50 hover:text-green-900"
          >
            <span className="flex items-center gap-2">
              <FiSearch className="text-green-700" /> Detect Crop Disease
            </span>
            <FiArrowUpRight className="text-slate-400" />
          </Link>

          <Link
            to="/soil-analysis"
            className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm transition hover:border-green-300 hover:bg-green-50/50 hover:text-green-900"
          >
            <span className="flex items-center gap-2">
              <FiDroplet className="text-green-700" /> Soil Health Analysis
            </span>
            <FiArrowUpRight className="text-slate-400" />
          </Link>

          <Link
            to="/recommendations"
            className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm transition hover:border-green-300 hover:bg-green-50/50 hover:text-green-900"
          >
            <span className="flex items-center gap-2">
              <FiStar className="text-green-700" /> Smart Recommendations
            </span>
            <FiArrowUpRight className="text-slate-400" />
          </Link>

          <Link
            to="/prediction-history"
            className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm transition hover:border-green-300 hover:bg-green-50/50 hover:text-green-900"
          >
            <span className="flex items-center gap-2">
              <FiClock className="text-green-700" /> Diagnostic History
            </span>
            <FiArrowUpRight className="text-slate-400" />
          </Link>
        </div>
      </div>
    </div>
  );
}
