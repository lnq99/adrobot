// Interactive capture of the Keitaro admin login session for the dual recording.
// Opens a real browser, you log in via GitHub, then press Enter in THIS terminal
// to save the session. Saving is triggered by the keypress (not by how you close
// the window), so it can't be missed.
//
//   npm run e2e:auth
//
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const OUT = "e2e/.auth/keitaro.json";
const URL = "https://keitaro-for-tests.etolegko.com/admin/#!/campaigns/";

const browser = await chromium.launch({ headless: false });
const context = await browser.newContext({ viewport: { width: 1100, height: 900 } });
const page = await context.newPage();
await page.goto(URL).catch(() => {});

console.log("\n" + "─".repeat(70));
console.log("  A browser window opened on the Keitaro admin login.");
console.log("  1) Click « Войти через GitHub » and complete the GitHub login.");
console.log("  2) Make sure you land on the CAMPAIGNS LIST (not the login page).");
console.log("  3) Come back here and press ENTER to save the session.");
console.log("─".repeat(70) + "\n");

await new Promise((resolve) => {
  process.stdin.resume();
  process.stdin.once("data", () => resolve());
});

// Sanity: warn if the current page still looks like the login screen.
const hasLogin = await page.locator("input[type=password]").count().catch(() => 0);
const loginText = (await page.locator("body").innerText().catch(() => "")).includes("Войти через GitHub");
if (hasLogin || loginText) {
  console.log(
    "\n⚠️  The page still shows the login screen — you may not be logged in.\n" +
      "   Saving anyway, but if the recording's right pane shows the login page,\n" +
      "   re-run `npm run e2e:auth` and finish the login before pressing Enter.\n",
  );
}

fs.mkdirSync(path.dirname(OUT), { recursive: true });
await context.storageState({ path: OUT });
const st = JSON.parse(fs.readFileSync(OUT, "utf8"));
console.log(
  `\n✅ Saved ${OUT}  (cookies: ${(st.cookies || []).length}, ` +
    `storage origins: ${(st.origins || []).length})\n`,
);

await browser.close();
process.exit(0);
