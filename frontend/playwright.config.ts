import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: "http://localhost:4173",
    video: "on",
    trace: "on-first-retry",
  },
  webServer: [
    {
      // Backend: demo mode with SQLite — always delete the db so ids start fresh
      command:
        "rm -f e2e_playwright.db && USE_FAKE_KEITARO=1 DATABASE_URL=sqlite:///./e2e_playwright.db ../backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: "../backend",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 20_000,
    },
    {
      // Frontend: build then preview (static, base=/ so preview routes from root)
      command:
        "VITE_API_URL=http://localhost:8000 VITE_BASE=/ npm run build && VITE_BASE=/ npm run preview -- --port 4173 --host --base /",
      url: "http://localhost:4173",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
