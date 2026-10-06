import api, { unwrapList } from "./api";

export async function listModels() {
  const response = await api.get("/api/v1/models/");
  return unwrapList(response.data);
}

export async function activateModel(id) {
  const response = await api.post(`/api/v1/models/${id}/activate/`);
  return response.data;
}
