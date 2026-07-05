import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts"
  },
  server: {
    allowedHosts: ["localhost", "127.0.0.1", "frontend", "satisfaction_frontend"],
    host: "0.0.0.0",
    port: 5173
  }
});
