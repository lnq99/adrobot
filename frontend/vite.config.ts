import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// base must match the repo name for GitHub Pages project sites
export default defineConfig({
  plugins: [tailwindcss(), react()],
  base: process.env.VITE_BASE ?? "/adrobot/",
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
});
