import { useEffect, useState } from "react";
import DataTable from "../components/DataTable";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import MetricCard from "../components/MetricCard";
import api, { errorMessage, unwrapList } from "../services/api";
import { getOverview } from "../services/analyticsService";

export default function AdminPage() {
  const [overview, setOverview] = useState(null);
  const [users, setUsers] = useState([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([getOverview(), api.get("/api/v1/auth/users/")])
      .then(([data, userResponse]) => {
        setOverview(data);
        setUsers(unwrapList(userResponse.data));
      })
      .catch((error) => setMessage(errorMessage(error)));
  }, []);

  if (!overview && !message) return <LoadingState />;

  return (
    <div className="space-y-6">
      <header>
        <p className="page-kicker">Administration</p>
        <h1 className="page-title">Overview</h1>
      </header>
      <ErrorState message={message} />
      {overview ? (
        <section className="grid gap-4 sm:grid-cols-3">
          <MetricCard label="Users" value={overview.total_users} />
          <MetricCard label="Dataset versions" value={overview.total_datasets} />
          <MetricCard label="Predictions" value={overview.total_predictions} />
        </section>
      ) : null}
      <section className="panel">
        <h2 className="mb-2 font-serif text-2xl text-ink">Users</h2>
        <DataTable
          columns={[
            { key: "username", label: "Username" },
            { key: "email", label: "Email" },
            { key: "role", label: "Role" },
          ]}
          rows={users}
          empty="No users returned."
        />
      </section>
    </div>
  );
}
