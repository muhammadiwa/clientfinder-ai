/**
 * i18n index — useT() hook + getT() function for translations.
 *
 * T8.5++++++: the final evolution. After the TDZ fix in
 * PR #80 (which kept the Proxy but eliminated the
 * problematic const), this PR removes the Proxy entirely.
 *
 * Two ways to access translations:
 *
 * 1. In React components (recommended):
 *      import { useT } from "@/i18n";
 *      export function MyComponent() {
 *        const t = useT();   // subscribes to locale changes
 *        return <h1>{t.outreach.title}</h1>;
 *      }
 *
 * 2. Anywhere (module-level constants, helpers, etc):
 *      import { getT } from "@/i18n";
 *      const label = getT().outreach.title;
 *    Note: getT() does NOT subscribe to locale changes. For
 *    module-level t.* usages that should react to locale
 *    changes, wrap them in a component or hook.
 *
 * Benefits over the Proxy:
 *   - No more circular import risk (the Proxy was
 *     fragile to it — see PR #80)
 *   - No TDZ access patterns
 *   - Re-render is explicit (component subscribes to the
 *     locale via the zustand store; re-renders on toggle)
 *   - TypeScript catches missing keys at compile time
 *   - Easier to debug (no Proxy magic)
 */
import { useLocaleStore, type Locale } from "@/stores/locale";
import id from "./id";
import en from "./en";

type IdStrings = typeof id;


const PACKS: Record<Locale, IdStrings> = {
  id: id as IdStrings,
  en: en as unknown as IdStrings,
};

/**
 * Get the current locale's STRINGS object.
 * Synchronous, does not subscribe. Use in module-level
 * code or non-React contexts.
 */
export function getT(): IdStrings {
  const locale = useLocaleStore.getState().locale;
  return PACKS[locale] ?? PACKS.id;
}

/**
 * useT — React hook version. Subscribes to the zustand
 * locale store so the component re-renders on locale
 * change. Use in React components.
 */
export function useT(): IdStrings {
  const locale = useLocaleStore((s) => s.locale);
  return PACKS[locale] ?? PACKS.id;
}

export { useLocaleStore };
export type { Locale };
