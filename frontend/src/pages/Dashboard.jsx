import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ImportanceChart, RainChart, SeasonChart, TimeChart, YieldBins } from "../components/Charts";
import DataTable from "../components/DataTable";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import ReportButton from "../components/ReportButton";
import { getOverview } from "../services/analyticsService";
import { errorMessage } from "../services/api";
import { downloadReport } from "../services/reportService";

const SEASON = [
  ["Nov", false],
  ["Dec", false],
  ["Jan", true],
  ["Feb", true],
  ["Mar", false],
];

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    getOverview().then(setData).catch((error) => setMessage(errorMessage(error)));
  }, []);

  async function exportReport(path, format, key) {
    setBusy(key);
    try {
      await downloadReport(path, format);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setBusy("");
    }
  }

  if (!data && !message) return <LoadingState />;

  const synthetic = /synthetic/i.test(data?.disclaimer || "");
  const model = data?.active_model;

  return (
    <div className="desk -mx-4 space-y-6 px-4 py-6 sm:-mx-8 sm:px-8">
      <header className="border-b-4 border-double border-ink pb-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-moss">Mashonaland East · Zimbabwe</p>
            <h1 className="mt-1 font-serif text-5xl tracking-tight text-ink">Macheke maize desk</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink/70">
              A working record for maize yield in tonnes per hectare. Saved estimates are model outputs. They are not weighed harvests from Macheke farms.
            </p>
          </div>
          <Link to="/predict" className="btn-primary">
            Record an estimate
          </Link>
        </div>
        <dl className="mt-5 grid gap-px overflow-hidden rounded-md border border-ink/15 bg-ink/10 sm:grid-cols-4">
          <Fact label="Crop" value="Maize" note="Only crop in this study" />
          <Fact label="Season window" value="November–March" note="Research assumption, harvest year" />
          <Fact label="Critical months" value="January–February" note="Marked on the season strip" />
          <Fact label="Reference point" value="18.14°S, 31.85°E" note="Macheke town, not a farm boundary" />
        </dl>
        <ol className="mt-4 flex gap-1" aria-label="Maize season months">
          {SEASON.map(([month, critical]) => (
            <li
              key={month}
              className={`flex-1 rounded-sm px-1 py-2 text-center text-xs font-semibold ${critical ? "bg-leaf text-white" : "bg-white text-ink ring-1 ring-ink/10"}`}
            >
              {month}
              <span className="mt-0.5 block text-[10px] font-medium opacity-70">{critical ? "Critical" : "Season"}</span>
            </li>
          ))}
        </ol>
      </header>

      <ErrorState message={message} />

      {data ? (
        <>
          {/*{data.disclaimer ? (*/}
          {/*  <aside className="border-l-4 border-clay bg-white px-4 py-3 text-sm leading-relaxed text-ink">*/}
          {/*    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-clay">*/}
          {/*      {synthetic ? "Development model" : "Model note"}*/}
          {/*    </p>*/}
          {/*    <p className="mt-1">{data.disclaimer}</p>*/}
          {/*  </aside>*/}
          {/*) : null}*/}

          <section className="grid overflow-hidden rounded-md border border-ink/15 bg-white sm:grid-cols-2 lg:grid-cols-5">
            <Ledger label="Estimates on file" value={data.total_predictions} note="Saved prediction requests" />
            <Ledger label="Mean estimate" value={data.average_predicted_yield ?? "—"} note="t/ha, not a harvest mean" />
            <Ledger label="Served model" value={model ? `v${model.version}` : "—"} note={model?.algorithm || "No active model"} />
            <Ledger label="Test R²" value={data.model_r2 ?? "—"} note="Coefficient of determination" />
            <Ledger label="File rows" value={data.dataset_records} note="Latest validated dataset" />
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <ChartCard
              kicker="Estimate log"
              title="When estimates were saved"
              caption="Each bar is a count of stored prediction requests. It is not rainfall or a count of farms."
            >
              {data.predictions_over_time?.length ? (
                <TimeChart data={data.predictions_over_time} />
              ) : (
                <EmptyState title="No estimates saved" body="The log fills after the first successful prediction." />
              )}
            </ChartCard>
            <ChartCard
              kicker="Estimate log"
              title="Spread of estimated yield"
              caption="Bins are calculated from saved estimates, in tonnes per hectare."
            >
              {data.yield_distribution?.length ? (
                <YieldBins data={data.yield_distribution} />
              ) : (
                <EmptyState title="No estimate spread yet" body="This chart uses stored predictions." />
              )}
            </ChartCard>
            <ChartCard
              kicker="Model"
              title="Inputs that moved the estimate"
              caption="Permutation importance on the validation window. A high bar means the input changed predictions. It does not prove that input caused yield."
            >
              {data.feature_importance?.length ? (
                <ImportanceChart data={data.feature_importance} />
              ) : (
                <EmptyState title="No importance values" body="Importance is stored with the model metadata." />
              )}
            </ChartCard>
            <ChartCard
              kicker="Validated file"
              title="Mean yield by season"
              caption="Mean of yield_t_ha on the latest validated file. The label on that file decides whether the figure is a farm, a district, or a national series."
            >
              {data.yield_by_season?.length ? (
                <SeasonChart data={data.yield_by_season} />
              ) : (
                <EmptyState title="No season summary" body="The validated file needs a season column and yield_t_ha." />
              )}
            </ChartCard>
            <ChartCard
              kicker="Validated file"
              title="Rainfall against recorded yield"
              caption="Pairs of rainfall_mm and yield_t_ha from the latest validated file. A point is a row in that file, not automatically a Macheke farm."
            >
              {data.rainfall_vs_yield?.length ? (
                <RainChart data={data.rainfall_vs_yield} />
              ) : (
                <EmptyState title="No rainfall pairs" body="The latest validated file has no rainfall and yield columns together." />
              )}
            </ChartCard>
            <section className="border border-ink/15 bg-white p-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-moss">Study limits</p>
              <h2 className="mt-1 font-serif text-xl text-ink">What this desk can and cannot say</h2>
              <ul className="mt-4 space-y-3 text-sm leading-relaxed text-ink/80">
                <li>The served prediction form still uses the registered model and its original inputs.</li>
                <li>National or grid figures must stay labelled at that level. They are not rewritten as Macheke farms.</li>
                <li>An R² of 0.80 was the academic target. R² is not classification accuracy, and the target is unmet when the registry says so.</li>
                <li>Missing soil, fertilizer, or farm yield stays missing. This screen does not fill those gaps.</li>
              </ul>
            </section>
          </section>

          <section className="border border-ink/15 bg-white p-5">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-moss">Estimate log</p>
                <h2 className="font-serif text-2xl text-ink">Latest saved estimates</h2>
              </div>
              <p className="text-xs text-ink/55">Production = estimated t/ha × area ha</p>
            </div>
            <DataTable
              columns={[
                { key: "created_at", label: "When", render: (row) => row.created_at?.slice(0, 16).replace("T", " ") },
                { key: "username", label: "User" },
                { key: "predicted_yield", label: "Estimate t/ha" },
                { key: "farm_area", label: "Area ha" },
                { key: "predicted_production", label: "Production t" },
                { key: "model_version", label: "Model" },
              ]}
              rows={data.recent_predictions}
              empty="No estimates stored."
            />
          </section>

          <section className="flex flex-wrap gap-2">
            <ReportButton label="Export analytics" busy={busy === "analytics"} onClick={() => exportReport("/api/v1/reports/analytics/", "pdf", "analytics")} />
            <ReportButton label="Export model report" busy={busy === "model"} onClick={() => exportReport("/api/v1/reports/model-performance/", "pdf", "model")} />
            <ReportButton label="Export estimates" busy={busy === "predictions"} onClick={() => exportReport("/api/v1/reports/predictions/", "csv", "predictions")} />
          </section>
        </>
      ) : null}
    </div>
  );
}

function Fact({ label, value, note }) {
  return (
    <div className="bg-[#f7f4ec] px-3 py-3">
      <dt className="text-[10px] font-semibold uppercase tracking-[0.14em] text-moss">{label}</dt>
      <dd className="mt-1 font-serif text-lg leading-tight text-ink">{value}</dd>
      <dd className="mt-1 text-xs text-ink/55">{note}</dd>
    </div>
  );
}

function Ledger({ label, value, note }) {
  return (
    <article className="border-b border-ink/10 px-4 py-4 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-moss">{label}</p>
      <p className="mt-2 font-serif text-3xl tracking-tight text-ink">{value ?? "—"}</p>
      <p className="mt-2 text-xs leading-snug text-ink/55">{note}</p>
    </article>
  );
}

function ChartCard({ kicker, title, caption, children }) {
  return (
    <section className="border border-ink/15 bg-white p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-moss">{kicker}</p>
      <h2 className="mt-1 font-serif text-xl text-ink">{title}</h2>
      <div className="mt-4">{children}</div>
      <p className="mt-3 text-xs leading-relaxed text-ink/60">{caption}</p>
    </section>
  );
}
