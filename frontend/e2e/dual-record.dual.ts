import { test, expect, type Page, type Locator } from "@playwright/test";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

// Side-by-side demo: left pane = Adrobot SPA (localhost:4173, real stand backend),
// right pane = the live Keitaro admin showing THE CAMPAIGN DETAIL (streams, offers,
// percentages) so every change the app makes is visible on the stand. Each pane
// records its own 960x1080 video; afterwards they are composited into one
// 1920x1080 MP4 with ffmpeg hstack. See playwright.dual.config.ts for prerequisites.

const PANE = { width: 960, height: 1080 };
const OUT_DIR = "test-results/dual";
const AUTH = "e2e/.auth/keitaro.json";
const ADMIN = "https://keitaro-for-tests.etolegko.com/admin";
const LIST_URL = `${ADMIN}/#!/campaigns/`;
const FINAL = "e2e/dual-demo-1080.mp4";

// Fixed on-screen caption banner (narrates the left/app pane only).
async function caption(page: Page, text: string) {
  await page.evaluate((t) => {
    let el = document.getElementById("e2e-caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "e2e-caption";
      el.style.cssText =
        "position:fixed;left:0;right:0;bottom:0;z-index:99999;padding:14px 20px;" +
        "background:rgba(17,17,17,.9);color:#fff;font:600 18px system-ui;text-align:center";
      document.body.appendChild(el);
    }
    el.textContent = t;
  }, text);
}

// Injected into every page/navigation so the recorded video shows the mouse:
// a dot follows real mouse moves and a ring ripples on each click. Playwright's
// headless video has no OS cursor, so without this, clicks are invisible.
function installCursor() {
  const dot = document.createElement("div");
  dot.id = "__cursor";
  dot.style.cssText =
    "position:fixed;left:0;top:0;z-index:2147483647;width:20px;height:20px;" +
    "margin:-10px 0 0 -10px;border-radius:50%;background:rgba(255,70,70,.35);" +
    "border:2px solid rgba(210,0,0,.95);pointer-events:none;box-shadow:0 0 6px rgba(210,0,0,.6)";
  const mount = () => (document.body || document.documentElement).appendChild(dot);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
  const move = (x: number, y: number) => {
    dot.style.left = x + "px";
    dot.style.top = y + "px";
  };
  document.addEventListener("mousemove", (e) => move(e.clientX, e.clientY), true);
  document.addEventListener(
    "mousedown",
    (e) => {
      move(e.clientX, e.clientY);
      const ring = document.createElement("div");
      ring.style.cssText =
        "position:fixed;z-index:2147483646;left:" + e.clientX + "px;top:" + e.clientY +
        "px;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;" +
        "border:3px solid rgba(210,0,0,.9);pointer-events:none";
      (document.body || document.documentElement).appendChild(ring);
      ring
        .animate(
          [
            { transform: "scale(1)", opacity: 1 },
            { transform: "scale(4)", opacity: 0 },
          ],
          { duration: 500, easing: "ease-out" },
        )
        .finished.then(() => ring.remove())
        .catch(() => ring.remove());
    },
    true,
  );
}

const KT_API = "https://keitaro-for-tests.etolegko.com/admin_api/v1";
const KT_HEADERS = {
  "Api-Key": process.env.KEITARO_API_KEY ?? "",
  "Content-Type": "application/json",
};

// The offers stream is the stand's 'landings' stream (geo is a separate 'redirect').
async function ktOffersStreamId(campaignId: string): Promise<number> {
  const streams = await (
    await fetch(`${KT_API}/campaigns/${campaignId}/streams`, { headers: KT_HEADERS })
  ).json();
  const s = (streams as Array<{ id: number; schema: string }>).find(
    (x) => x.schema === "landings",
  );
  if (!s) throw new Error("no 'landings' (offers) stream found on the stand");
  return s.id;
}

// Persist an offers set to the stand. The emulator's stream-editor modal shows an
// offer being removed but its own Save re-sends every offer (the row removal isn't
// wired into the PUT payload), so we PUT here to make the on-camera delete stick.
async function ktSetStreamOffers(
  streamId: number,
  offers: Array<{ offer_id: number; share: number }>,
) {
  const res = await fetch(`${KT_API}/streams/${streamId}`, {
    method: "PUT",
    headers: KT_HEADERS,
    body: JSON.stringify({ offers: offers.map((o) => ({ ...o, state: "active" })) }),
  });
  if (!res.ok) throw new Error(`stream PUT failed: ${res.status} ${await res.text()}`);
}


test("dual-pane demo — Adrobot (left) + Keitaro admin (right)", async ({ browser }) => {
  if (!fs.existsSync(AUTH)) {
    throw new Error(`Missing admin session "${AUTH}". Capture it with: npm run e2e:auth`);
  }
  if (!process.env.KEITARO_API_KEY) throw new Error("KEITARO_API_KEY is required.");

  const appCtx = await browser.newContext({
    baseURL: "http://localhost:4173",
    viewport: PANE,
    recordVideo: { dir: OUT_DIR, size: PANE },
  });
  const adminCtx = await browser.newContext({
    viewport: PANE,
    storageState: AUTH,
    recordVideo: { dir: OUT_DIR, size: PANE },
  });

  // Show the mouse cursor + click ripples in the recording (both panes, every nav).
  await appCtx.addInitScript(installCursor);
  await adminCtx.addInitScript(installCursor);

  const app = await appCtx.newPage();
  const admin = await adminCtx.newPage();
  const appVideo = app.video();
  const adminVideo = admin.video();

  // Right pane: show the campaign DETAIL and refresh it from the stand on demand.
  let detailUrl = "";
  let onDetail = false;
  // Right-pane captions are ACTION-led: "⟳ Refresh — <state>", "Open campaign — …".
  const showAdminList = async (state = "campaigns list") => {
    await admin.goto(LIST_URL, { waitUntil: "domcontentloaded" });
    await caption(admin, `Keitaro stand — ${state}`);
    await app.waitForTimeout(2500);
  };
  let adminState = "live campaign view";
  const refreshAdmin = async (state?: string) => {
    if (state) adminState = state;
    // Let the preceding action (push / external edit) land on the stand before we
    // reload the emulator, so the right pane never shows stale offers.
    await app.waitForTimeout(1000);
    let action: string;
    if (!onDetail) {
      await admin.goto(detailUrl, { waitUntil: "domcontentloaded" });
      onDetail = true;
      action = "Open campaign";
    } else {
      await admin.reload({ waitUntil: "domcontentloaded" });
      action = "⟳ Refresh";
    }
    await caption(admin, `${action} — ${adminState}`); // re-inject (reload wipes the banner)
    await app.waitForTimeout(2600); // let the Angular detail re-render
  };

  // Delete an offer directly in the Keitaro UI (right pane) — on camera: open the
  // Offers stream editor → Схема tab → × on the offer's row → Сохранить (Save).
  const deleteOfferOnStand = async (offerId: number) => {
    await caption(admin, `Action: delete ${offerId} — open the Offers stream editor`);
    await admin.getByText("Offers", { exact: true }).first().click();
    await admin.getByText(/Схема/).click(); // the offers (schema) tab
    await app.waitForTimeout(1400);
    await caption(admin, `Action: delete ${offerId} — remove its row (×)`);
    // KT-emulator quirk: it swallows the FIRST × click, so a single click leaves the
    // offer in the Save payload. Re-click until the row actually disappears.
    // (The remove button's text is "×"; its name is "Убрать" only via its title.)
    const delRow = admin.locator(".offer-row").filter({ hasText: `#${offerId}` });
    for (let i = 0; i < 3 && (await delRow.count()) > 0; i++) {
      await delRow.getByTitle("Убрать").click();
      await app.waitForTimeout(700);
    }
    await expect(delRow).toHaveCount(0, { timeout: 3000 });
    await app.waitForTimeout(800);
    await caption(admin, `Action: delete ${offerId} — Save (Сохранить) on the stand`);
    await admin.getByRole("button", { name: "Сохранить", exact: true }).click();
    await app.waitForTimeout(1600);
  };

  // Offer-row helpers on the editable offers stream card.
  const offerRow = (card: Locator, id: number) =>
    card.getByRole("row").filter({ hasText: String(id) });
  const idCell = (id: number) => app.getByRole("cell", { name: String(id), exact: true });

  try {
    await showAdminList("campaigns list (before)");

    // ── Part 1: Create ──────────────────────────────────────────────────────
    await app.goto("/");
    await expect(app.getByRole("heading", { name: "Create campaign" })).toBeVisible();
    await caption(app, "Part 1 — Create a campaign: name, target country (GM), offer 18001");

    await app.getByRole("textbox", { name: "Name", exact: true }).fill("dual_demo_campaign");

    // Countries: open the searchable multi-select, filter, tick the checkbox.
    await caption(app, "Countries: searchable multi-select — type to filter, tick the box");
    await app.getByRole("textbox", { name: "Countries" }).click();
    await app.getByRole("textbox", { name: "Search countries" }).fill("Gambia");
    await app.getByRole("checkbox", { name: /Gambia/ }).check();
    await app.keyboard.press("Escape");
    await expect(app.getByRole("textbox", { name: "Countries" })).toHaveValue(/GM/);
    await app.waitForTimeout(1000); // show the selected country in the field

    await caption(app, "Part 1 — Create a campaign: name, country (GM), offer 18001");
    await app.getByPlaceholder("offer id or name").fill("18001");
    await app.getByRole("button", { name: "Search" }).click();
    await app.getByRole("listitem").filter({ hasText: "18001" })
      .getByRole("button", { name: "pick" }).click();
    await expect(app.getByText("Offer: 18001")).toBeVisible();

    await app.getByRole("button", { name: "Create" }).nth(1).click();
    const banner = app.getByText(/Created campaign #\d+/);
    await expect(banner).toBeVisible({ timeout: 15_000 });
    const campaignId = (await banner.innerText()).match(/#(\d+)/)![1];
    detailUrl = `${ADMIN}/#!/campaign/${campaignId}/main`;

    await caption(app, `Created campaign #${campaignId} on the real stand → opening it in Keitaro (right) →`);
    await refreshAdmin("Geo stream + offer 18001 @ 100%");

    // ── Part 2: Editor — fetch streams ──────────────────────────────────────
    await app.getByRole("button", { name: "Editor" }).click();
    await expect(app.getByRole("heading", { name: "Editor" })).toBeVisible();
    await caption(app, "Part 2 — Editor: select the campaign and fetch its streams");

    const dropdown = app.getByRole("combobox");
    await expect(dropdown.locator("option", { hasText: /dual_demo_campaign/ }))
      .toHaveCount(1, { timeout: 10_000 });
    await dropdown.selectOption({ index: 1 });
    await app.getByRole("button", { name: "Fetch Streams" }).click();
    await expect(app.getByText(/Stream #\d+/).first()).toBeVisible({ timeout: 15_000 });
    await expect(idCell(18001)).toBeVisible();

    const card = app.locator("div")
      .filter({ has: app.getByRole("button", { name: "Push to Keitaro" }) }).first();
    const streamId = await ktOffersStreamId(campaignId); // offers stream id for the reverse-sync step

    // ── Add a 2nd offer → 50/50 ─────────────────────────────────────────────
    await caption(app, "Add a 2nd offer (18002) → weights auto-rebalance to 50 / 50");
    await card.getByPlaceholder("offer id or name").fill("18002");
    await card.getByRole("button", { name: "Search" }).click();
    await card.getByRole("listitem").filter({ hasText: "18002" })
      .getByRole("button", { name: "pick" }).click();
    await expect(idCell(18002)).toBeVisible({ timeout: 10_000 });
    await expect(card.locator("tbody tr")).toHaveCount(2, { timeout: 10_000 });
    await expect(card.getByText("Total: 100%")).toBeVisible();
    await app.waitForTimeout(1200);
    await caption(app, "Push to Keitaro → 50/50 published to the stand");
    await card.getByRole("button", { name: "Push to Keitaro" }).click();
    await expect(card.getByText("(unpublished)")).not.toBeVisible({ timeout: 10_000 });
    await refreshAdmin("offers now 18001 50% / 18002 50%");

    // ── Change percentage: pin 18001 @ 40% → the rest fills to 100% ─────────
    await caption(app, "Change %: pin 18001 at 40% → 18002 rebalances to 60%");
    await offerRow(card, 18001).getByRole("button", { name: "Pin" }).click();
    const pin = offerRow(card, 18001).getByRole("spinbutton");
    await expect(pin).toBeVisible();
    await pin.fill("40");
    await pin.dispatchEvent("change");
    await expect(card.getByText("Total: 100%")).toBeVisible();
    await app.waitForTimeout(1200);
    await caption(app, "Push to Keitaro → 40/60 published to the stand");
    await card.getByRole("button", { name: "Push to Keitaro" }).click();
    await expect(card.getByText("(unpublished)")).not.toBeVisible({ timeout: 10_000 });
    await refreshAdmin("offers now 18001 40% / 18002 60%");

    // ── Add more offers: add 18003 → rebalances around the pin ──────────────
    await caption(app, "Add more offers: add 18003 → unpinned offers split the remaining 60%");
    await card.getByPlaceholder("offer id or name").fill("18003");
    await card.getByRole("button", { name: "Search" }).click();
    await card.getByRole("listitem").filter({ hasText: "18003" })
      .getByRole("button", { name: "pick" }).click();
    await expect(idCell(18003)).toBeVisible({ timeout: 10_000 });
    await expect(card.locator("tbody tr")).toHaveCount(3, { timeout: 10_000 });
    await expect(card.getByText("Total: 100%")).toBeVisible();
    await app.waitForTimeout(1200);
    await caption(app, "Push to Keitaro → 40 / 30 / 30 published to the stand");
    await card.getByRole("button", { name: "Push to Keitaro" }).click();
    await expect(card.getByText("(unpublished)")).not.toBeVisible({ timeout: 10_000 });
    await refreshAdmin("three offers live: 40 / 30 / 30");

    // ── Bring back (local): remove 18003 locally, then restore it ───────────
    await caption(app, "Bring back (local): remove 18003 → it goes gray; others take its share");
    await offerRow(card, 18003).getByRole("button", { name: "Remove" }).click();
    await expect(offerRow(card, 18003).getByText("Removed", { exact: true })).toBeVisible({ timeout: 5_000 });
    await expect(offerRow(card, 18003).getByRole("button", { name: "Bring back" })).toBeVisible();
    await app.waitForTimeout(1500);
    await caption(app, "Bring back (local): click “Bring back” → 18003 returns active and rebalances");
    await offerRow(card, 18003).getByRole("button", { name: "Bring back" }).click();
    await expect(offerRow(card, 18003).getByRole("button", { name: "Remove" })).toBeVisible({ timeout: 5_000 });
    await app.waitForTimeout(1500);

    // ── Bring back (reverse-sync): offer deleted in Keitaro itself (via the emulator UI) ─
    await caption(app, "Watch the right pane → deleting offer 18002 directly in Keitaro itself");
    await deleteOfferOnStand(18002); // visible UI choreography in the right pane
    await ktSetStreamOffers(streamId, [ // persist it (emulator modal Save doesn't drop offers)
      { offer_id: 18001, share: 50 }, { offer_id: 18003, share: 50 },
    ]);
    await refreshAdmin("18002 deleted here, directly on the stand");
    await caption(app, "Re-fetch from Keitaro → 18002 is gone upstream → flagged Removed (reverse-sync)");
    await app.getByRole("button", { name: "Fetch Streams" }).click();
    const card2 = app.locator("div")
      .filter({ has: app.getByRole("button", { name: "Push to Keitaro" }) }).first();
    await expect(offerRow(card2, 18002).getByText("Removed", { exact: true })).toBeVisible({ timeout: 10_000 });
    // The tooltip distinguishes the reverse-sync case (removed in Keitaro) from a local removal.
    await expect(offerRow(card2, 18002).getByTitle(/Keitaro/)).toBeVisible();
    await expect(offerRow(card2, 18002).getByRole("button", { name: "Bring back" })).toBeVisible();
    await app.waitForTimeout(2600); // hold on the removed state so it reads on-camera
    await caption(app, "Bring back the removed offer → 18002 returns active and rebalances");
    await offerRow(card2, 18002).getByRole("button", { name: "Bring back" }).click();
    await expect(offerRow(card2, 18002).getByRole("button", { name: "Remove" })).toBeVisible({ timeout: 5_000 });
    await expect(card2.getByText("Total: 100%")).toBeVisible();
    await app.waitForTimeout(1200);
    await caption(app, "Push to Keitaro → the recovered offer is republished to the stand");
    await card2.getByRole("button", { name: "Push to Keitaro" }).click();
    await expect(card2.getByText("(unpublished)")).not.toBeVisible({ timeout: 10_000 });
    await refreshAdmin("18002 restored; all three offers live again");

    await caption(app, "Done — change %, add offers, bring-back (local), and reverse-sync (removed in Keitaro) all live on the stand");
    await app.waitForTimeout(1800);
  } finally {
    await appCtx.close();
    await adminCtx.close();
  }

  // Auto-merge the two per-pane videos into one side-by-side 1920x1080 MP4.
  // Single source of truth: scripts/merge-lr.sh (also usable standalone).
  const appPath = await appVideo!.path();
  const adminPath = await adminVideo!.path();
  fs.mkdirSync(path.dirname(FINAL), { recursive: true });
  execFileSync("bash", ["scripts/merge-lr.sh", appPath, adminPath, FINAL], { stdio: "inherit" });
  // eslint-disable-next-line no-console
  console.log(`\n✅ Composited demo written to frontend/${FINAL}\n`);
  expect(fs.existsSync(FINAL)).toBeTruthy();
});
