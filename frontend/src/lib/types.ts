export type Role = "patient" | "staff" | "admin";

export interface AuthUser {
  access_token: string;
  role: Role;
  user_id: number;
  name: string;
}

export interface Profile {
  id: number;
  date_of_birth: string | null;
  phone: string | null;
  preferred_language: string;
  emergency_contact: string | null;
  mrn: string | null;
}

export interface Me {
  id: number;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  profile: Profile | null;
}

export interface Department {
  id: number;
  name: string;
  slug: string;
  description: string;
  active: boolean;
}

export interface Appointment {
  id: number;
  patient_id: number;
  doctor_id: number;
  slot_id: number | null;
  status: string;
  reason: string;
  confirmation_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientDocument {
  id: number;
  patient_id: number;
  original_filename: string;
  document_type: string;
  classification_confidence: number;
  content_type: string;
  size_bytes: number;
  checksum: string;
  document_date: string | null;
  is_duplicate: boolean;
  notes: string;
  created_at: string;
}

export interface Reminder {
  id: number;
  patient_id: number;
  appointment_id: number | null;
  reminder_type: string;
  message: string;
  scheduled_at: string;
  status: string;
  channel: string;
}

export interface WorkflowStep {
  id: number;
  sequence: number;
  agent: string;
  action: string;
  status: string;
  message: string;
  data: Record<string, unknown>;
  created_at: string;
}

export interface Escalation {
  id: number;
  run_id: number;
  category: string;
  reason: string;
  severity: string;
  status: string;
  requires_approval: boolean;
  reviewed_by: number | null;
  resolution_note: string;
  created_at: string;
}

export interface WorkflowRun {
  id: number;
  thread_id: string;
  patient_id: number | null;
  request_text: string;
  current_step: string;
  status: string;
  summary: string;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRunDetail extends WorkflowRun {
  state: Record<string, any>;
  steps: WorkflowStep[];
  escalations: Escalation[];
}

export interface AuditEvent {
  id: number;
  actor_id: number | null;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  workflow_run_id: number | null;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface Analytics {
  totals: {
    workflows: number;
    patients: number;
    appointments: number;
    documents: number;
    reminders: number;
    escalations: number;
    escalations_pending: number;
    audit_events: number;
    avg_steps_per_workflow: number;
  };
  workflows_by_status: Record<string, number>;
  appointments_by_status: Record<string, number>;
  escalations_by_category: Record<string, number>;
  escalations_by_status: Record<string, number>;
  documents_by_type: Record<string, number>;
  reminders_by_type: Record<string, number>;
  appointments_by_department: { department: string; count: number }[];
  duplicate_documents: number;
}

export interface TraceEvent {
  type: "step" | "done" | "error" | "info";
  node?: string;
  event?: WorkflowStep;
  message?: string;
}
