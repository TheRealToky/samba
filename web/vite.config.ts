import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev (npm run dev), proxy API calls to the backend so the SPA can use
// same-origin relative URLs (matching the nginx setup used in the container).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
