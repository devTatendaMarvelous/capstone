import api from "./api";

export async function login(username, password) {
  const response = await api.post("/api/v1/auth/token/", { username, password });
  localStorage.setItem("smartcrop_access", response.data.access);
  localStorage.setItem("smartcrop_refresh", response.data.refresh);
  localStorage.setItem("smartcrop_user", JSON.stringify(response.data.user));
  return response.data.user;
}

export async function register(payload) {
  const response = await api.post("/api/v1/auth/register/", payload);
  return response.data;
}

export async function currentUser() {
  const response = await api.get("/api/v1/auth/me/");
  localStorage.setItem("smartcrop_user", JSON.stringify(response.data));
  return response.data;
}

export function logout() {
  localStorage.removeItem("smartcrop_access");
  localStorage.removeItem("smartcrop_refresh");
  localStorage.removeItem("smartcrop_user");
}

export function storedUser() {
  const raw = localStorage.getItem("smartcrop_user");
  return raw ? JSON.parse(raw) : null;
}
