import { useState } from "react";
import { Link } from "react-router-dom";
import ErrorState from "../components/ErrorState";
import PredictionForm from "../components/PredictionForm";
import { errorMessage } from "../services/api";
import { createPrediction } from "../services/predictionService";
import { downloadReport } from "../services/reportService";

export default function PredictionPage() {
  const [result, setResult] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(payload, errors) {
    setFieldErrors(errors);
    setMessage("");
    if (Object.keys(errors).length) {
      setMessage("Please check the highlighted errors above.");
      return;
    }
    setBusy(true);
    try {
      setResult(await createPrediction(payload));
    } catch (error) {
      setResult(null);
      const data = error.response?.data;
      setFieldErrors(data?.errors || {});
      setMessage(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
      <section>
        <p className="page-kicker">Prediction</p>
        <h1 className="page-title">Estimate maize yield</h1>
        <p className="mt-2 max-w-2xl text-sm text-ink/65">
          Select and confirm your farm location to automatically acquire rainfall, temperature, and soil metrics.
          You only need to enter cultivated area, planting date, and fertilizer rate.
        </p>
        <div className="mt-4">
          <ErrorState message={message} />
          {Object.entries(fieldErrors).map(([field, texts]) => (
            <p key={field} className="mt-1 text-sm text-clay">
              {field}: {Array.isArray(texts) ? texts.join(" ") : texts}
            </p>
          ))}
        </div>
        <div className="mt-4">
          <PredictionForm onSubmit={onSubmit} busy={busy} />
        </div>
      </section>

      <aside className="h-fit rounded-3xl bg-[#10281c] p-6 text-white shadow-card lg:sticky lg:top-8 space-y-4">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-lime">Prediction Result</p>
        {result ? (
          <div className="space-y-4">
            <div>
              <p className="font-serif text-5xl tracking-tight">
                {result.predicted_yield_t_ha}
                <span className="ml-2 text-2xl text-white/60">t/ha</span>
              </p>
              <p className="mt-2 text-white/80 text-sm leading-relaxed">{result.interpretation}</p>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-2xl bg-white/10 p-3">
                <p className="text-white/55 text-xs">Total Production</p>
                <p className="mt-1 text-lg font-semibold">{result.estimated_production_tonnes ?? result.predicted_production_tonnes} t</p>
              </div>
              <div className="rounded-2xl bg-white/10 p-3">
                <p className="text-white/55 text-xs">Model Version</p>
                <p className="mt-1 text-lg font-semibold">v{result.model_version}</p>
              </div>
            </div>

            {/* Farm Location Provenance */}
            {result.location && (
              <div className="rounded-2xl bg-white/5 p-3.5 text-xs space-y-1.5 border border-white/10">
                <div className="flex items-center justify-between">
                  <span className="text-white/60 font-medium">Farm Location</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${result.location.is_within_study_area ? "bg-lime/20 text-lime" : "bg-amber-400/20 text-amber-300"}`}>
                    {result.location.is_within_study_area ? "Macheke Scope" : "Experimental Scope"}
                  </span>
                </div>
                <p className="font-mono text-white/90">
                  {result.location.latitude.toFixed(4)}°, {result.location.longitude.toFixed(4)}°
                </p>
                <p className="text-white/50 text-[11px]">
                  Method: {String(result.location.location_selection_method || "").replace(/_/g, " ")}
                </p>
              </div>
            )}

            {/* Data Sources Provenance */}
            {result.data_sources?.length > 0 && (
              <div className="rounded-2xl bg-white/5 p-3.5 text-xs space-y-1.5 border border-white/10">
                <span className="text-white/60 font-medium block">Acquired Data Sources</span>
                <ul className="space-y-1 text-[11px] text-white/80">
                  {result.data_sources.map((src, i) => (
                    <li key={i} className="flex items-start gap-1">
                      <span className="text-lime">•</span>
                      <span>
                        <strong>{src.provider || src.dataset_name}:</strong> {src.spatial_resolution || src.temporal_resolution || "Recorded"}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Quality warnings */}
            {result.data_quality?.warnings?.length > 0 && (
              <div className="rounded-2xl bg-amber-500/20 p-3 text-xs text-amber-200 space-y-1">
                {result.data_quality.warnings.map((w, idx) => (
                  <p key={idx}>⚠️ {w}</p>
                ))}
              </div>
            )}

            <div className="pt-2 border-t border-white/10">
              <p className="text-xs text-white/50 leading-relaxed">{result.disclaimer}</p>
            </div>

            <div className="flex flex-wrap gap-2 pt-2">
              <Link to="/history" className="rounded-xl bg-lime px-3 py-2 text-sm font-semibold text-ink hover:bg-[#b0d944] transition">
                View history
              </Link>
              <button
                type="button"
                className="rounded-xl bg-white/10 px-3 py-2 text-sm font-semibold text-white hover:bg-white/20 transition"
                onClick={() => downloadReport("/api/v1/reports/predictions/", "pdf")}
              >
                Download report
              </button>
            </div>
          </div>
        ) : (
          <p className="mt-4 text-sm text-white/65">
            Select a farm location and specify cultivated area to generate a crop yield prediction.
          </p>
        )}
      </aside>
    </div>
  );
}
