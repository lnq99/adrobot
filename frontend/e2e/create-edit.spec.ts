import { test, expect, type Page } from "@playwright/test";

// Injects a fixed on-screen caption banner into the page so the recorded
// video narrates what is happening in each step.
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

// End-to-end browser test of the full Part 1 + Part 2 flow, driven through the
// real SPA against a demo backend (FakeKeitaro + SQLite, USE_FAKE_KEITARO=1).
// Records video (see playwright.config.ts).
test("create campaign and edit stream offers", async ({ page }) => {
  // ── Part 1: Create tab ──────────────────────────────────────────────────────
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Create campaign" })).toBeVisible();

  await caption(page, "Part 1 — Create a campaign: name, target country, and an offer");

  // Name
  await page.getByRole("textbox", { name: "Name", exact: true }).fill("e2e_test_campaign");

  // Country multi-select
  await page.getByRole("listbox").selectOption({ value: "GM" });

  // Offer picker: search 18001 and pick it
  await page.getByPlaceholder("offer id or name").fill("18001");
  await page.getByRole("button", { name: "Search" }).click();
  await page
    .getByRole("listitem")
    .filter({ hasText: "18001" })
    .getByRole("button", { name: "pick" })
    .click();
  await expect(page.getByText("Offer: 18001")).toBeVisible();

  // Submit (the second "Create" — the first is the tab button)
  await page.getByRole("button", { name: "Create" }).nth(1).click();
  await expect(page.getByText(/Created campaign #\d+/)).toBeVisible({ timeout: 10_000 });

  await caption(page, "Keitaro campaign created with 2 streams (geo→Google + offer)");
  await page.waitForTimeout(1200); // let the success message read on-camera

  // ── Part 2: Editor tab ──────────────────────────────────────────────────────
  await page.getByRole("button", { name: "Editor" }).click();
  await expect(page.getByRole("heading", { name: "Editor" })).toBeVisible();

  await caption(page, "Part 2 — Editor: selecting the campaign and fetching its streams");

  // Campaign dropdown: option 0 is the "pick a campaign" placeholder, so the
  // first real campaign is index 1.
  const dropdown = page.getByRole("combobox");
  await expect(
    dropdown.locator("option", { hasText: /e2e_test_campaign/ })
  ).toHaveCount(1, { timeout: 5_000 });
  await dropdown.selectOption({ index: 1 });

  // Fetch streams from the demo backend
  await page.getByRole("button", { name: "Fetch Streams" }).click();
  await expect(page.getByText(/Stream #\d+/).first()).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole("cell", { name: "18001" })).toBeVisible();

  // The offers stream card (the one with the Push button)
  const streamCard = page
    .locator("div")
    .filter({ has: page.getByRole("button", { name: "Push to Keitaro" }) })
    .first();

  await caption(page, "Part 2 — Editor: add a 2nd offer → weights auto-rebalance to 50/50");

  // Add a second offer (18002) → shares rebalance to 50/50
  await streamCard.getByPlaceholder("offer id or name").fill("18002");
  await streamCard.getByRole("button", { name: "Search" }).click();
  await streamCard
    .getByRole("listitem")
    .filter({ hasText: "18002" })
    .getByRole("button", { name: "pick" })
    .click();
  await expect(page.getByRole("cell", { name: "18002" })).toBeVisible({ timeout: 5_000 });
  await expect(streamCard.locator("tbody tr")).toHaveCount(2, { timeout: 5_000 });
  await expect(streamCard.getByText("Total: 100%")).toBeVisible();
  const shareCells = streamCard.locator("tbody td").filter({ hasText: /^\d+%$/ });
  await expect(shareCells.first()).toContainText("50%");
  await page.waitForTimeout(1500); // linger on the 50/50 rebalance

  await caption(page, "Pin offer 18001 at 40% → the rest fills to 100%");

  // Pin offer 18001 and set its share to 40 (others fill the rest)
  await streamCard
    .getByRole("row")
    .filter({ hasText: "18001" })
    .getByRole("button", { name: "Pin" })
    .click();
  const pinInput = streamCard
    .getByRole("row")
    .filter({ hasText: "18001" })
    .getByRole("spinbutton");
  await expect(pinInput).toBeVisible();
  await pinInput.fill("40");
  await pinInput.dispatchEvent("change");
  await page.waitForTimeout(1500); // show the pinned 40 / rebalanced split

  await caption(page, "Push to Keitaro → draft published (no longer 'unpublished')");

  // Push → stream is no longer unpublished
  await streamCard.getByRole("button", { name: "Push to Keitaro" }).click();
  await expect(streamCard.getByText("(unpublished)")).not.toBeVisible({ timeout: 5_000 });
  await page.waitForTimeout(1500); // hold on the published (not-yellow) end state
});
