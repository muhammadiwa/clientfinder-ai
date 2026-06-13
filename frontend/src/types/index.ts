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
