import api from "./api";

export async function getOverview() {
  const response = await api.get("/api/v1/analytics/overview/");
  return response.data;
}
