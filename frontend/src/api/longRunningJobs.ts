import { apiFetch } from "./client";

export type LongRunningJobKind =
  | "smart_discovery"
  | "source_url_extraction"
  | "bulk_source_extraction";
export type LongRunningJobStatus = "pending" | "running" | "succeeded" | "failed";

export interface JobStartResponse {
  job_id: string;
  status: LongRunningJobStatus;
}

export interface LongRunningJobRead<T = unknown> {
  id: string;
  kind: LongRunningJobKind;
  status: LongRunningJobStatus;
  source_id?: string | null;
  request_payload: Record<string, unknown>;
  result_payload?: T | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export function getLongRunningJob<T>(jobId: string): Promise<LongRunningJobRead<T>> {
  return apiFetch(`/jobs/${jobId}`);
}
