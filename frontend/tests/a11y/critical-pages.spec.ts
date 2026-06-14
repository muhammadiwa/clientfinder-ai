import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * a11y helper — logs in + waits for dashboard.
 *
 * The test must be authenticated to reach protected routes
 * (Dashboard, Prospects, Outreach, Analytics).
 */
async function loginAsAdmin(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill("admin@clientfinder.app");
  await page.getByLabel("Password").fill("changeme-admin-password");
  await page.getByRole("button", { name: /masuk|sign in/i }).click();
  // Wait for redirect to dashboard
  await page.waitForURL("**/dashboard", { timeout: 10_000 });
}

/**
 * Run axe-core on the current page. Returns the violations.
 * Filters to "serious" + "critical" only — the ones we MUST fix.
 */
async function getA11yViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  return results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
}

test.describe("WCAG 2.1 AA — critical pages", () => {
  test("Login page has no critical a11y violations", async ({ page }) => {
    await page.goto("/login");
    const violations = await getA11yViolations(page);
    expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
  });

  test("Dashboard has no critical a11y violations", async ({ page }) => {
    await loginAsAdmin(page);
    await page.waitForLoadState("networkidle");
    const violations = await getA11yViolations(page);
    expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
  });

  test("Prospects has no critical a11y violations", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/prospects");
    await page.waitForLoadState("networkidle");
    const violations = await getA11yViolations(page);
    expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
  });

  test("Outreach has no critical a11y violations", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/outreach");
    await page.waitForLoadState("networkidle");
    const violations = await getA11yViolations(page);
    expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
  });

  test("Analytics has no critical a11y violations", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/analytics");
    await page.waitForLoadState("networkidle");
    const violations = await getA11yViolations(page);
    expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
  });
});
