/**
 * formatApiError — convert API/axios errors into user-friendly
 * Bahasa Indonesia messages.
 *
 * Handles:
 * - 422 (Pydantic validation) — converts the field-level errors
 *   to a single human-readable message
 * - 401 (unauthorized) — auth.invalidCredentials / formErrors.unauthorized
 * - 403 (forbidden) — formErrors.forbidden
 * - 404 (not found) — formErrors.notFound
 * - 409 (conflict) — formErrors.conflict
 * - 429 (rate limit) — formErrors.rateLimited
 * - 5xx (server error) — formErrors.serverError
 * - Network / unknown — formErrors.networkError / unknown
 *
 * Pattern: do NOT trust the raw error.detail (English Pydantic
 * messages). Convert via this helper so users see ID copy.
 */
import { AxiosError } from "axios";
import { getT } from "@/i18n";

export interface ApiErrorPayload {
  detail?: string | Array<{ loc?: string[]; msg?: string; type?: string }>;
  error?: {
    code?: string;
    message?: string;
  };
}

const FIELD_TRANSLATIONS: Record<string, string> = {
  email: "Email",
  password: "Kata sandi",
  full_name: "Nama lengkap",
  fullName: "Nama lengkap",
  name: "Nama",
  subject: "Subjek",
  body: "Body",
  hook_id: "Hook",
  prospect_id: "Prospek",
  template_id: "Template",
  sequence_id: "Sequence",
  channel: "Channel",
  status: "Status",
  source: "Sumber",
  keywords: "Kata kunci",
  location: "Lokasi",
  max_results: "Jumlah hasil",
};

const TYPE_TRANSLATIONS: Record<string, string> = {
  missing: "wajib diisi",
  value_error: "nilai tidak valid",
  type_error: "tipe data tidak valid",
  "string_too_short": "terlalu pendek",
  "string_too_long": "terlalu panjang",
  "value_error.any_str.min_length": "terlalu pendek (min {min_length} karakter)",
  "value_error.any_str.max_length": "terlalu panjang (max {max_length} karakter)",
  "value_error.email": "format email tidak valid",
  "json_invalid": "format JSON tidak valid",
  "int_parsing": "harus berupa angka",
  "float_parsing": "harus berupa angka desimal",
  "bool_parsing": "harus berupa true/false",
  "uuid_parsing": "format tidak valid",
};

function translateField(fieldName: string): string {
  return FIELD_TRANSLATIONS[fieldName] ?? fieldName;
}

function translateType(type: string): string {
  return TYPE_TRANSLATIONS[type] ?? "tidak valid";
}

function formatValidationDetails(
  details: Array<{ loc?: string[]; msg?: string; type?: string }>,
): string {
  if (!details.length) return getT().formErrors.validationFailed;
  return details
    .map((d) => {
      const field = d.loc && d.loc.length > 1 ? translateField(d.loc[d.loc.length - 1]) : "Data";
      const typeMsg = d.type ? translateType(d.type) : (d.msg ?? "tidak valid");
      return `${field}: ${typeMsg}`;
    })
    .join("; ");
}

/**
 * Format an unknown error (catch block arg) into a user-friendly ID string.
 */
export function formatApiError(error: unknown): string {
  if (error instanceof AxiosError) {
    return formatAxiosError(error);
  }
  if (error instanceof Error) {
    return error.message || getT().formErrors.unknown;
  }
  return getT().formErrors.unknown;
}

function formatAxiosError(error: AxiosError<ApiErrorPayload>): string {
  // Network error (no response from server)
  if (!error.response) {
    return getT().formErrors.networkError;
  }

  const status = error.response.status;
  const data = error.response.data;
  const detail = data?.detail;
  const serverMsg = data?.error?.message;

  // Pydantic 422: convert field errors to ID
  if (status === 422) {
    if (Array.isArray(detail)) {
      return formatValidationDetails(detail);
    }
    if (typeof detail === "string") {
      // Sometimes Pydantic returns a string (e.g. "Value error, ...")
      return `${getT().formErrors.validationFailed}: ${detail}`;
    }
    return getT().formErrors.validationFailed;
  }

  // 401: most common in login flow
  if (status === 401) {
    // If on /auth/login, treat as invalid credentials
    if (typeof detail === "string" && /credential|invalid|email|password|unauthorized/i.test(detail)) {
      return getT().auth.invalidCredentials;
    }
    return getT().formErrors.unauthorized;
  }

  if (status === 403) {
    return getT().formErrors.forbidden;
  }
  if (status === 404) {
    return getT().formErrors.notFound;
  }
  if (status === 409) {
    return getT().formErrors.conflict;
  }
  if (status === 429) {
    return getT().formErrors.rateLimited;
  }
  if (status >= 500) {
    return getT().formErrors.serverError;
  }

  // Fallback: use the server message if it looks Indonesian, else unknown
  if (serverMsg) return serverMsg;
  if (typeof detail === "string") return detail;
  return getT().formErrors.unknown;
}

/**
 * Format a field-level error (for inline form validation, not API errors).
 * Used by the FormField component to show errors below the input.
 */
export function formatFieldError(
  fieldName: string,
  type: "required" | "tooShort" | "tooLong" | "invalid" | "mismatch" | "custom",
  params?: { min?: number; max?: number; custom?: string },
): string {
  const label = translateField(fieldName);
  switch (type) {
    case "required":
      return getT().formErrors.required.replace("{field}", label);
    case "tooShort":
      return getT().formErrors.fieldTooShort
        .replace("{field}", label)
        .replace("{min}", String(params?.min ?? "?"));
    case "tooLong":
      return getT().formErrors.fieldTooLong
        .replace("{field}", label)
        .replace("{max}", String(params?.max ?? "?"));
    case "invalid":
      return getT().formErrors.fieldInvalid.replace("{field}", label);
    case "mismatch":
      return getT().formErrors.passwordMismatch;
    case "custom":
      return params?.custom ?? getT().formErrors.unknown;
  }
}
