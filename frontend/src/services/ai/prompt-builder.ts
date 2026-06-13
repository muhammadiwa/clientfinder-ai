/**
 * Prompt builder — constructs prompts for the LLM (T5, A29).
 *
 * These templates match the backend `prompts.py` (server-side
 * version). Kept in sync manually — if you change one, change
 * the other.
 *
 * Templates are in Bahasa Indonesia for Indonesian UMKM audience.
 */

import type { Prospect } from "@/types";

/** Frontend-friendly pain shape (mirrors backend API response). */
export interface PainLike {
  id?: string;
  category?: string;
  severity?: string;
  /** Severity as number (0-100), used by the LLM scoring prompt. */
  severity_score?: number;
  title?: string;
  description?: string;
  evidence_quote?: string;
  source?: string;
  detected_at?: string;
}

/** Frontend-friendly tech stack shape. */
export interface TechLike {
  cms?: string | null;
  framework?: string | null;
  hosting_provider?: string | null;
  has_ssl?: boolean | null;
  page_speed_score?: number | null;
  technologies?: string[];
  issues?: string[];
  audited_at?: string;
}

// --- Hook generation ---

export const HOOK_GENERATION_SYSTEM =
  "Anda adalah sales copywriter senior yang ahli dalam Bahasa Indonesia. " +
  "Anda membantu UMKM owner untuk menulis pesan outreach yang personal, " +
  "ringkas, dan value-driven. Selalu rujuk ke pain point spesifik dan " +
  "industri bisnis. Output HARUS JSON valid.";

export const HOOK_GENERATION_USER_TEMPLATE = `# KONTEKS BISNIS

**Nama**: {company_name}
**Industri**: {industry}
**Lokasi**: {location}
**Website**: {website}

# PAIN POINTS TERDETEKSI

{pains_block}

# TECH STACK / DIGITAL PRESENCE

{tech_block}

# TUGAS

Buat 3 sudut outreach (hooks) yang highly personalized berdasarkan data di atas.
Setiap hook adalah opening line untuk pesan email/WA pertama, dengan struktur:
- "audit_finding": Masalah spesifik yang diobservasi (1 kalimat)
- "hook_text": Opening line (max 280 karakter, casual tapi profesional)
- "recommended_service": Layanan kami yang paling cocok (1-3 kata)
- "confidence": 0.0-1.0, seberapa yakin hook ini akan resonansi

# OUTPUT FORMAT (JSON, TIDAK ADA TEKS LAIN)

{
  "hooks": [
    {
      "audit_finding": "...",
      "hook_text": "...",
      "recommended_service": "...",
      "confidence": 0.0
    }
  ]
}
`;

export interface HookInputContext {
  prospect: Prospect;
  pains: PainLike[];
  tech: TechLike | null;
}

export function buildHookPrompt(ctx: HookInputContext): {
  system: string;
  user: string;
} {
  const { prospect, pains, tech } = ctx;
  const user = HOOK_GENERATION_USER_TEMPLATE.replace(
    "{company_name}",
    prospect.company_name,
  )
    .replace("{industry}", prospect.industry ?? "tidak diketahui")
    .replace("{location}", prospect.location_city ?? "tidak diketahui")
    .replace("{website}", prospect.website ?? "tidak ada")
    .replace("{pains_block}", formatPainsForPrompt(pains))
    .replace("{tech_block}", formatTechForPrompt(tech));
  return { system: HOOK_GENERATION_SYSTEM, user };
}

// --- Pain analysis (richer) ---

export const PAIN_ANALYSIS_SYSTEM =
  "Anda adalah digital marketing analyst untuk UMKM Indonesia. " +
  "Anda ahli dalam mengidentifikasi masalah operasional, digital " +
  "presence, dan growth blockers. Output HARUS JSON valid.";

export const PAIN_ANALYSIS_USER_TEMPLATE = `# PROSPECT

{company_name} ({industry}, {location})
Website: {website}

# DATA YANG SUDAH DIKUMPULKAN

{existing_pains}

# TUGAS

Berdasarkan data di atas, identifikasi 2-4 pain points tambahan yang TIDAK
tertangkap oleh heuristic. Berikan:
- "kind": identifier machine
- "title": judul Bahasa Indonesia
- "description": 1-2 kalimat kenapa ini penting
- "severity": 0-100
- "recommended_service": layanan kami yang cocok

# OUTPUT (JSON only, no prose)

{
  "additional_pains": [
    {"kind": "...", "title": "...", "description": "...", "severity": 0, "recommended_service": "..."}
  ]
}
`;

export function buildPainAnalysisPrompt(
  prospect: Prospect,
  existingPains: PainLike[],
): { system: string; user: string } {
  const user = PAIN_ANALYSIS_USER_TEMPLATE.replace(
    "{company_name}",
    prospect.company_name,
  )
    .replace("{industry}", prospect.industry ?? "?")
    .replace("{location}", prospect.location_city ?? "?")
    .replace("{website}", prospect.website ?? "tidak ada")
    .replace("{existing_pains}", formatPainsForPrompt(existingPains));
  return { system: PAIN_ANALYSIS_SYSTEM, user };
}

// --- Helpers ---

/** Format pain list for inclusion in a prompt. */
export function formatPainsForPrompt(pains: PainLike[]): string {
  if (!pains || pains.length === 0) {
    return "(tidak ada pain points yang terdeteksi)";
  }
  return pains
    .map((p, i) => {
      const sev = p.severity ?? "?";
      const title = p.title ?? p.description?.split("\n")[0] ?? "";
      const desc = p.description ?? "";
      return `${i + 1}. **[${sev}] ${p.category ?? ""}** — ${title}\n   ${desc}`;
    })
    .join("\n\n");
}

/** Format tech stack for inclusion in a prompt. */
export function formatTechForPrompt(tech: TechLike | null): string {
  if (!tech) return "(tidak ada data tech stack)";
  const parts: string[] = [];
  if (tech.cms) parts.push(`- CMS: ${tech.cms}`);
  if (tech.framework) parts.push(`- Framework: ${tech.framework}`);
  if (tech.hosting_provider) parts.push(`- Hosting: ${tech.hosting_provider}`);
  if (tech.has_ssl === true) parts.push("- SSL: ✓ aktif");
  else if (tech.has_ssl === false)
    parts.push("- SSL: ✗ tidak aktif (security risk)");
  if (tech.page_speed_score != null)
    parts.push(`- PageSpeed score: ${tech.page_speed_score}/100`);
  if (tech.issues && tech.issues.length > 0)
    parts.push(`- Issues: ${tech.issues.join(", ")}`);
  return parts.length > 0 ? parts.join("\n") : "(tidak ada info tech stack)";
}

// --- Outbound message generation (T6 prep) ---

export const OUTREACH_SYSTEM =
  "Anda adalah copywriter untuk pesan outreach B2B Indonesia. " +
  "Tulis pesan yang sopan, ringkas, tidak salesy, dan value-driven. " +
  "Bahasa Indonesia yang natural dan profesional.";

export const OUTREACH_EMAIL_TEMPLATE = `# PROSPECT

{company_name}, {industry}, {location}

# HOOK YANG DIPILIH

{hook_text}

# PAIN POINTS

{pains_block}

# TUGAS

Tulis email outreach (subject + body) berdasarkan hook di atas.
- Subject: max 60 karakter, jangan clickbait
- Body: max 150 kata, paragraf pendek, 1 CTA
- Tone: santai tapi profesional (seperti peer yang punya insight)
- Akhiri dengan signature: "Salam,\n[Tim ClientFinder]"

# OUTPUT (JSON only)

{
  "subject": "...",
  "body": "..."
}
`;

export function buildOutreachEmailPrompt(
  prospect: Prospect,
  hookText: string,
  pains: PainLike[],
): { system: string; user: string } {
  const user = OUTREACH_EMAIL_TEMPLATE.replace(
    "{company_name}",
    prospect.company_name,
  )
    .replace("{industry}", prospect.industry ?? "tidak diketahui")
    .replace("{location}", prospect.location_city ?? "tidak diketahui")
    .replace("{hook_text}", hookText)
    .replace("{pains_block}", formatPainsForPrompt(pains));
  return { system: OUTREACH_SYSTEM, user };
}
