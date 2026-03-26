import { apiFetch } from "./client";

export interface CaptchaChallenge {
  token: string;
  question: string;
}

export interface BugReportPayload {
  message: string;
  page_url?: string;
  user_agent?: string;
  captcha_token?: string;
  captcha_answer?: string;
}

export interface BugReportRead {
  id: string;
  user_id: string | null;
  message: string;
  page_url: string | null;
  user_agent: string | null;
  created_at: string;
}

export function getCaptcha(): Promise<CaptchaChallenge> {
  return apiFetch<CaptchaChallenge>("/bug-reports/captcha", { method: "GET" });
}

export function submitBugReport(payload: BugReportPayload): Promise<BugReportRead> {
  return apiFetch<BugReportRead>("/bug-reports", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
