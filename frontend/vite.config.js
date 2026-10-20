import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // Preserve the browser's Host so the API can verify same-origin writes.
      "/api": { target: "http://127.0.0.1:8100", changeOrigin: false },
      "/health": { target: "http://127.0.0.1:8100", changeOrigin: false },
      "/ready": { target: "http://127.0.0.1:8100", changeOrigin: false },
      "/login": { target: "http://127.0.0.1:8100", changeOrigin: false },
      "/auth.css": { target: "http://127.0.0.1:8100", changeOrigin: false },
    },
  },
});
