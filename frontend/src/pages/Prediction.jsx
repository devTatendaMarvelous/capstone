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
      setMessage("Check the highlighted inputs.");
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
          Inputs match the saved model. Area is used only to turn tonnes per hectare into total tonnes.
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
      <aside className="h-fit rounded-3xl bg-[#10281c] p-6 text-white shadow-card lg:sticky lg:top-8">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-lime">Result</p>
        {result ? (
          <div className="mt-4 space-y-4">
            <p className="font-serif text-5xl tracking-tight">{result.predicted_yield_t_ha}<span className="ml-2 text-2xl text-white/60">t/ha</span></p>
            <p className="text-white/80">{result.interpretation}</p>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-2xl bg-white/10 p-3">
                <p className="text-white/55">Production</p>
                <p className="mt-1 text-lg font-semibold">{result.predicted_production_tonnes} t</p>
              </div>
              <div className="rounded-2xl bg-white/10 p-3">
                <p className="text-white/55">Model</p>
                <p className="mt-1 text-lg font-semibold">v{result.model_version}</p>
              </div>
            </div>
            <p className="text-sm text-white/55">{result.disclaimer}</p>
            <div className="flex flex-wrap gap-2">
              <Link to="/history" className="rounded-xl bg-lime px-3 py-2 text-sm font-semibold text-ink">
                View history
              </Link>
              <button type="button" className="rounded-xl bg-white/10 px-3 py-2 text-sm font-semibold text-white" onClick={() => downloadReport("/api/v1/reports/predictions/", "pdf")}>
                Download prediction report
              </button>
            </div>
          </div>
        ) : (
          <p className="mt-4 text-sm text-white/65">The estimate will appear here. It is saved when the request succeeds.</p>
        )}
      </aside>
    </div>
  );
}
