/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const additionalAllowedHosts = (
  process.env.__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS ?? ""
)
  .split(",")
  .map((host) => host.trim())
  .filter(Boolean);

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    allowedHosts:
      additionalAllowedHosts.length > 0 ? additionalAllowedHosts : undefined,
  },
  esbuild: {
    logOverride: {
      "unsupported-directive": "silent",
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return;
          }

          if (id.includes("@mui")) {
            return "mui";
          }

          if (id.includes("react-router")) {
            return "router";
          }

          if (id.includes("react")) {
            return "react-vendor";
          }

          return "vendor";
        },
      },
    },
  },
  resolve: {
    alias: {
      "react-router-dom": "react-router",
    },
  },
  test: {
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary", "lcov"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/**/*.spec.{ts,tsx}",
        "src/main.tsx",
      ],
    },
  },
});
