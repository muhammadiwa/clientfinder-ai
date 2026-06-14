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

const STRINGS = { id, en } as const;
type Strings = typeof id;

/**
 * Type-erased locale pack. We cast to a structural
 * shape so the Proxy can serve any key — the runtime
 * fallback chain (locale → id) handles missing keys.
 */
type LocalePack = Record<string, unknown>;

/**
 * Proxy-based t — looks up the current locale from the
 * zustand store on every property access. Falls back to
 * 'id' if the requested key is missing in the active
 * locale (graceful degradation — no broken UI).
 */
export const t = new Proxy(id, {
  get(_target, prop: string) {
    const locale = useLocaleStore.getState().locale;
    const pack: LocalePack = (STRINGS[locale] as unknown as LocalePack)
      ?? (id as unknown as LocalePack);
    return pack[prop] ?? (id as unknown as LocalePack)[prop];
  },
}) as unknown as Strings;

/** Hook version (for components that need to re-render on locale change) */
export function useT(): Strings {
  useLocaleStore((s) => s.locale); // subscribe to changes
  return t;
}

export type Locale = "id" | "en";
export { useLocaleStore };
