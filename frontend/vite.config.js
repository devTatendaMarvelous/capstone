import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiOrigin = process.env.SMARTCROP_API || "http://127.0.0.1:8000";
const webPort = Number(process.env.SMARTCROP_WEB_PORT || 5173);

export default defineConfig({
  plugins: [react()],
  server: {
    port: webPort,
    strictPort: true,
    proxy: {
      "/api": apiOrigin,
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
  },
});
