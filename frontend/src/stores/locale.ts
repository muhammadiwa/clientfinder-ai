import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Locale store — tracks the user's preferred i18n locale.
 *
 * T8.5++++++: language toggle. R2 says "Indonesia-only"
 * but the user wants to support BOTH 'id' and 'en' so
 * the i18n system is verified end-to-end. 'id' remains
 * the default per R2.
 *
 * Persisted to localStorage as 'cf-locale' so the choice
 * survives page reloads.
 */
export type Locale = "id" | "en";

interface LocaleState {
  locale: Locale;
  setLocale: (l: Locale) => void;
}

export const useLocaleStore = create<LocaleState>()(
  persist(
    (set) => ({
      locale: "id",
      setLocale: (l) => set({ locale: l }),
    }),
    { name: "cf-locale" },
  ),
);
