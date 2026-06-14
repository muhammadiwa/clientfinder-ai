/**
 * i18n index — locale-aware translation getter.
 *
 * T8.5++++++: language toggle. Re-exports `t` as a
 * Proxy that reads from the zustand locale store and
 * returns the right locale's strings.
 *
 * All 200+ call sites in the codebase that do `t.foo.bar`
 * continue to work unchanged — the Proxy intercepts each
 * property access and looks up the right locale.
 *
 * Usage:
 *   import { t } from "@/i18n";   // (no longer from id.ts)
 *   <h1>{t.outreach.title}</h1>   // resolves to current locale
 *
 * To switch locale: useLocaleStore.getState().setLocale('en')
 *   (or click the language picker in the Topbar)
 */
import { useLocaleStore } from "@/stores/locale";
import id from "./id";
import en from "./en";

type LocalePack = Record<string, unknown>;

/**
 * Helper to unwrap a locale module (handles the circular
 * import case where `id` may be a partial module namespace
 * rather than the default export). The default export
 * is what we actually want.
 */
function asPack(mod: unknown): LocalePack {
  const m = mod as { default?: unknown };
  if (m && typeof m === "object" && m.default && typeof m.default === "object") {
    return m.default as LocalePack;
  }
  return (mod as LocalePack) ?? {};
}

/**
 * Proxy-based t — looks up the current locale from the
 * zustand store on every property access. Falls back to
 * 'id' if the requested key is missing in the active
 * locale (graceful degradation — no broken UI).
 *
 * IMPORTANT: no top-level `const STRINGS = ...` here
 * because of the circular import (id.ts re-exports from
 * this file, so when index.ts loads, `id` is still a
 * partial module and any const initialization that
 * references it would throw a TDZ error when later
 * accessed). Instead, the Proxy reads `id` and `en`
 * directly at access time.
 */
export const t = new Proxy(id, {
  get(_target, prop: string) {
    const locale = useLocaleStore.getState().locale;
    const active = locale === "en" ? en : id;
    const activePack = asPack(active);
    const fallbackPack = asPack(id);
    return activePack[prop] ?? fallbackPack[prop];
  },
}) as unknown as typeof id;

/** Hook version (for components that need to re-render on locale change) */
export function useT(): typeof id {
  useLocaleStore((s) => s.locale); // subscribe to changes
  return t;
}

export type Locale = "id" | "en";
export { useLocaleStore };
