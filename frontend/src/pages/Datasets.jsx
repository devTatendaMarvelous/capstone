import { useEffect, useState } from "react";
import DataTable from "../components/DataTable";
import DatasetStatus from "../components/DatasetStatus";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import { useAuth } from "../hooks/useAuth";
import { errorMessage } from "../services/api";
import { datasetQuality, listDatasets, uploadDataset } from "../services/datasetService";

export default function DatasetsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState(null);
  const [message, setMessage] = useState("");
  const [quality, setQuality] = useState(null);
  const canUpload = user?.role === "admin" || user?.role === "researcher";

  function refresh() {
    return listDatasets().then(setRows).catch((error) => setMessage(errorMessage(error)));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onUpload(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await uploadDataset(form);
      event.currentTarget.reset();
      setMessage("");
      await refresh();
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  if (!rows && !message) return <LoadingState />;

  return (
    <div className="space-y-6">
      <header>
        <p className="page-kicker">Sources</p>
        <h1 className="page-title">Datasets</h1>
      </header>
      <ErrorState message={message} />
      {canUpload ? (
        <form onSubmit={onUpload} className="panel grid gap-3 sm:grid-cols-2">
          <input name="name" required placeholder="Name" className="input mt-0" />
          <input name="version" required placeholder="Version" className="input mt-0" />
          <input name="source" required placeholder="Source" className="input mt-0" />
          <select name="source_type" className="input mt-0">
            <option value="SYNTHETIC">SYNTHETIC</option>
            <option value="REAL">REAL</option>
            <option value="EXTERNAL">EXTERNAL</option>
          </select>
          <input name="description" placeholder="Description" className="input mt-0 sm:col-span-2" />
          <input name="file" type="file" accept=".csv,.xlsx" required className="text-sm sm:col-span-2" />
          <button type="submit" className="btn-primary sm:col-span-2 sm:w-fit">
            Upload dataset
          </button>
        </form>
      ) : (
        <p className="text-sm text-ink/70">Uploads are limited to researchers and administrators.</p>
      )}
      <div className="panel">
        <DataTable
          columns={[
            { key: "name", label: "Name" },
            { key: "version", label: "Version" },
            { key: "source", label: "Source" },
            { key: "source_type", label: "Type" },
            { key: "record_count", label: "Records" },
            { key: "status", label: "Status", render: (row) => <DatasetStatus status={row.status} /> },
            { key: "uploaded_at", label: "Uploaded", render: (row) => row.uploaded_at?.slice(0, 10) },
            {
              key: "quality",
              label: "Quality",
              render: (row) => (
                <button type="button" className="text-leaf underline" onClick={() => datasetQuality(row.id).then(setQuality).catch((error) => setMessage(errorMessage(error)))}>
                  View
                </button>
              ),
            },
          ]}
          rows={rows || []}
          empty="No datasets uploaded."
        />
      </div>
      {quality ? (
        <aside className="panel bg-mist text-sm">
          <p>Observations: {quality.observations}</p>
          <p>Missing cells: {quality.missing_cells}</p>
          <p>Duplicate rows: {quality.duplicate_rows}</p>
          <p>Invalid values: {quality.invalid_values}</p>
          <p>Feature completeness: {quality.feature_completeness_percent}%</p>
          <p className="mt-2 text-ink/70">{quality.completeness_definition}</p>
        </aside>
      ) : null}
    </div>
  );
}
