import api, { unwrapList } from "./api";

export async function listDatasets() {
  const response = await api.get("/api/v1/datasets/");
  return unwrapList(response.data);
}

export async function uploadDataset(formData) {
  const response = await api.post("/api/v1/datasets/upload/", formData);
  return response.data;
}

export async function datasetQuality(id) {
  const response = await api.get(`/api/v1/datasets/${id}/quality/`);
  return response.data;
}
