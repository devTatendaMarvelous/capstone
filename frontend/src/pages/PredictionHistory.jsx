import { useEffect, useState } from "react";
import DataTable from "../components/DataTable";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import { errorMessage } from "../services/api";
import { listPredictions } from "../services/predictionService";

export default function PredictionHistoryPage() {
  const [rows, setRows] = useState(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    listPredictions().then(setRows).catch((error) => setMessage(errorMessage(error)));
  }, []);

  if (!rows && !message) return <LoadingState />;
  return (
    <section className="panel">
      <p className="page-kicker">Records</p>
      <h1 className="page-title">Prediction history</h1>
      <p className="mt-2 text-sm text-ink/65">Farmers see their own estimates. Analysts, researchers, and administrators see the shared history.</p>
      <ErrorState message={message} />
      <div className="mt-4">
        <DataTable
          columns={[
            { key: "created_at", label: "When", render: (row) => row.created_at?.slice(0, 16).replace("T", " ") },
            { key: "username", label: "User" },
            { key: "predicted_yield", label: "Yield t/ha" },
            { key: "farm_area", label: "Area ha" },
            { key: "predicted_production", label: "Production t" },
            { key: "model_version", label: "Model" },
          ]}
          rows={rows || []}
          empty="No predictions stored."
        />
      </div>
    </section>
  );
}
