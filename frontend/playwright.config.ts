import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for ClientFinder a11y tests (T8.5+++).
 *
 * Usage:
 *   npm run test:a11y
 *   npm run test:a11y:install   # first-time only
 *
 * Runs axe-core on critical pages to catch a11y regressions.
 */
export default defineConfig({
  testDir: "./tests",
  testMatch: "**/a11y/**/*.spec.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "list" : "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
