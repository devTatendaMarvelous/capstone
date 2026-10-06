import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import App from "../App";
import ErrorState from "../components/ErrorState";
import PredictionForm from "../components/PredictionForm";
import { AuthProvider } from "../hooks/useAuth";
import DashboardPage from "../pages/Dashboard";
import AppLayout from "../layouts/AppLayout";
import { Route, Routes } from "react-router-dom";

vi.mock("../services/analyticsService", () => ({
  getOverview: vi.fn(async () => ({
    total_predictions: 4,
    average_predicted_yield: 1.8,
    active_model: { name: "smartcrop_maize_yield", version: "1.0.0", algorithm: "Random Forest Regressor" },
    model_r2: 0.47,
    dataset_records: 938,
    predictions_over_time: [],
    yield_distribution: [],
    feature_importance: [{ rank: 1, feature: "fertilizer_kg_ha", importance_mean: 0.4 }],
    yield_by_season: [],
    rainfall_vs_yield: [],
    recent_predictions: [],
  })),
}));

describe("PredictionForm", () => {
  it("reports empty numeric inputs", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PredictionForm onSubmit={onSubmit} busy={false} />);
    await user.click(screen.getByRole("button", { name: "Estimate yield" }));
    expect(onSubmit).toHaveBeenCalled();
    const errors = onSubmit.mock.calls[0][1];
    expect(errors.rainfall_mm).toBeTruthy();
  });
});

describe("ErrorState", () => {
  it("shows the API message", () => {
    render(<ErrorState message="Invalid prediction input. rainfall_mm: Value must be between 0 and 2500." />);
    expect(screen.getByRole("alert")).toHaveTextContent("rainfall_mm");
  });
});

describe("protected routes", () => {
  it("sends an anonymous visitor to login", async () => {
    localStorage.clear();
    render(
      <MemoryRouter initialEntries={["/history"]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });
});

describe("Dashboard", () => {
  it("renders metrics returned by the API", async () => {
    localStorage.setItem("smartcrop_user", JSON.stringify({ username: "admin", role: "admin" }));
    render(
      <MemoryRouter>
        <AuthProvider>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByText("4")).toBeInTheDocument();
    expect(screen.getByText("0.47")).toBeInTheDocument();
  });
});
