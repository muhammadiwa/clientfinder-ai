/**
 * LLM provider abstraction (frontend).
 *
 * Calls the BACKEND AI endpoints (not Groq/Gemini directly).
 * The backend holds the GROQ_API_KEY / GEMINI_API_KEY — never
 * expose keys in the browser bundle.
 *
 * Pattern:
 *   promptBuilder → llm.complete(...) → backend /api/v1/ai/...
 *   AI logic lives in this layer; backend is a thin proxy.
 */

import { api } from "@/api/client";

// --- Types ---

export type LLMProviderName = "groq" | "gemini" | "template";

export interface LLMRequest {
  /** System prompt (role + constraints) */
  system: string;
  /** User prompt (the actual task) */
  user: string;
  /** 0.0-1.0, lower = more deterministic */
  temperature?: number;
  /** Token cap (1 token ≈ 4 chars in Bahasa Indonesia) */
  maxTokens?: number;
  /** Force JSON-mode response (provider must support) */
  jsonMode?: boolean;
  /** Provider override (otherwise uses default) */
  provider?: LLMProviderName;
  /** Try fallback provider first (e.g. for testing) */
  preferFallback?: boolean;
}

export interface LLMResult {
  content: string;
  provider: LLMProviderName;
  model: string;
  tokensUsed: number;
  error: string | null;
}

export interface LLMProvider {
  name: LLMProviderName;
  model: string;
  complete: (req: LLMRequest) => Promise<LLMResult>;
}

// --- Provider implementations (proxy to backend) ---

class BackendProxyProvider implements LLMProvider {
  name: LLMProviderName;
  model: string;
  private endpoint: string;

  constructor(name: LLMProviderName, model: string, endpoint: string) {
    this.name = name;
    this.model = model;
    this.endpoint = endpoint;
  }

  async complete(req: LLMRequest): Promise<LLMResult> {
    try {
      const { data } = await api.post<{
        content: string;
        provider: LLMProviderName;
        model: string;
        tokens_used: number;
        error: string | null;
      }>(this.endpoint, {
        system: req.system,
        user: req.user,
        temperature: req.temperature ?? 0.3,
        max_tokens: req.maxTokens ?? 2048,
        json_mode: req.jsonMode ?? false,
        provider: req.provider,
        prefer_fallback: req.preferFallback ?? false,
      });
      return {
        content: data.content,
        provider: data.provider,
        model: data.model,
        tokensUsed: data.tokens_used,
        error: data.error,
      };
    } catch (e) {
      return {
        content: "",
        provider: this.name,
        model: this.model,
        tokensUsed: 0,
        error: e instanceof Error ? e.message : "LLM request failed",
      };
    }
  }
}

// --- Provider registry ---

const GROQ_PROVIDER: LLMProvider = new BackendProxyProvider(
  "groq",
  "llama-3.1-70b-versatile",
  "/ai/complete",
);

const GEMINI_PROVIDER: LLMProvider = new BackendProxyProvider(
  "gemini",
  "gemini-1.5-flash",
  "/ai/complete",
);

const TEMPLATE_PROVIDER: LLMProvider = {
  name: "template",
  model: "template-v1",
  async complete(_req: LLMRequest): Promise<LLMResult> {
    // The template provider just returns the prompt as content.
    // The orchestrator (ai-analyzer.ts) interprets this and
    // generates deterministic output.
    return {
      content: "[TEMPLATE_PROVIDER_NOT_USED_DIRECTLY]",
      provider: "template",
      model: "template-v1",
      tokensUsed: 0,
      error: null,
    };
  },
};

export const PROVIDERS: Record<LLMProviderName, LLMProvider> = {
  groq: GROQ_PROVIDER,
  gemini: GEMINI_PROVIDER,
  template: TEMPLATE_PROVIDER,
};

// Touch unused symbols to keep them in the bundle (Vite tree-shaking)
// — they'll be used by /prospects/:id detail page in T5 Group 3.
void PROVIDERS;
void GROQ_PROVIDER;
void GEMINI_PROVIDER;

// --- Public API ---

/**
 * Complete a prompt using the configured LLM provider chain
 * (primary → fallback → template).
 *
 * The chain is implemented on the backend; this just calls it.
 * Returns the LLMResult, never throws (errors in `error` field).
 */
export async function complete(req: LLMRequest): Promise<LLMResult> {
  const provider = req.provider
    ? PROVIDERS[req.provider]
    : PROVIDERS.groq;
  return provider.complete(req);
}

/**
 * Parse JSON from LLM response. Handles ```json code fences
 * and bare JSON. Returns null on parse failure.
 */
export function safeParseJson<T = unknown>(text: string): T | null {
  if (!text) return null;
  // Strip code fences
  const fenceMatch = text.match(
    /```(?:json)?\s*([\s\S]*?)\s*```/,
  );
  const candidate = fenceMatch ? fenceMatch[1] : text.trim();
  // Try to find JSON object/array
  const objStart = candidate.indexOf("{");
  const arrStart = candidate.indexOf("[");
  let start = -1;
  let end = -1;
  if (objStart === -1 && arrStart === -1) return null;
  if (objStart === -1) {
    start = arrStart;
    end = candidate.lastIndexOf("]");
  } else if (arrStart === -1) {
    start = objStart;
    end = candidate.lastIndexOf("}");
  } else if (objStart < arrStart) {
    start = objStart;
    end = candidate.lastIndexOf("}");
  } else {
    start = arrStart;
    end = candidate.lastIndexOf("]");
  }
  if (end <= start) return null;
  try {
    return JSON.parse(candidate.slice(start, end + 1)) as T;
  } catch {
    return null;
  }
}

/**
 * Check if LLM is configured (has backend API key).
 * Returns false if backend would fall back to template.
 */
export async function isLLMAvailable(): Promise<boolean> {
  try {
    const { data } = await api.get<{ available: boolean }>("/ai/status");
    return data.available;
  } catch {
    return false;
  }
}
