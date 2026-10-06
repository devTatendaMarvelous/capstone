import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import AppLayout from "./layouts/AppLayout";
import LoadingState from "./components/LoadingState";
import AdminPage from "./pages/Admin";
import AnalyticsPage from "./pages/Analytics";
import DashboardPage from "./pages/Dashboard";
import DatasetsPage from "./pages/Datasets";
import LoginPage from "./pages/Login";
import ModelsPage from "./pages/Models";
import PredictionPage from "./pages/Prediction";
import PredictionHistoryPage from "./pages/PredictionHistory";
import ProfilePage from "./pages/Profile";
import RegisterPage from "./pages/Register";
import ReportsPage from "./pages/Reports";

function Protected({ children, roles }) {
  const { user, ready } = useAuth();
  if (!ready) return <LoadingState />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        element={
          <Protected>
            <AppLayout />
          </Protected>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="predict" element={<PredictionPage />} />
        <Route path="history" element={<PredictionHistoryPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="datasets" element={<DatasetsPage />} />
        <Route path="models" element={<ModelsPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="admin" element={<Protected roles={["admin"]}><AdminPage /></Protected>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
