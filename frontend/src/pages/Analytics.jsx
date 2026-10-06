import { useEffect, useState } from "react";
import { ImportanceChart, RainChart, SeasonChart, YieldBins } from "../components/Charts";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import { getOverview } from "../services/analyticsService";
import { errorMessage } from "../services/api";

export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    getOverview().then(setData).catch((error) => setMessage(errorMessage(error)));
  }, []);

  if (!data && !message) return <LoadingState />;

  return (
    <div className="space-y-6">
      <header>
        <p className="page-kicker">Insights</p>
        <h1 className="page-title">Analytics</h1>
        <p className="mt-2 max-w-3xl text-sm text-ink/65">
          Dataset charts read the latest validated file. Prediction charts read stored estimates. Model metrics come from the active registry entry.
        </p>
      </header>
      <ErrorState message={message} />
      {data ? (
        <>
          <Section title="Dataset overview">
            <p>Records on the latest validated file: {data.dataset_records}</p>
            <Quality quality={data.data_quality} />
          </Section>
          <Section title="Yield analysis">
            {data.yield_by_season?.length ? <SeasonChart data={data.yield_by_season} /> : <EmptyState title="No season table" body="The dataset needs a season column and yield_t_ha." />}
            <div className="mt-4">{data.yield_distribution?.length ? <YieldBins data={data.yield_distribution} /> : <EmptyState title="No predicted-yield bins" body="Save a prediction to fill this chart." />}</div>
          </Section>
          <Section title="Weather and management">
            {data.rainfall_vs_yield?.length ? <RainChart data={data.rainfall_vs_yield} /> : <EmptyState title="No rainfall plot" body="The latest dataset has no rainfall and yield pair." />}
          </Section>
          <Section title="Model insights">
            <p className="mb-2 text-sm">R² {data.model_r2 ?? "—"} · RMSE {data.model_rmse ?? "—"} · MAE {data.model_mae ?? "—"}</p>
            {data.feature_importance?.length ? <ImportanceChart data={data.feature_importance} /> : <EmptyState title="No importance table" body="Train and register a model to see permutation importance." />}
            <p className="mt-2 text-xs text-ink/70">Feature importance indicates variables that contributed strongly to model predictions. It does not prove causation.</p>
          </Section>
        </>
      ) : null}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="panel">
      <h2 className="mb-4 font-serif text-2xl text-ink">{title}</h2>
      {children}
    </section>
  );
}

function Quality({ quality }) {
  if (!quality) return <p className="text-sm text-ink/70">No dataset file is available to summarise.</p>;
  return (
    <ul className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
      <li>Observations: {quality.observations}</li>
      <li>Missing cells: {quality.missing_cells}</li>
      <li>Duplicate rows: {quality.duplicate_rows}</li>
      <li>Invalid values: {quality.invalid_values}</li>
      <li>Feature completeness: {quality.feature_completeness_percent}%</li>
      <li className="sm:col-span-2 text-ink/70">{quality.completeness_definition}</li>
    </ul>
  );
}
