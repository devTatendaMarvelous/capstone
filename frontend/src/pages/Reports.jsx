import { useState } from "react";
import ErrorState from "../components/ErrorState";
import ReportButton from "../components/ReportButton";
import { errorMessage } from "../services/api";
import { downloadReport } from "../services/reportService";

const REPORTS = [
  ["Prediction report", "/api/v1/reports/predictions/"],
  ["Model performance report", "/api/v1/reports/model-performance/"],
  ["Dataset report", "/api/v1/reports/dataset/"],
  ["Analytics report", "/api/v1/reports/analytics/"],
];

export default function ReportsPage() {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");

  async function run(path, format, key) {
    setBusy(key);
    setMessage("");
    try {
      await downloadReport(path, format);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setBusy("");
    }
  }

  return (
    <section>
      <p className="page-kicker">Downloads</p>
      <h1 className="page-title">Reports</h1>
      <p className="mt-2 max-w-2xl text-sm text-ink/65">
        Files are built on the server from stored predictions, the model registry, and the latest dataset. View opens a PDF. Excel and CSV download directly.
      </p>
      <ErrorState message={message} />
      <div className="mt-6 space-y-4">
        {REPORTS.map(([label, path]) => (
          <article key={path} className="panel flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="font-serif text-xl text-ink">{label}</h2>
            <div className="flex flex-wrap gap-2">
              <ReportButton label="View" busy={busy === `${path}-pdf`} onClick={() => run(path, "pdf", `${path}-pdf`)} />
              <ReportButton label="Download Excel" busy={busy === `${path}-xlsx`} onClick={() => run(path, "xlsx", `${path}-xlsx`)} />
              <ReportButton label="Download CSV" busy={busy === `${path}-csv`} onClick={() => run(path, "csv", `${path}-csv`)} />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
