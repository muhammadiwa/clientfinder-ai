import { api } from "./client";
import type {
  Message,
  MessageChannel,
  MessageListResponse,
  OutreachStats,
  Template,
  TemplateListResponse,
  Sequence,
  SequenceListResponse,
  SequenceStep,
} from "@/types";

export interface MessageCreate {
  prospect_id: string;
  channel: MessageChannel;
  subject?: string;
  body: string;
  scheduled_at?: string;
  hook_id?: string;
  template_id?: string;
}

export interface MessageUpdate {
  subject?: string;
  body?: string;
  scheduled_at?: string;
}

export interface MessageApproval {
  approve: boolean;
  reason?: string;
}

export interface MessageGenerateRequest {
  prospect_id: string;
  hook_id: string;
  channel: MessageChannel;
  template_id?: string;
}

export interface MessageListFilters {
  page?: number;
  per_page?: number;
  status?: string;
  channel?: MessageChannel;
  prospect_id?: string;
  prospect_grade?: string;
  needs_approval?: boolean;
}

// --- Message CRUD ---

export async function listMessages(
  filters: MessageListFilters = {},
): Promise<MessageListResponse> {
  const params: Record<string, string | number | boolean> = {};
  if (filters.page != null) params.page = filters.page;
  if (filters.per_page != null) params.per_page = filters.per_page;
  if (filters.status) params.status = filters.status;
  if (filters.channel) params.channel = filters.channel;
  if (filters.prospect_id) params.prospect_id = filters.prospect_id;
  if (filters.prospect_grade) params.prospect_grade = filters.prospect_grade;
  if (filters.needs_approval) params.needs_approval = true;
  const { data } = await api.get<MessageListResponse>("/outreach/messages", {
    params,
  });
  return data;
}

/** Hero KPI counts — drives the outreach stats cards. */
export async function getOutreachStats(): Promise<OutreachStats> {
  const { data } = await api.get<OutreachStats>("/outreach/stats");
  return data;
}

export async function getMessage(id: string): Promise<Message> {
  const { data } = await api.get<Message>(`/outreach/messages/${id}`);
  return data;
}

export async function createMessage(payload: MessageCreate): Promise<Message> {
  const { data } = await api.post<Message>("/outreach/messages", payload);
  return data;
}

export async function updateMessage(
  id: string,
  payload: MessageUpdate,
): Promise<Message> {
  const { data } = await api.patch<Message>(
    `/outreach/messages/${id}`,
    payload,
  );
  return data;
}

export async function deleteMessage(id: string): Promise<void> {
  await api.delete(`/outreach/messages/${id}`);
}

// --- Workflow ---

export async function submitForApproval(id: string): Promise<Message> {
  const { data } = await api.post<Message>(
    `/outreach/messages/${id}/submit`,
  );
  return data;
}

export async function approveMessage(
  id: string,
  body: MessageApproval = { approve: true },
): Promise<Message> {
  const { data } = await api.post<Message>(
    `/outreach/messages/${id}/approve`,
    body,
  );
  return data;
}

export async function sendMessage(id: string): Promise<Message> {
  const { data } = await api.post<Message>(
    `/outreach/messages/${id}/send`,
  );
  return data;
}

export async function generateMessage(
  payload: MessageGenerateRequest,
  create = true,
): Promise<Message> {
  const { data } = await api.post<Message>(
    `/outreach/messages/generate?create=${create}`,
    payload,
  );
  return data;
}

// --- Templates ---

export interface TemplateCreate {
  name: string;
  channel: MessageChannel;
  category?: string;
  subject?: string;
  body: string;
  variables?: string[];
  is_active?: boolean;
}

export async function listTemplates(
  channel?: MessageChannel,
): Promise<TemplateListResponse> {
  const { data } = await api.get<TemplateListResponse>("/templates", {
    params: channel ? { channel } : {},
  });
  return data;
}

export async function getTemplate(id: string): Promise<Template> {
  const { data } = await api.get<Template>(`/templates/${id}`);
  return data;
}

export async function createTemplate(payload: TemplateCreate): Promise<Template> {
  const { data } = await api.post<Template>("/templates", payload);
  return data;
}

export async function updateTemplate(
  id: string,
  payload: Partial<TemplateCreate>,
): Promise<Template> {
  const { data } = await api.patch<Template>(`/templates/${id}`, payload);
  return data;
}

export async function deleteTemplate(id: string): Promise<void> {
  await api.delete(`/templates/${id}`);
}

// --- Sequences ---

export interface SequenceCreate {
  name: string;
  description?: string;
  steps: SequenceStep[];
  is_active?: boolean;
  target_grade?: string[];
  target_source?: string[];
  target_industry?: string[];
  daily_send_cap?: number;
}

export async function listSequences(
  isActive?: boolean,
): Promise<SequenceListResponse> {
  const { data } = await api.get<SequenceListResponse>("/sequences", {
    params: isActive != null ? { is_active: isActive } : {},
  });
  return data;
}

export async function getSequence(id: string): Promise<Sequence> {
  const { data } = await api.get<Sequence>(`/sequences/${id}`);
  return data;
}

export async function createSequence(
  payload: SequenceCreate,
): Promise<Sequence> {
  const { data } = await api.post<Sequence>("/sequences", payload);
  return data;
}

export async function updateSequence(
  id: string,
  payload: Partial<SequenceCreate>,
): Promise<Sequence> {
  const { data } = await api.patch<Sequence>(`/sequences/${id}`, payload);
  return data;
}

export async function deleteSequence(id: string): Promise<void> {
  await api.delete(`/sequences/${id}`);
}

// --- Analytics (Sprint 3A sub-task 3) ---

export interface SequenceStepStats {
  step_index: number;
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
  bounced: number;
  failed: number;
  response_rate: number;
  open_rate: number;
}

export interface SequenceChannelStats {
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
  bounced: number;
  failed: number;
  response_rate: number;
  open_rate: number;
}

export interface SequenceAnalytics {
  sequence_id: string;
  sequence_name: string;
  daily_send_cap: number;
  totals: {
    sent: number;
    delivered: number;
    opened: number;
    clicked: number;
    replied: number;
    bounced: number;
    failed: number;
  };
  by_step: SequenceStepStats[];
  by_channel: Record<string, SequenceChannelStats>;
  today_sent: number;
  computed_at: string;
}

export async function getSequenceAnalytics(
  sequenceId: string,
): Promise<SequenceAnalytics> {
  const { data } = await api.get<SequenceAnalytics>(
    `/sequences/${sequenceId}/analytics`,
  );
  return data;
}

// --- Enrollments (Sprint 3A) ---

export interface EnrollmentItem {
  id: string;
  prospect_id: string;
  sequence_id: string;
  current_step: number;
  status: "active" | "paused" | "completed" | "stopped";
  next_action_at: string | null;
  started_at: string;
  completed_at: string | null;
  stopped_reason: string | null;
}

export interface EnrollmentListResponse {
  items: EnrollmentItem[];
  total: number;
}

export async function listEnrollments(
  params: {
    status_filter?: string;
    sequence_id?: string;
    prospect_id?: string;
    limit?: number;
  } = {},
): Promise<EnrollmentListResponse> {
  const { data } = await api.get<EnrollmentListResponse>(
    "/sequences/enrollments",
    { params },
  );
  return data;
}

export async function pauseEnrollment(
  enrollmentId: string,
): Promise<{ ok: boolean; status?: string; error?: string }> {
  const { data } = await api.post<{ ok: boolean; status?: string; error?: string }>(
    `/sequences/enrollments/${enrollmentId}/pause`,
  );
  return data;
}

export async function resumeEnrollment(
  enrollmentId: string,
): Promise<{ ok: boolean; status?: string; error?: string }> {
  const { data } = await api.post<{ ok: boolean; status?: string; error?: string }>(
    `/sequences/enrollments/${enrollmentId}/resume`,
  );
  return data;
}

export async function stopEnrollment(
  enrollmentId: string,
  reason: string = "manual_stop",
): Promise<{ ok: boolean; status?: string; error?: string }> {
  const { data } = await api.post<{ ok: boolean; status?: string; error?: string }>(
    `/sequences/enrollments/${enrollmentId}/stop`,
    null,
    { params: { reason } },
  );
  return data;
}

export async function triggerDripRunner(): Promise<{
  ok: boolean;
  task_id: string;
  status: string;
}> {
  const { data } = await api.post<{
    ok: boolean;
    task_id: string;
    status: string;
  }>("/sequences/drip-runner/run");
  return data;
}

export async function enrollProspectInSequence(
  prospectId: string,
  sequenceId: string,
): Promise<{ ok: boolean; enrollment_id: string; next_action_at: string }> {
  const { data } = await api.post<{
    ok: boolean;
    enrollment_id: string;
    next_action_at: string;
  }>("/sequences/enroll", {
    prospect_id: prospectId,
    sequence_id: sequenceId,
  });
  return data;
}
