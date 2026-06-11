#!/usr/bin/env node
/**
 * Render docs/assets/mock/*.html to PNG screenshots for README.
 * Requires: npx playwright (chromium) — installed on first run.
 */
import { chromium } from "playwright";
import { fileURLToPath } from "url";
import path from "path";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const MOCK = path.join(ROOT, "mock");

const SHOTS = [
  { html: "chat-approval.html", out: "chat-approval.png", width: 1280, height: 800 },
  { html: "goals.html", out: "goals.png", width: 1280, height: 800 },
  { html: "export.html", out: "export.png", width: 1280, height: 720 },
];

const browser = await chromium.launch();
const page = await browser.newPage();

for (const { html, out, width, height } of SHOTS) {
  const file = path.join(MOCK, html);
  const dest = path.join(ROOT, out);
  await page.setViewportSize({ width, height });
  await page.goto(`file://${file}`, { waitUntil: "networkidle" });
  await page.screenshot({ path: dest, type: "png" });
  console.log(`Wrote ${dest}`);
}

await browser.close();
