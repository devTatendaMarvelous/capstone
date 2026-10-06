import api from "./api";

export async function downloadReport(path, format) {
  const response = await api.get(path, { params: { format }, responseType: "blob" });
  const blob = new Blob([response.data], { type: response.headers["content-type"] });
  const url = URL.createObjectURL(blob);
  if (format === "pdf") {
    window.open(url, "_blank", "noopener");
    return;
  }
  const link = document.createElement("a");
  link.href = url;
  link.download = `smartcrop-report.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
