/**
 * LanguagePicker — small dropdown to switch between
 * 'id' (Bahasa Indonesia) and 'en' (English).
 *
 * T8.5++++++: language toggle. Lives in the Topbar's
 * user menu. Persists choice to localStorage via the
 * zustand store.
 */
import { Languages, Check } from "lucide-react";

import { useLocaleStore, type Locale } from "@/stores/locale";

const LOCALES: { value: Locale; label: string; flag: string }[] = [
  { value: "id", label: "Bahasa Indonesia", flag: "🇮🇩" },
  { value: "en", label: "English", flag: "🇺🇸" },
];

export function LanguagePicker() {
  const { locale, setLocale } = useLocaleStore();

  return (
    <div className="space-y-1">
      <div className="px-2 py-1.5 flex items-center gap-2">
        <Languages className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
          Bahasa / Language
        </span>
      </div>
      {LOCALES.map((l) => (
        <button
          key={l.value}
          type="button"
          onClick={() => setLocale(l.value)}
          className="w-full flex items-center gap-2.5 px-2 py-1.5 text-sm rounded hover:bg-muted/50 transition-colors text-left"
        >
          <span className="text-base" aria-hidden>
            {l.flag}
          </span>
          <span className="flex-1">{l.label}</span>
          {locale === l.value && (
            <Check className="h-3.5 w-3.5 text-emerald-500" />
          )}
        </button>
      ))}
    </div>
  );
}
