# Playwright a11y tests

T8.5+++ added @axe-core/playwright to catch a11y regressions
in CI.

## Quick start

```bash
# First time: install Chromium for Playwright
npm run test:a11y:install

# Run all a11y tests
npm run test:a11y
```

## What it checks

`tests/a11y/critical-pages.spec.ts` runs axe-core with
`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` tags on these
critical pages:

- `/login` (unauthenticated)
- `/dashboard` (authenticated)
- `/prospects`
- `/outreach`
- `/analytics`

Only `serious` and `critical` violations fail the test.
`moderate` and `minor` issues are logged but don't fail
the build (they should be tracked separately).

## Why this exists

Manual a11y reviews caught real bugs (missing aria-labels,
low contrast, no focus management). But manual reviews
don't scale — a single PR can regress a11y silently.

axe-core runs in CI on every PR. If anyone introduces a
critical a11y violation, the build fails.

## CI

`.github/workflows/ci.yml` runs `npm run test:a11y` on
every push to develop/main + every PR. Browser dependencies
are installed via `npm run test:a11y:install`.

If the test fails, fix the violation. Don't add
`disable-rules` to bypass it.

## Adding new pages to test

Add a new `test("Page X has no critical a11y violations", ...)`
in `critical-pages.spec.ts` with:

```ts
await page.goto("/your-page");
await page.waitForLoadState("networkidle");
const violations = await getA11yViolations(page);
expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
```

The test will fail on any new serious/critical violation.

## Common violations + fixes

| Violation | Fix |
|---|---|
| `color-contrast` | Increase text/bg contrast to 4.5:1 |
| `label` | Add `<Label htmlFor="x">` to inputs |
| `button-name` | Add `aria-label` to icon-only buttons |
| `link-name` | Add text/aria-label to anchor tags |
| `image-alt` | Add `alt` to `<img>` tags |
| `region` | Wrap page content in `<main>` or `<section>` |
| `document-title` | Set `<title>` in each page |
