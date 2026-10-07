import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // MapLibre 6 loads its web worker relative to its own module file; pre-bundling breaks that path.
  optimizeDeps: { exclude: ["maplibre-gl"] },
  // The worker is bundled by Vite (see TileMap) so production builds ship it with its imports.
  worker: { format: "es" },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: { "/api": process.env.API_URL ?? "http://127.0.0.1:8000" },
  },
});
