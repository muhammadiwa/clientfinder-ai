# Open Follow-ups

Items that need follow-up after the Sprint 1+2+3A+3B+3C work.
Captured in the wrap-up commit `cbecbfc` (2026-06-14).

## Frontend build: re-enable strict typecheck ✅ DONE (2026-06-14)

The 5 type fields documented in this section were all added in
this PR. Strict typecheck is re-enabled: `tsc -b && vite build`
runs clean in the docker build as of 2026-06-14.

### Original 5 issues (all fixed)

- ✅ `MessageListResponse` — imported from `@/types` in `outreach.ts`
- ✅ `Sequence.step_count` — added to the `Sequence` interface in `@/types`
- ✅ `SequenceTimeSeries` — imported from `@/api/outreach` in `useOutreach.ts`
- ✅ `Hook.confidence` — added as `number | null` to the `Hook` type
- ✅ `LeadScore.pain_severity` (+ all breakdown fields) — full
  9-factor breakdown added to the `LeadScore` type

### Bonus downstream fixes (uncovered while re-enabling strict tsc -b)

- ✅ `SequenceChannel` type added as `MessageChannel | "auto"`
- ✅ `SequenceStep.category` field added
- ✅ `TechStack` type expanded with `issues`, `hosting_provider`
- ✅ `MessageStatus` import added to `useOutreach.ts`
- ✅ `MessageChannel` import added to `outreach.ts`
- ✅ `HookCard` prop type uses the full `Hook` type (was an
  inline subset with a `confience` typo — missing the 'a')
- ✅ `prospectHooks` state in `Outreach.tsx` uses `Hook[]`
  directly (was an inline subset with the same `confience` typo)
- ✅ `prospect.tier_confidence` null handling on `TierBadge`
- ✅ `hook.confidence ?? 0` null handling in the hook card display

## Operational gaps (post-90% brief alignment)

Out-of-scope items the user asked about at session wrap-up
(reply tracking, source quality widget, etc.). These close
the last 5-10% of brief alignment:

- **Outreach reply tracking** (2-3 days) — close the
  outreach loop; currently tracks sent/delivered but
  not reply status from email providers (postmark webhook)
  + WAHA callback. Highest strategic value.
- **Source quality dashboard widget** (1-2 days) — leverage
  the 3C source diversification. Per-source noise %,
  success rate, conversion.
- **Outreach funnel widget** (1 day) — sent → delivered →
  opened → clicked → replied. Visual feedback on outreach
  health.
- **Rate limiting per-IP + per-user** (0.5 day) — use
  `slowapi`. Quick win before scaling.
- **Retry policies for external APIs** (0.5 day) — Places,
  Yelp calls. Resilience.
- **Cursor-based pagination for prospects** (1 day) —
  scale past 10k prospects.
- **Backfill tier for pre-Sprint-3B prospects** (0.5 day) —
  complete the data.

## Production deploy (separate track)

Not in v1 scope but operators asked about them:

- Auth: SSO (Google Workspace) + RBAC (admin/operator/viewer)
- Billing/quota tracking (LLM tokens, API calls per workspace)
- Multi-tenant workspace isolation

## Tools / infra

- **vitest setup for unit testing components** — frontend
  has no unit test runner. If a future sprint needs unit-level
  coverage: `npm install -D vitest @testing-library/react`
  + a `test` script.
