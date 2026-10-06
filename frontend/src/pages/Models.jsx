import { useEffect, useState } from "react";
import DataTable from "../components/DataTable";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import ModelBadge from "../components/ModelBadge";
import { getOverview } from "../services/analyticsService";
import { errorMessage } from "../services/api";
import { activateModel, listModels } from "../services/modelService";
import { useAuth } from "../hooks/useAuth";

export default function ModelsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState(null);
  const [importance, setImportance] = useState([]);
  const [message, setMessage] = useState("");

  function refresh() {
    return Promise.all([listModels(), getOverview()])
      .then(([models, overview]) => {
        setRows(models);
        setImportance(overview.feature_importance || []);
      })
      .catch((error) => setMessage(errorMessage(error)));
  }

  useEffect(() => {
    refresh();
  }, []);

  if (!rows && !message) return <LoadingState />;
  const active = rows?.find((row) => row.is_active);

  return (
    <div className="space-y-6">
      <header>
        <p className="page-kicker">Registry</p>
        <h1 className="page-title">Models</h1>
      </header>
      <ModelBadge model={active} />
      <ErrorState message={message} />
      <div className="panel">
        <DataTable
          columns={[
            { key: "algorithm", label: "Algorithm" },
            { key: "version", label: "Version" },
            { key: "r2", label: "R²" },
            { key: "rmse", label: "RMSE" },
            { key: "mae", label: "MAE" },
            { key: "is_active", label: "Active", render: (row) => (row.is_active ? "Yes" : "No") },
            {
              key: "activate",
              label: "",
              render: (row) =>
                user?.role === "admin" && !row.is_active ? (
                  <button type="button" className="text-leaf underline" onClick={() => activateModel(row.id).then(refresh).catch((error) => setMessage(errorMessage(error)))}>
                    Activate
                  </button>
                ) : null,
            },
          ]}
          rows={rows || []}
          empty="No model has been registered."
        />
      </div>
      <section className="panel">
        <h2 className="font-serif text-2xl text-ink">Top factors</h2>
        <p className="mt-2 text-sm text-ink/70">Feature importance indicates variables that contributed strongly to model predictions. It does not prove causation.</p>
        <ol className="mt-3 space-y-1 text-sm">
          {importance.slice(0, 5).map((item) => (
            <li key={item.feature}>
              {item.rank}. {item.feature} — {Number(item.importance_mean).toFixed(3)}
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
