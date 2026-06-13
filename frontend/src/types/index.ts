/**
 * Shared API types — mirrors backend Pydantic schemas
 */
export type UserRole = "owner" | "admin" | "member";

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  role: UserRole;
  is_active?: boolean;
  avatar_url?: string | null;
  last_login_at?: string | null;
  created_at?: string;
}

export type ProspectStatus =
  | "new"
  | "enriching"
  | "scored"
  | "approved"
  | "contacted"
  | "replied"
  | "won"
  | "lost"
  | "archived";

export type ProspectGrade = "A" | "B" | "C" | "D";

export interface Prospect {
  id: string;
  company_name: string;
  industry?: string | null;
  size_estimate?: string | null;
  location_city?: string | null;
  location_province?: string | null;
  website?: string | null;
  phone?: string | null;
  email?: string | null;
  social_links: Record<string, unknown>;
  description?: string | null;
  source: string;
  source_query?: string | null;
  source_url?: string | null;
  raw_data: Record<string, unknown>;
  status: ProspectStatus;
  quality_grade?: ProspectGrade | null;
  score_total?: number | null;
  owner_id?: string | null;
  last_contacted_at?: string | null;
  discovered_at: string;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
}

export interface ProspectListResponse {
  items: Prospect[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// --- T4 Scout module ---

export type ScrapingSource = "google" | "maps" | "twitter" | "threads";
export type ScrapingStatus = "pending" | "running" | "completed" | "failed";

export interface ScrapingJob {
  id: string;
  source: ScrapingSource | string;
  query: {
    keywords: string;
    location?: string | null;
    max_results?: number;
  };
  status: ScrapingStatus | string;
  prospects_found: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ScrapingJobListResponse {
  items: ScrapingJob[];
  total: number;
}

// --- T6 Outreach module ---

export type MessageChannel = "email" | "whatsapp" | "threads";
export type MessageStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "scheduled"
  | "sending"
  | "sent"
  | "delivered"
  | "opened"
  | "clicked"
  | "replied"
  | "bounced"
  | "failed"
  | "rejected";
export type MessageDirection = "outbound" | "inbound";

export interface Message {
  id: string;
  prospect_id: string;
  channel: MessageChannel;
  direction: MessageDirection;
  subject: string | null;
  body: string;
  status: MessageStatus;
  scheduled_at: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  opened_at: string | null;
  clicked_at: string | null;
  replied_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  error_message: string | null;
  external_id: string | null;
  extra_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface MessageListResponse {
  items: Message[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

/** Counts of messages per status — drives the hero KPI cards. */
export interface OutreachStats {
  draft: number;
  pending_approval: number;
  approved: number;
  scheduled: number;
  sending: number;
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
  bounced: number;
  failed: number;
  rejected: number;
}

// --- T6 Templates (T6 Group 3) ---

export interface Template {
  id: string;
  name: string;
  channel: MessageChannel;
  category: string | null;
  subject: string | null;
  body: string;
  variables: string[];
  is_active: boolean;
  usage_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface TemplateListResponse {
  items: Template[];
  total: number;
}

// --- T6 Sequences (T6 Group 3) ---

export interface SequenceStep {
  order: number;
  channel: MessageChannel;
  template_id?: string | null;
  day_offset: number;
  conditions?: Record<string, unknown>;
}

export interface Sequence {
  id: string;
  name: string;
  description: string | null;
  steps: SequenceStep[];
  is_active: boolean;
  target_grade: string[] | null;
  target_source: string[] | null;
  target_industry: string[] | null;
  daily_send_cap: number;
  created_by: string | null;
}

export interface SequenceListResponse {
  items: Sequence[];
  total: number;
}
