import api, { unwrapList } from "./api";

export async function createPrediction(payload) {
  const response = await api.post("/api/v1/predictions/", payload);
  return response.data;
}

export async function listPredictions() {
  const response = await api.get("/api/v1/predictions/");
  return unwrapList(response.data);
}

export async function validateLocation(payload) {
  const response = await api.post("/api/v1/location/validate/", payload);
  return response.data;
}

export async function previewEnvironmentalData(payload) {
  const response = await api.post("/api/v1/environmental-data/preview/", payload);
  return response.data;
}
