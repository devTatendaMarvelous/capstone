import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("smartcrop_access");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && original && !original._retry && !original.url?.includes("/auth/token")) {
      original._retry = true;
      const refresh = localStorage.getItem("smartcrop_refresh");
      if (refresh) {
        try {
          const next = await axios.post(`${api.defaults.baseURL}/api/v1/auth/token/refresh/`, { refresh });
          localStorage.setItem("smartcrop_access", next.data.access);
          original.headers.Authorization = `Bearer ${next.data.access}`;
          return api(original);
        } catch {
          localStorage.removeItem("smartcrop_access");
          localStorage.removeItem("smartcrop_refresh");
          localStorage.removeItem("smartcrop_user");
        }
      }
    }
    return Promise.reject(error);
  },
);

export function errorMessage(error) {
  const data = error?.response?.data;
  if (!data) return "The server could not be reached.";
  if (typeof data === "string") return data;
  const parts = [data.message].filter(Boolean);
  if (data.errors && typeof data.errors === "object") {
    Object.entries(data.errors).forEach(([field, messages]) => {
      const text = Array.isArray(messages) ? messages.join(" ") : String(messages);
      if (text) parts.push(`${field}: ${text}`);
    });
  }
  return parts.join(" ") || "Request failed.";
}

export function unwrapList(data) {
  if (data && Array.isArray(data.results)) return data.results;
  if (Array.isArray(data)) return data;
  return [];
}

export default api;
