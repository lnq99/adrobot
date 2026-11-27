import { defineConfig } from "@playwright/test";

// Side-by-side demo recording: left pane drives the Adrobot SPA against the REAL
// Keitaro stand; right pane shows the live Keitaro admin campaigns list so the
// viewer sees the stand react. Each pane is captured separately, then composited
// into a single 1920x1080 video by the spec (see dual-record.dual.ts).
//
// Prerequisites (both are secrets, provided by the operator — never committed):
//   1. KEITARO_API_KEY env var  — the real admin_api Api-Key.
//   2. e2e/.auth/keitaro.json   — a captured admin UI login session
//                                 (run `npm run e2e:auth` once to create it).
if (!process.env.KEITARO_API_KEY) {
  throw new Error(
    "KEITARO_API_KEY is required for the dual recording (real stand). " +
      "Run as: KEITARO_API_KEY=<key> npm run e2e:dual",
  );
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /.*\.dual\.ts/,
  // Panes are created manually in the spec (two contexts), so no global
  // viewport/video here. Give the whole flow generous time.
  timeout: 240_000,
  use: {
    launchOptions: {
      slowMo: Number(process.env.E2E_SLOWMO ?? 900),
    },
  },
  webServer: [
    {
      // Backend against the REAL Keitaro stand. Local app state is a throwaway
      // SQLite file; create its schema out-of-band (startup create_all only runs
      // in fake mode), then launch uvicorn in real mode.
      command:
        "rm -f e2e_dual.db && " +
        "USE_FAKE_KEITARO=0 DATABASE_URL=sqlite:///./e2e_dual.db " +
        '.venv/bin/python -c "import app.models; from app.core.db import Base, engine; Base.metadata.create_all(engine)" && ' +
        "USE_FAKE_KEITARO=0 DATABASE_URL=sqlite:///./e2e_dual.db " +
        ".venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: "../backend",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 20_000,
    },
    {
      command:
        "VITE_API_URL=http://localhost:8000 VITE_BASE=/ npm run build && VITE_BASE=/ npm run preview -- --port 4173 --host --base /",
      url: "http://localhost:4173",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
